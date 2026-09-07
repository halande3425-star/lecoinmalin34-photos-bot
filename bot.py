import json, os, time, threading, requests
from flask import Flask, send_from_directory, jsonify

TOKEN = os.environ.get("BOT_TOKEN", "").strip()
SOURCE_CHAT = os.environ.get("SOURCE_CHAT", "@Lecoinmalin34").strip()
PUBLIC_DOMAIN = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "").strip()
WEBAPP_URL = os.environ.get("WEBAPP_URL", "").strip()
if not WEBAPP_URL and PUBLIC_DOMAIN:
    WEBAPP_URL = "https://" + PUBLIC_DOMAIN

API = f"https://api.telegram.org/bot{TOKEN}"
PAGE_SIZE = 20

with open("catalog.json", encoding="utf-8") as f:
    CATALOG = json.load(f)
with open("menu.json", encoding="utf-8") as f:
    MENU = json.load(f)

app = Flask(__name__, static_folder="web", static_url_path="")

def api(method, **data):
    try:
        r = requests.post(f"{API}/{method}", json=data, timeout=90)
        j = r.json()
    except Exception as e:
        print("HTTP error:", method, repr(e), flush=True)
        return {"ok": False, "description": str(e)}
    if not j.get("ok"):
        print("Telegram error:", method, j, flush=True)
    return j

def send_start(chat_id):
    caption = (
        "✨ <b>LE COIN MALIN 34</b>\n"
        "<i>Catalogue officiel</i>\n\n"
        "Bienvenue dans notre catalogue.\n"
        "Choisissez une catégorie pour découvrir nos produits, photos et vidéos. 👇"
    )

    rows = [
        [{"text":"👟  Chaussures","callback_data":"group:shoes"}],
        [{"text":"👕  Vêtements","callback_data":"group:clothes"}],
        [{"text":"📱  High-Tech","callback_data":"group:tech"}],
        [{"text":"⌚  Montres & Bijoux","callback_data":"group:watches"}],
        [{"text":"👜  Accessoires","callback_data":"group:accessories"}],
        [{"text":"🚚  Produits prêts à être expédiés","callback_data":"group:ready"}],
        [{"text":"🛒  Comment passer commande","callback_data":"group:order"}],
        [{"text":"💬  Avis clients","callback_data":"group:reviews"}],
        [{"text":"✨  Voir plus","callback_data":"group:more"}],
    ]
    if WEBAPP_URL:
        rows.insert(0, [{"text":"🛍️  Ouvrir le catalogue Premium","web_app":{"url":WEBAPP_URL}}])
    kb = {"inline_keyboard": rows}

    try:
        with open("web/logo.png", "rb") as f:
            files = {"photo": ("logo.png", f, "image/png")}
            data = {
                "chat_id": str(chat_id),
                "caption": caption,
                "parse_mode": "HTML",
                "reply_markup": json.dumps(kb, ensure_ascii=False)
            }
            rr = requests.post(f"{API}/sendPhoto", data=data, files=files, timeout=90).json()
            if rr.get("ok"):
                return rr
            print("sendPhoto failed:", rr, flush=True)
    except Exception as e:
        print("sendPhoto local error:", repr(e), flush=True)

    return api("sendMessage", chat_id=chat_id, text=caption, parse_mode="HTML", reply_markup=kb)

def clean_title(t):
    mapping = {
        "📦 Articles disponibles":"Tous les articles",
        "💬 Avis clients":"Avis clients",
        "Sacoche 👜 et sac":"Sacs & Sacoches",
        "Chaussures homme femme":"Homme / Femme",
        "comment passer commande":"Comment commander",
        "stone et cp":"Stone & CP",
        "casquette de marque":"Casquettes de marque",
        "dyson sur commande":"Dyson",
        "Bracelets, bracelets et joncs Cartier":"Bracelets & Joncs Cartier",
        "Gshock⌚️":"G‑Shock",
        "Électronique🎧":"Électronique",
        "Pack fournisseur exploitation":"Pack fournisseurs",
        "paire de lunette tout marque":"Lunettes de marque",
        "chaussure de football":"Football",
        "Parfum homme femme":"Parfums Homme / Femme",
        "montre de marque":"Montres de marque",
        "maillot de foot":"Maillots de foot",
        "UG":"UGG",
        "crocs":"Crocs",
        "Casque arai sur commande 🚀":"Casques Arai",
        "Ensemble essentials":"Essentials",
        "Coque de téléphone 📱":"Coques téléphone",
        "Alo femme 👩":"Alo Femme",
        "Alo homme 👨":"Alo Homme",
        "vêtements all":"Sport & Été",
        "vêtements luxe":"Vêtements Luxe",
        "⚡️moto électrique":"Moto électrique",
        "Lunnete meta qui flime":"Lunettes Meta",
        "commande client":"Commandes clients",
        "📦 VENTE EN GROS SUR COMMANDE 📦":"Vente en gros",
        "Chaussures de luxe 🤩":"Luxe & Claquettes",
        "Chaussures pour enfants 👶":"Chaussures Enfants",
        "Basic fit offre":"Basic‑Fit — Offre",
        "Location de voiture -40%":"Location voiture -40 %",
        "Déblocage snap":"Déblocage Snap",
        "Doudoune hiver ❄️":"Doudoune hiver",
        "Ensemble haut et bas":"Ensemble haut & bas",
        "Valise 🧳":"Valises",
        "Pc gamer 💻":"PC Gamer",
        "Canapé 🛋️ bubble sur commande":"Canapé Bubble",
        "Bonnet d’hiver homme femme ☃️":"Bonnet hiver"
    }
    return mapping.get(t, t)

