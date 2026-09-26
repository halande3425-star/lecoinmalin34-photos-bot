import os, sqlite3, secrets, json, time, threading, mimetypes
from pathlib import Path
from datetime import datetime
from flask import Flask, request, jsonify, session, send_from_directory, send_file
import requests

BASE_DIR = Path(__file__).resolve().parent
SHOP_WEB = BASE_DIR / "shop_web"
app = Flask(__name__)
app.secret_key = os.environ.get("SHOP_SECRET_KEY", secrets.token_hex(32))
DB = Path(os.environ.get("SHOP_DB", "/data/shop.db" if Path("/data").exists() else str(BASE_DIR / "shop.db")))
MEDIA_DIR = Path(os.environ.get("TELEGRAM_MEDIA_DIR", "/data/telegram_media" if Path("/data").exists() else str(BASE_DIR / "telegram_media")))
MEDIA_DIR.mkdir(parents=True, exist_ok=True)
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
SOURCE_CHAT = os.environ.get("TELEGRAM_SOURCE_CHAT", "@Lecoinmalin34").strip()
SOURCE_CHAT_ID = os.environ.get("TELEGRAM_SOURCE_CHAT_ID", "-1003782657059").strip()
TRANSFER_INSTRUCTIONS = os.environ.get("BANK_TRANSFER_INSTRUCTIONS", "Virement bancaire — les coordonnées de paiement seront communiquées après validation de la commande.")

CATALOG_FILE = BASE_DIR / "telegram_catalog.json"
CATALOG = json.loads(CATALOG_FILE.read_text(encoding="utf-8")) if CATALOG_FILE.exists() else {"topics": []}

def db():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c

