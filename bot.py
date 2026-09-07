import json, os, time, requests

TOKEN = os.environ.get("BOT_TOKEN", "").strip()
SOURCE_CHAT = os.environ.get("SOURCE_CHAT", "@Lecoinmalin34").strip()
API = f"https://api.telegram.org/bot{TOKEN}"
PAGE_SIZE = 100

with open("catalog.json", encoding="utf-8") as f:
    CATALOG = json.load(f)

def api(method, **data):
    r = requests.post(f"{API}/{method}", json=data, timeout=60)
    j = r.json()
    if not j.get("ok"):
        print("Telegram error:", method, j, flush=True)
    return j

def keyboard_menu():
    rows=[]
    items=list(CATALOG.items())
    for i in range(0,len(items),2):
        row=[]
        for tid,c in items[i:i+2]:
            row.append({"text":c["title"],"callback_data":f"cat:{tid}:0"})
        rows.append(row)
    return {"inline_keyboard":rows}

def send_menu(chat_id, text="📸 Choisis une catégorie :"):
    api("sendMessage", chat_id=chat_id, text=text, reply_markup=keyboard_menu())

def send_page(chat_id, tid, offset):
    c=CATALOG.get(str(tid))
    if not c:
        return send_menu(chat_id,"Catégorie introuvable.")
    ids=c["message_ids"]; page=ids[offset:offset+PAGE_SIZE]
    if not page:
        return send_menu(chat_id,"Il n’y a plus de photos dans cette catégorie.")
    api("sendMessage",chat_id=chat_id,text=f"📂 {c['title']} — photos {offset+1} à {offset+len(page)} sur {len(ids)}")
    # copyMessages: jusqu'à 100 IDs, ordre croissant
    api("copyMessages", chat_id=chat_id, from_chat_id=SOURCE_CHAT, message_ids=page)
    buttons=[]
    if offset+PAGE_SIZE < len(ids):
        buttons.append({"text":"➡️ 100 suivantes","callback_data":f"cat:{tid}:{offset+PAGE_SIZE}"})
    buttons.append({"text":"🏠 Menu","callback_data":"menu"})
    api("sendMessage",chat_id=chat_id,text="👇 Continuer :",reply_markup={"inline_keyboard":[buttons]})

def handle(update):
    if "message" in update:
        m=update["message"]
        if m.get("chat",{}).get("type") == "private" and m.get("text","").startswith("/start"):
            send_menu(m["chat"]["id"])
    q=update.get("callback_query")
    if q:
        api("answerCallbackQuery",callback_query_id=q["id"])
        chat_id=q["message"]["chat"]["id"]
        data=q.get("data","")
        if data=="menu": return send_menu(chat_id)
        if data.startswith("cat:"):
            _,tid,off=data.split(":")
            return send_page(chat_id,tid,int(off))

def main():
    if not TOKEN:
        raise SystemExit("BOT_TOKEN manquant dans Railway Variables")
    print("Bot démarré", flush=True)
    offset=0
    while True:
        try:
            r=requests.get(f"{API}/getUpdates",params={"timeout":50,"offset":offset,"allowed_updates":json.dumps(["message","callback_query"])},timeout=60).json()
            for u in r.get("result",[]):
                offset=u["update_id"]+1
                handle(u)
        except Exception as e:
            print("Erreur:",repr(e),flush=True); time.sleep(3)

if __name__=="__main__": main()