@app.get("/")
def index():
    return send_from_directory("web", "index.html")

@app.get("/api/catalog")
def catalog_api():
    groups = []
    for g in MENU["groups"]:
        items = []
        for tid in g["topics"]:
            c = CATALOG.get(str(tid))
            if not c:
                continue
            items.append({
                "id": str(tid),
                "title": clean_title(c["title"]),
                "photos": c.get("photos", 0),
                "videos": c.get("videos", 0),
                "count": len(c.get("message_ids", []))
            })
        if items:
            groups.append({
                "id":g["id"], "emoji":g["emoji"], "title":g["title"],
                "subtitle":g["subtitle"], "items":items
            })
    return jsonify({"groups":groups})

def group_keyboard(group_id):
    g = next((x for x in MENU["groups"] if x["id"] == group_id), None)
    if not g:
        return {"inline_keyboard":[[{"text":"🏠 Accueil","callback_data":"home"}]]}
    rows=[]
    for tid in g["topics"]:
        c=CATALOG.get(str(tid))
        if not c:
            continue
        p,v=c.get("photos",0),c.get("videos",0)
        suffix=f"📷 {p}"
        if v:
            suffix += f" · 🎬 {v}"
        rows.append([{"text":f"{clean_title(c['title'])}  |  {suffix}","callback_data":f"cat:{tid}:0"}])
    rows.append([{"text":"🏠 Accueil","callback_data":"home"}])
    return {"inline_keyboard":rows}

def send_page(chat_id, tid, offset=0):
    c=CATALOG.get(str(tid))
    if not c:
        return
    ids=c.get("message_ids",[])
    page=ids[offset:offset+PAGE_SIZE]
    if not page:
        return
    total=len(ids)
    end=offset+len(page)
    p,v=c.get("photos",0),c.get("videos",0)
    title=clean_title(c["title"])
    api("sendMessage", chat_id=chat_id,
        text=f"✨ <b>{title}</b>\n📷 {p} photos  ·  🎬 {v} vidéos\n\nAffichage {offset+1}–{end} sur {total}",
        parse_mode="HTML")

    res=api("copyMessages", chat_id=chat_id, from_chat_id=SOURCE_CHAT, message_ids=page)
    if not res.get("ok"):
        return api("sendMessage", chat_id=chat_id,
                   text=f"⚠️ Telegram n’a pas pu copier ces médias.\n<code>{res.get('description','Erreur inconnue')}</code>",
                   parse_mode="HTML")

    nav=[]
    if offset>0:
        nav.append({"text":"⬅️ Précédents","callback_data":f"cat:{tid}:{max(0,offset-PAGE_SIZE)}"})
    if end<total:
        nav.append({"text":"Suivants ➡️","callback_data":f"cat:{tid}:{end}"})
    rows=[nav] if nav else []
    rows.append([{"text":"🏠 Accueil","callback_data":"home"}])
    api("sendMessage", chat_id=chat_id,
        text=f"✅ <b>{end} / {total} médias affichés</b>",
        parse_mode="HTML", reply_markup={"inline_keyboard":rows})

def handle(u):
    m=u.get("message")
    if m and m.get("chat",{}).get("type")=="private":
        if m.get("text","").startswith(("/start","/menu")):
            return send_start(m["chat"]["id"])
        wad=m.get("web_app_data")
        if wad:
            try:
                d=json.loads(wad.get("data","{}"))
                if d.get("action")=="open_topic":
                    return send_page(m["chat"]["id"], str(d["topic_id"]), 0)
            except Exception as e:
                print("web_app_data:",repr(e),flush=True)

    q=u.get("callback_query")
    if not q:
        return
    api("answerCallbackQuery", callback_query_id=q["id"])
    chat_id=q["message"]["chat"]["id"]
    d=q.get("data","")
    if d=="home":
        return send_start(chat_id)
    if d.startswith("group:"):
        gid=d.split(":",1)[1]
        g=next((x for x in MENU["groups"] if x["id"]==gid),None)
        if g:
            return api("sendMessage", chat_id=chat_id,
                       text=f"{g['emoji']} <b>{g['title']}</b>\n<i>{g['subtitle']}</i>",
                       parse_mode="HTML", reply_markup=group_keyboard(gid))
    if d.startswith("cat:"):
        _,tid,off=d.split(":",2)
        return send_page(chat_id,tid,int(off))

def poll():
    offset=0
    while True:
        try:
            r=requests.get(f"{API}/getUpdates",
                params={"timeout":50,"offset":offset,
                        "allowed_updates":json.dumps(["message","callback_query"])},
                timeout=60).json()
            for u in r.get("result",[]):
                offset=u["update_id"]+1
                handle(u)
        except Exception as e:
            print("Polling:",repr(e),flush=True)
            time.sleep(3)

def main():
    if not TOKEN:
        raise SystemExit("BOT_TOKEN manquant")
    threading.Thread(target=poll,daemon=True).start()
    port=int(os.environ.get("PORT","8080"))
    app.run(host="0.0.0.0",port=port,threaded=True)

if __name__=="__main__":
    main()