def init():
    with db() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, first_name TEXT, last_name TEXT, address TEXT, address2 TEXT, postal_code TEXT, city TEXT, phone TEXT, email TEXT, created_at TEXT);
        CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY, tracking TEXT UNIQUE, user_id INTEGER, status TEXT, total REAL, payment_method TEXT, created_at TEXT);
        CREATE TABLE IF NOT EXISTS order_items(id INTEGER PRIMARY KEY, order_id INTEGER, telegram_message_id INTEGER, title TEXT, qty INTEGER, unit_price REAL, price_known INTEGER, category TEXT);
        """)
        # Backward-compatible columns for existing Railway DBs.
        for col,typ in [('address','TEXT'),('address2','TEXT'),('postal_code','TEXT'),('city','TEXT'),('phone','TEXT'),('email','TEXT')]:
            try: c.execute(f'ALTER TABLE users ADD COLUMN {col} {typ}')
            except sqlite3.OperationalError: pass
        try: c.execute('ALTER TABLE orders ADD COLUMN payment_method TEXT')
        except sqlite3.OperationalError: pass
        try: c.execute('ALTER TABLE order_items ADD COLUMN price_known INTEGER DEFAULT 0')
        except sqlite3.OperationalError: pass
        try: c.execute('ALTER TABLE order_items ADD COLUMN category TEXT')
        except sqlite3.OperationalError: pass
init()

def admin_ok(): return bool(session.get("admin"))
def user_ok(): return bool(session.get("user_id"))

def find_post(mid):
    for t in CATALOG.get('topics',[]):
        for p in t.get('posts',[]):
            if mid in p.get('media_ids',[]) or mid==p.get('id'):
                return t,p
    return None,None

def tg_call(method, payload):
    if not BOT_TOKEN: raise RuntimeError('BOT_TOKEN manquant')
    r=requests.post(f'https://api.telegram.org/bot{BOT_TOKEN}/{method}',json=payload,timeout=30)
    r.raise_for_status(); data=r.json()
    if not data.get('ok'): raise RuntimeError(data.get('description','Telegram API error'))
    return data['result']

def cache_path(mid): return MEDIA_DIR / f'{int(mid)}.bin'

def fetch_media(mid):
    path=cache_path(mid)
    if path.exists() and path.stat().st_size>0: return path
    if not BOT_TOKEN: raise RuntimeError('BOT_TOKEN manquant')
    # Copy the original Telegram message into the source chat, read its real file_id, then delete the temporary copy.
    copied=tg_call('copyMessage', {'chat_id': SOURCE_CHAT_ID or SOURCE_CHAT, 'from_chat_id': SOURCE_CHAT_ID or SOURCE_CHAT, 'message_id': int(mid)})
    temp_id=int(copied['message_id'])
    try:
        media=None
        if copied.get('photo'): media=copied['photo'][-1]
        elif copied.get('document'): media=copied['document']
        elif copied.get('video'): media=copied['video']
        elif copied.get('animation'): media=copied['animation']
        if not media: raise RuntimeError('Publication sans média téléchargeable')
        file_id=media['file_id']
        info=tg_call('getFile', {'file_id':file_id})
        fp=info.get('file_path')
        if not fp: raise RuntimeError('Telegram file_path absent')
        url=f'https://api.telegram.org/file/bot{BOT_TOKEN}/{fp}'
        rr=requests.get(url,timeout=60); rr.raise_for_status()
        tmp=path.with_suffix('.tmp')
        tmp.write_bytes(rr.content); tmp.replace(path)
        return path
    finally:
        try: tg_call('deleteMessage', {'chat_id': SOURCE_CHAT_ID or SOURCE_CHAT, 'message_id': temp_id})
        except Exception: pass

@app.get('/')
def home(): return send_from_directory(str(SHOP_WEB), 'index.html')
@app.get('/health')
def health(): return jsonify(ok=True,topics=len(CATALOG.get('topics',[])),publications=sum(len(t.get('posts',[])) for t in CATALOG.get('topics',[]))),200

@app.get('/api/catalog')
def api_catalog(): return jsonify(CATALOG)

@app.get('/api/stats')
def api_stats():
    return jsonify(topics=len(CATALOG.get('topics',[])), publications=sum(len(t.get('posts',[])) for t in CATALOG.get('topics',[])), source_messages=3938, source_total_messages=4042)

@app.get('/api/media/<int:message_id>')
def api_media(message_id):
    t,p=find_post(message_id)
    if not t: return jsonify(error='Publication introuvable'),404
    try: path=fetch_media(message_id)
    except Exception as e: return jsonify(error='Média indisponible',detail=str(e)),502
    # Browser can display Telegram image/file directly; type is inferred from content where possible.
    mime='image/jpeg'
    if p.get('media_paths'):
        mime=mimetypes.guess_type(str(p['media_paths'][0]))[0] or mime
    return send_file(path, mimetype=mime, max_age=86400)

@app.post('/api/login')
def login():
    d=request.get_json(force=True)
    first=(d.get('first_name') or '').strip(); last=(d.get('last_name') or '').strip()
    if not first or not last: return jsonify(error='Prénom et nom obligatoires'),400
    with db() as c:
        cur=c.execute('INSERT INTO users(first_name,last_name,created_at) VALUES(?,?,?)',(first,last,datetime.utcnow().isoformat()))
        session['user_id']=cur.lastrowid; session['name']=f'{first} {last}'
    return jsonify(ok=True,name=session['name'])

@app.get('/api/me')
def me(): return jsonify(logged=user_ok(),name=session.get('name'))

@app.post('/api/order')
def order():
    d=request.get_json(force=True); items=d.get('items') or []
    if not items: return jsonify(error='Panier vide'),400
    first=(d.get('first_name') or '').strip(); last=(d.get('last_name') or '').strip(); address=(d.get('address') or '').strip(); postal=(d.get('postal_code') or '').strip(); city=(d.get('city') or '').strip(); phone=(d.get('phone') or '').strip(); email=(d.get('email') or '').strip(); address2=(d.get('address2') or '').strip()
    if not all([first,last,address,postal,city,phone]): return jsonify(error='Prénom, nom, adresse, code postal, ville et téléphone sont obligatoires'),400
    with db() as c:
        uid=session.get('user_id')
        if uid:
            c.execute('UPDATE users SET first_name=?,last_name=?,address=?,address2=?,postal_code=?,city=?,phone=?,email=? WHERE id=?',(first,last,address,address2,postal,city,phone,email,uid))
        else:
            cur=c.execute('INSERT INTO users(first_name,last_name,address,address2,postal_code,city,phone,email,created_at) VALUES(?,?,?,?,?,?,?,?,?)',(first,last,address,address2,postal,city,phone,email,datetime.utcnow().isoformat())); uid=cur.lastrowid; session['user_id']=uid
        tracking='LCM34-'+datetime.now().strftime('%y%m%d')+'-'+secrets.token_hex(3).upper()
        total=0.0; normalized=[]
        for i in items:
            mid=int(i.get('telegram_message_id') or i.get('message_id') or i.get('id'))
            t,p=find_post(mid)
            if not p: continue
            qty=max(1,int(i.get('qty',1)))
            # No price is invented. Client-supplied price is ignored unless an actual numeric price was parsed by admin later.
            raw=i.get('unit_price')
            price_known=isinstance(raw,(int,float)) and raw>=0
            price=float(raw) if price_known else 0.0
            if price_known: total += price*qty
            normalized.append((mid,p.get('title','Publication'),qty,price,int(price_known),t.get('title','')))
        cur=c.execute('INSERT INTO orders(tracking,user_id,status,total,payment_method,created_at) VALUES(?,?,?,?,?,?)',(tracking,uid,'En attente de paiement',total,'Virement bancaire',datetime.utcnow().isoformat()))
        oid=cur.lastrowid
        for row in normalized: c.execute('INSERT INTO order_items(order_id,telegram_message_id,title,qty,unit_price,price_known,category) VALUES(?,?,?,?,?,?,?)',(oid,*row))
    return jsonify(ok=True,tracking=tracking,total=total,status='En attente de paiement',payment_method='Virement bancaire',instructions=TRANSFER_INSTRUCTIONS)

@app.get('/api/orders')
def orders():
    if not user_ok(): return jsonify(orders=[])
    with db() as c: rows=[dict(x) for x in c.execute('SELECT tracking,status,total,payment_method,created_at FROM orders WHERE user_id=? ORDER BY id DESC',(session['user_id'],))]
    return jsonify(orders=rows)

@app.post('/api/admin/login')
def admin_login():
    d=request.get_json(force=True)
    if not ADMIN_PASSWORD or not secrets.compare_digest(str(d.get('password','')),ADMIN_PASSWORD): return jsonify(error='Accès refusé'),403
    session['admin']=True; return jsonify(ok=True)

@app.get('/api/admin/orders')
def admin_orders():
    if not admin_ok(): return jsonify(error='Admin requis'),403
    with db() as c:
        rows=[dict(x) for x in c.execute('SELECT o.id,o.tracking,o.status,o.total,o.payment_method,o.created_at,u.first_name,u.last_name,u.address,u.address2,u.postal_code,u.city,u.phone,u.email FROM orders o JOIN users u ON u.id=o.user_id ORDER BY o.id DESC')]
        for r in rows:
            r['items']=[dict(x) for x in c.execute('SELECT telegram_message_id,title,qty,unit_price,price_known,category FROM order_items WHERE order_id=?',(r['id'],))]
    return jsonify(orders=rows)

@app.post('/api/admin/order-status')
def admin_status():
    if not admin_ok(): return jsonify(error='Admin requis'),403
    d=request.get_json(force=True)
    allowed=['En attente de paiement','Paiement reçu','En préparation','Expédiée','Terminée','Annulée']
    if d.get('status') not in allowed: return jsonify(error='Statut invalide'),400
    with db() as c: c.execute('UPDATE orders SET status=? WHERE id=?',(d['status'],int(d['id'])))
    return jsonify(ok=True)

@app.get('/<path:filename>')
def shop_static(filename):
    # Explicit catch-all endpoint has a unique endpoint name, so there is no Flask static collision.
    return send_from_directory(str(SHOP_WEB), filename)

if __name__=='__main__':
    app.run(host='0.0.0.0',port=int(os.environ.get('PORT',8080)))
