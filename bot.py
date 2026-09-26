import os
import json
import sqlite3
import time
import threading
from pathlib import Path
from datetime import datetime
from flask import Flask, jsonify
import requests

BASE = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get('DATA_DIR', str(BASE / 'data'))) / 'catalog.db'
SEED_PATH = BASE / 'result.json'
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

TOKEN = os.environ.get('BOT_TOKEN', '').strip()
SOURCE_CHAT_ID = int(os.environ.get('SOURCE_CHAT_ID', '-1003782657059'))
SOURCE_CHAT_USERNAME = os.environ.get('SOURCE_CHAT_USERNAME', 'Lecoinmalin34w').strip().lstrip('@')
ADMIN_USER_ID = int(os.environ.get('ADMIN_USER_ID', '0') or 0)
PAGE_SIZE = max(1, min(10, int(os.environ.get('PAGE_SIZE', '8'))))
POLL_TIMEOUT = max(10, min(50, int(os.environ.get('POLL_TIMEOUT', '45'))))

app = Flask(__name__)


def db():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    with db() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS topics(
            topic_id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS messages(
            message_id INTEGER PRIMARY KEY,
            topic_id INTEGER,
            chat_id INTEGER,
            date TEXT,
            text TEXT,
            media_type TEXT,
            file_ref TEXT,
            has_media INTEGER DEFAULT 0,
            updated_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_messages_topic_date ON messages(topic_id, date, message_id);
        CREATE TABLE IF NOT EXISTS state(
            key TEXT PRIMARY KEY,
            value TEXT
        );
        ''')


def flatten_text(value):
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        out = []
        for x in value:
            if isinstance(x, str):
                out.append(x)
            elif isinstance(x, dict):
                out.append(str(x.get('text', '')))
        return ''.join(out)
    return ''


def seed_from_export():
    if not SEED_PATH.exists():
        return
    try:
        data = json.loads(SEED_PATH.read_text(encoding='utf-8'))
    except Exception as exc:
        print('Seed JSON unreadable:', exc, flush=True)
        return
    messages = data.get('messages', [])
    topic_map = {}
    with db() as c:
        for m in messages:
            if m.get('type') == 'service' and m.get('action') == 'topic_created':
                tid = m.get('id')
                title = m.get('title') or 'Sans nom'
                if isinstance(tid, int):
                    topic_map[tid] = title
                    c.execute('INSERT OR REPLACE INTO topics(topic_id,title,created_at) VALUES(?,?,?)',
                              (tid, title, m.get('date','')))
        for m in messages:
            if m.get('type') != 'message' or not isinstance(m.get('id'), int):
                continue
            rid = m.get('reply_to_message_id')
            topic_id = rid if isinstance(rid, int) and rid in topic_map else None
            media_type = m.get('media_type') or ('photo' if 'photo' in m else '')
            file_ref = m.get('photo') or m.get('file') or ''
            has_media = 1 if file_ref or media_type else 0
            c.execute('''INSERT INTO messages(message_id,topic_id,chat_id,date,text,media_type,file_ref,has_media,updated_at)
                         VALUES(?,?,?,?,?,?,?,?,?)
                         ON CONFLICT(message_id) DO UPDATE SET
                           topic_id=excluded.topic_id,
                           chat_id=excluded.chat_id,
                           date=excluded.date,
                           text=excluded.text,
                           media_type=excluded.media_type,
                           file_ref=excluded.file_ref,
                           has_media=excluded.has_media,
                           updated_at=excluded.updated_at''',
                      (m['id'], topic_id, SOURCE_CHAT_ID, m.get('date',''), flatten_text(m.get('text','')),
                       media_type, file_ref, has_media, datetime.utcnow().isoformat()))
        c.execute("INSERT OR REPLACE INTO state(key,value) VALUES('seeded_at',?)", (datetime.utcnow().isoformat(),))
        c.commit()
    print(f'Seed loaded: {len(topic_map)} topics, {len(messages)} exported records', flush=True)


def telegram(method, payload=None):
    if not TOKEN:
        return {'ok': False, 'description': 'BOT_TOKEN missing'}
    try:
        r = requests.post(f'https://api.telegram.org/bot{TOKEN}/{method}', json=payload or {}, timeout=65)
        return r.json()
    except Exception as exc:
        return {'ok': False, 'description': str(exc)}


def send_message(chat_id, text, reply_markup=None):
    payload = {'chat_id': chat_id, 'text': text, 'disable_web_page_preview': True}
    if reply_markup:
        payload['reply_markup'] = reply_markup
    return telegram('sendMessage', payload)


def edit_message(chat_id, message_id, text, reply_markup=None):
    payload = {'chat_id': chat_id, 'message_id': message_id, 'text': text, 'disable_web_page_preview': True}
    if reply_markup:
        payload['reply_markup'] = reply_markup
    return telegram('editMessageText', payload)


def answer_callback(callback_id, text=''):
    return telegram('answerCallbackQuery', {'callback_query_id': callback_id, 'text': text})


def copy_message(target_chat, source_message_id):
    return telegram('copyMessage', {
        'chat_id': target_chat,
        'from_chat_id': SOURCE_CHAT_ID,
        'message_id': source_message_id,
        'protect_content': False,
    })


def main_menu(page=0):
    with db() as c:
        topics = c.execute('SELECT topic_id,title FROM topics ORDER BY topic_id').fetchall()
    start = page * 8
    chunk = topics[start:start+8]
    rows = []
    for t in chunk:
        rows.append([{'text': t['title'], 'callback_data': f'topic:{t["topic_id"]}:0'}])
    nav = []
    if page > 0:
        nav.append({'text': '⬅️ Précédent', 'callback_data': f'menu:{page-1}'})
    if start + 8 < len(topics):
        nav.append({'text': 'Suivant ➡️', 'callback_data': f'menu:{page+1}'})
    if nav:
        rows.append(nav)
    return {'inline_keyboard': rows}, len(topics), page


def send_start(chat_id, page=0):
    markup, total, current = main_menu(page)
    text = ('🛍️ <b>LE COIN MALIN 34</b>\n\n'
            'Catalogue directement depuis Telegram.\n'
            'Choisis une rubrique pour voir les publications, photos et vidéos.\n\n'
            f'📚 {total} topics disponibles')
    payload = {'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML', 'reply_markup': markup}
    return telegram('sendMessage', payload)


def topic_page(chat_id, topic_id, page=0, editing=None):
    with db() as c:
        t = c.execute('SELECT title FROM topics WHERE topic_id=?', (topic_id,)).fetchone()
        if not t:
            return send_message(chat_id, 'Rubrique introuvable.')
        count = c.execute('SELECT COUNT(*) AS n FROM messages WHERE topic_id=?', (topic_id,)).fetchone()['n']
        rows = c.execute('''SELECT message_id,text,media_type,file_ref FROM messages
                           WHERE topic_id=? ORDER BY date,message_id LIMIT ? OFFSET ?''',
                         (topic_id, PAGE_SIZE, page * PAGE_SIZE)).fetchall()
    if editing:
        msg_id = editing
        head = f'📂 <b>{t["title"]}</b>\n\n'
        body = f'Page {page+1} • {count} publications\n\n'
        edit_message(chat_id, msg_id, head + body, topic_markup(topic_id, page, count))
    else:
        send_message(chat_id, f'📂 <b>{t["title"]}</b>\n\nPage {page+1} • {count} publications', topic_markup(topic_id, page, count))
    for r in rows:
        res = copy_message(chat_id, r['message_id'])
        if not res.get('ok'):
            text = r['text'] or 'Publication'
            link = f'https://t.me/{SOURCE_CHAT_USERNAME}/{r["message_id"]}' if SOURCE_CHAT_USERNAME else ''
            fallback = f'📌 {text}'
            if link:
                fallback += f'\n\n{link}'
            send_message(chat_id, fallback)
    return True


def topic_markup(topic_id, page, total):
    rows = []
    nav = []
    if page > 0:
        nav.append({'text':'⬅️', 'callback_data':f'topic:{topic_id}:{page-1}'})
    if (page+1)*PAGE_SIZE < total:
        nav.append({'text':'➡️', 'callback_data':f'topic:{topic_id}:{page+1}'})
    if nav:
        rows.append(nav)
    rows.append([
        {'text':'🏠 Accueil', 'callback_data':'menu:0'},
        {'text':'🔄 Actualiser', 'callback_data':f'topic:{topic_id}:{page}'}
    ])
    return {'inline_keyboard': rows}


def process_message(m):
    chat = m.get('chat', {})
    if chat.get('id') != SOURCE_CHAT_ID:
        return
    mid = m.get('message_id')
    if not isinstance(mid, int):
        return
    thread_id = m.get('message_thread_id')
    topic_id = thread_id if isinstance(thread_id, int) else None
    text = m.get('text') or m.get('caption') or ''
    media_type = ''
    file_ref = ''
    if m.get('photo'):
        media_type = 'photo'; file_ref = 'photo'
    elif m.get('video'):
        media_type = 'video'; file_ref = 'video'
    elif m.get('document'):
        media_type = 'document'; file_ref = 'document'
    elif m.get('animation'):
        media_type = 'animation'; file_ref = 'animation'
    elif m.get('audio'):
        media_type = 'audio'; file_ref = 'audio'
    elif m.get('voice'):
        media_type = 'voice'; file_ref = 'voice'
    if m.get('forum_topic_created'):
        ft = m['forum_topic_created']
        topic_id = thread_id or mid
        with db() as c:
            c.execute('INSERT OR REPLACE INTO topics(topic_id,title,created_at) VALUES(?,?,?)',
                      (topic_id, ft.get('name','Nouveau topic'), datetime.utcnow().isoformat()))
            c.commit()
        return
    if m.get('forum_topic_closed') or m.get('forum_topic_reopened'):
        return
    with db() as c:
        c.execute('''INSERT INTO messages(message_id,topic_id,chat_id,date,text,media_type,file_ref,has_media,updated_at)
                     VALUES(?,?,?,?,?,?,?,?,?)
                     ON CONFLICT(message_id) DO UPDATE SET
                       topic_id=excluded.topic_id, date=excluded.date, text=excluded.text,
                       media_type=excluded.media_type, file_ref=excluded.file_ref,
                       has_media=excluded.has_media, updated_at=excluded.updated_at''',
                  (mid, topic_id, SOURCE_CHAT_ID, datetime.fromtimestamp(m.get('date', time.time())).isoformat(),
                   text, media_type, file_ref, 1 if file_ref else 0, datetime.utcnow().isoformat()))
        c.commit()


def process_update(update):
    if 'message' in update:
        process_message(update['message'])
    elif 'edited_message' in update:
        process_message(update['edited_message'])
    elif 'callback_query' in update:
        cb = update['callback_query']
        data = cb.get('data','')
        chat_id = cb.get('message',{}).get('chat',{}).get('id')
        message_id = cb.get('message',{}).get('message_id')
        answer_callback(cb.get('id'))
        if not chat_id:
            return
        if data.startswith('menu:'):
            page = int(data.split(':')[1])
            markup, total, _ = main_menu(page)
            edit_message(chat_id, message_id,
                         f'🛍️ <b>LE COIN MALIN 34</b>\n\n📚 {total} topics — choisis une rubrique.', markup)
        elif data.startswith('topic:'):
            _, tid, page = data.split(':')
            topic_page(chat_id, int(tid), int(page), editing=message_id)


def polling_loop():
    if not TOKEN:
        print('BOT_TOKEN missing; Telegram polling disabled.', flush=True)
        return
    # avoid stale updates when a new deployment starts; keep future messages only
    telegram('deleteWebhook', {'drop_pending_updates': False})
    offset = 0
    while True:
        try:
            resp = telegram('getUpdates', {'timeout': POLL_TIMEOUT, 'offset': offset, 'allowed_updates': ['message','edited_message','callback_query']})
            if not resp.get('ok'):
                print('getUpdates error:', resp.get('description'), flush=True)
                time.sleep(3)
                continue
            for u in resp.get('result', []):
                offset = u['update_id'] + 1
                try:
                    process_update(u)
                except Exception as exc:
                    print('Update error:', exc, flush=True)
        except Exception as exc:
            print('Polling error:', exc, flush=True)
            time.sleep(3)


@app.get('/')
def home():
    with db() as c:
        topics = c.execute('SELECT COUNT(*) AS n FROM topics').fetchone()['n']
        messages = c.execute('SELECT COUNT(*) AS n FROM messages').fetchone()['n']
    return jsonify({'ok': True, 'service': 'lecoinmalin34-catalog-bot', 'topics': topics, 'messages': messages})


@app.get('/health')
def health():
    with db() as c:
        topics = c.execute('SELECT COUNT(*) AS n FROM topics').fetchone()['n']
        messages = c.execute('SELECT COUNT(*) AS n FROM messages').fetchone()['n']
    return jsonify({'ok': True, 'topics': topics, 'messages': messages})


@app.get('/api/topics')
def api_topics():
    with db() as c:
        rows = c.execute('SELECT topic_id,title FROM topics ORDER BY topic_id').fetchall()
    return jsonify([dict(r) for r in rows])


def command_allowed(message):
    return ADMIN_USER_ID == 0 or message.get('from', {}).get('id') == ADMIN_USER_ID


def command_handler(m):
    text = (m.get('text') or '').strip()
    if not text.startswith('/'):
        return False
    chat_id = m.get('chat',{}).get('id')
    cmd = text.split()[0].split('@')[0].lower()
    if cmd in ('/start','/catalogue','/catalog'):
        send_start(chat_id, 0); return True
    if cmd == '/status' and command_allowed(m):
        with db() as c:
            t = c.execute('SELECT COUNT(*) n FROM topics').fetchone()['n']
            msg = c.execute('SELECT COUNT(*) n FROM messages').fetchone()['n']
            media = c.execute('SELECT COUNT(*) n FROM messages WHERE has_media=1').fetchone()['n']
        send_message(chat_id, f'✅ Topics: {t}\n📦 Publications: {msg}\n🖼️ Médias référencés: {media}')
        return True
    return False


# Wrap process_message to catch commands sent privately to the bot and source messages.
_orig_process_message = process_message
def process_message(m):
    if m.get('chat',{}).get('id') != SOURCE_CHAT_ID:
        if command_handler(m):
            return
        return
    _orig_process_message(m)


if __name__ == '__main__':
    init_db()
    seed_from_export()
    if TOKEN:
        threading.Thread(target=polling_loop, daemon=True).start()
    port = int(os.environ.get('PORT','8080'))
    app.run(host='0.0.0.0', port=port, debug=False)
