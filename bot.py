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
SOURCE_CHAT_ID = None
BUILD_VERSION = "V5.4-SEARCH-ARTICLES"

# --- V5 : marques séparées Homme/Femme + Luxe + recherche de marque/modèle ---
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()
VISION_MODEL = os.environ.get("VISION_MODEL", "gpt-5.6-luna").strip()

BRAND_TOPIC_IDS = {"64", "3616"}  # Chaussures Homme/Femme + Chaussures de luxe
SEARCH_WAITING = {}  # chat_id -> topic_id

REGULAR_BRANDS = [
    "Nike", "New Balance", "On Running", "Adidas", "ASICS", "Jordan",
    "Puma", "Salomon", "UGG", "Crocs", "Reebok", "Converse",
    "Lacoste", "Autres / À vérifier"
]
LUXURY_BRANDS = [
    "Dior", "Louis Vuitton", "Prada", "Chanel", "Hermès", "Gucci",
    "Balenciaga", "Louboutin", "Versace", "Valentino", "Givenchy",
    "Moncler", "Fendi", "Bottega Veneta", "Alexander McQueen",
    "Dolce & Gabbana", "Burberry", "Loewe", "Autres / À vérifier"
]


SEARCH_ALIASES = {
    "64": {
        "tn": "Nike", "tn3": "Nike", "air max": "Nike", "vapormax": "Nike",
        "jordan": "Jordan", "air jordan": "Jordan",
        "samba": "Adidas", "gazelle": "Adidas", "campus": "Adidas",
        "gel nyc": "ASICS", "gel-kayano": "ASICS", "kayano": "ASICS",
        "cloud": "On Running", "cloudtilt": "On Running", "cloudmonster": "On Running",
        "new balance": "New Balance", "nb": "New Balance",
        "salomon": "Salomon", "ugg": "UGG", "crocs": "Crocs",
        "reebok": "Reebok", "converse": "Converse", "lacoste": "Lacoste",
        "puma": "Puma", "adidas": "Adidas", "nike": "Nike", "asics": "ASICS",
    },
    "3616": {
        "b22": "Dior", "b30": "Dior", "dior": "Dior",
        "lv": "Louis Vuitton", "lv runner": "Louis Vuitton", "louis vuitton": "Louis Vuitton",
        "prada cup": "Prada", "prada": "Prada",
        "chanel": "Chanel", "hermes": "Hermès", "hermès": "Hermès",
        "gucci": "Gucci", "balenciaga": "Balenciaga", "louboutin": "Louboutin",
        "versace": "Versace", "valentino": "Valentino", "givenchy": "Givenchy",
        "moncler": "Moncler", "fendi": "Fendi", "bottega": "Bottega Veneta",
        "mcqueen": "Alexander McQueen", "alexander mcqueen": "Alexander McQueen",
        "dolce": "Dolce & Gabbana", "gabbana": "Dolce & Gabbana", "d&g": "Dolce & Gabbana",
        "burberry": "Burberry", "loewe": "Loewe",
    }
}

def find_brand_from_query(query, tid):
    """Trouve une marque depuis un nom de marque ou un modèle tapé par le client."""
    tid = str(tid)
    q = (query or "").strip().casefold()
    if not q:
        return None
    allowed = REGULAR_BRANDS if tid == "64" else LUXURY_BRANDS

    # nom exact / partiel
    for brand in allowed:
        if brand == "Autres / À vérifier":
            continue
        if q == brand.casefold() or q in brand.casefold() or brand.casefold() in q:
            return brand

    # alias de modèle
    aliases = SEARCH_ALIASES.get(tid, {})
    # plus long alias d'abord, pour éviter "lv" avant "lv runner"
    for alias in sorted(aliases, key=len, reverse=True):
        if alias.casefold() in q:
            return aliases[alias]

    # réutilise la détection texte existante
    return _canonical_brand_from_text(query, tid)

import shutil
from pathlib import Path
from threading import RLock

BASE_CATALOG = Path("catalog.json")
DATA_DIR = Path(os.environ.get("DATA_DIR", "/data"))
if not DATA_DIR.exists():
    DATA_DIR = Path(".")
RUNTIME_CATALOG = DATA_DIR / "catalog_runtime.json"
CATALOG_LOCK = RLock()

BASE_BRANDS = Path("brand_catalog.json")
RUNTIME_BRANDS = DATA_DIR / "brand_catalog_runtime.json"
BRAND_LOCK = RLock()

def _load_brands():
    source = RUNTIME_BRANDS if RUNTIME_BRANDS.exists() else BASE_BRANDS
    if source.exists():
        with open(source, encoding="utf-8") as f:
            return json.load(f)
    return {"64": {}, "3616": {}}

BRAND_CATALOG = _load_brands()

def save_brands():
    with BRAND_LOCK:
        tmp = RUNTIME_BRANDS.with_suffix(".tmp")
        tmp.parent.mkdir(parents=True, exist_ok=True)
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(BRAND_CATALOG, f, ensure_ascii=False, indent=2)
        tmp.replace(RUNTIME_BRANDS)

def _load_catalog():
    source = RUNTIME_CATALOG if RUNTIME_CATALOG.exists() else BASE_CATALOG
    with open(source, encoding="utf-8") as f:
        return json.load(f)

CATALOG = _load_catalog()

with open("menu.json", encoding="utf-8") as f:
    MENU = json.load(f)

def save_catalog():
    """Persist the live catalogue safely. Use a Railway Volume mounted at /data."""
    with CATALOG_LOCK:
        tmp = RUNTIME_CATALOG.with_suffix(".tmp")
        tmp.parent.mkdir(parents=True, exist_ok=True)
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(CATALOG, f, ensure_ascii=False, indent=2)
        tmp.replace(RUNTIME_CATALOG)

def resolve_source_chat_id():
    global SOURCE_CHAT_ID
    try:
        r = requests.post(f"{API}/getChat", json={"chat_id": SOURCE_CHAT}, timeout=30).json()
        if r.get("ok"):
            SOURCE_CHAT_ID = r["result"]["id"]
            print(f"SOURCE OK: {SOURCE_CHAT} -> {SOURCE_CHAT_ID}", flush=True)
        else:
            print("SOURCE getChat error:", r, flush=True)
    except Exception as e:
        print("SOURCE resolve error:", repr(e), flush=True)

def is_source_message(m):
    chat = m.get("chat") or {}
    cid = chat.get("id")
    if SOURCE_CHAT_ID is not None:
        return cid == SOURCE_CHAT_ID
    username = chat.get("username")
    if SOURCE_CHAT.startswith("@") and username:
        return ("@" + username).lower() == SOURCE_CHAT.lower()
    return False

def message_kind(m):
    if m.get("photo"):
        return "photo"
    if m.get("video") or m.get("animation") or m.get("video_note"):
        return "video"
    doc = m.get("document") or {}
    mime = (doc.get("mime_type") or "").lower()
    if mime.startswith("image/"):
        return "photo"
    if mime.startswith("video/"):
        return "video"
    if m.get("text"):
        return "text"
    return None

def _canonical_brand_from_text(text, topic_id):
    """Détection gratuite depuis le texte/caption avant d'appeler la vision."""
    t = (text or "").lower()
    replacements = [
        (["new balance", "nb "], "New Balance"),
        (["on running", "on cloud", "cloudtilt", "cloudmonster", "cloud 5"], "On Running"),
        (["nike", "air max", "tn ", "tn3", "vapormax"], "Nike"),
        (["jordan", "air jordan"], "Jordan"),
        (["adidas", "samba", "gazelle", "campus"], "Adidas"),
        (["asics", "gel-kayano", "gel nyc"], "ASICS"),
        (["puma"], "Puma"), (["salomon"], "Salomon"), (["ugg"], "UGG"),
        (["crocs"], "Crocs"), (["reebok"], "Reebok"), (["converse"], "Converse"),
        (["lacoste"], "Lacoste"),
        (["dior", "b22", "b30"], "Dior"),
        (["louis vuitton", " lv ", "lv runner"], "Louis Vuitton"),
        (["prada", "prada cup"], "Prada"),
        (["chanel"], "Chanel"), (["hermès", "hermes"], "Hermès"),
        (["gucci"], "Gucci"), (["balenciaga"], "Balenciaga"),
        (["louboutin"], "Louboutin"), (["versace"], "Versace"),
        (["valentino"], "Valentino"), (["givenchy"], "Givenchy"),
        (["moncler"], "Moncler"), (["fendi"], "Fendi"),
        (["bottega"], "Bottega Veneta"), (["mcqueen", "alexander mcqueen"], "Alexander McQueen"),
        (["dolce", "gabbana", "d&g"], "Dolce & Gabbana"),
        (["burberry"], "Burberry"), (["loewe"], "Loewe"),
    ]
    allowed = REGULAR_BRANDS if str(topic_id) == "64" else LUXURY_BRANDS
    padded = f" {t} "
    for keys, brand in replacements:
        if brand not in allowed:
            continue
        if any(k in padded for k in keys):
            return brand
    return None

def _telegram_visual_file_id(m):
    """Photo HD ou miniature d'une vidéo."""
    photos = m.get("photo") or []
    if photos:
        return photos[-1].get("file_id")
    for field in ("video", "animation", "video_note", "document"):
        obj = m.get(field) or {}
        thumb = obj.get("thumbnail") or obj.get("thumb") or {}
        if thumb.get("file_id"):
            return thumb["file_id"]
    return None

def _download_telegram_file(file_id):
    if not file_id:
        return None, None
    info = api("getFile", file_id=file_id)
    if not info.get("ok"):
        return None, None
    path = (info.get("result") or {}).get("file_path")
    if not path:
        return None, None
    try:
        r = requests.get(f"https://api.telegram.org/file/bot{TOKEN}/{path}", timeout=60)
        r.raise_for_status()
        ext = Path(path).suffix.lower()
        mime = "image/png" if ext == ".png" else "image/jpeg"
        return r.content, mime
    except Exception as e:
        print("VISION download:", repr(e), flush=True)
        return None, None

def _extract_response_text(payload):
    # Responses API also exposes output_text in some SDKs, but raw HTTP returns output[].
    if isinstance(payload.get("output_text"), str):
        return payload["output_text"].strip()
    pieces = []
    for item in payload.get("output", []):
        for content in item.get("content", []) if isinstance(item, dict) else []:
            if isinstance(content, dict) and content.get("type") == "output_text":
                pieces.append(content.get("text", ""))
    return " ".join(pieces).strip()

def classify_brand_with_vision(m, topic_id):
    """Reconnaît la marque sur la photo ou sur la miniature de la vidéo."""
    text = (m.get("caption") or m.get("text") or "").strip()
    by_text = _canonical_brand_from_text(text, topic_id)
    if by_text:
        return by_text

    allowed = REGULAR_BRANDS if str(topic_id) == "64" else LUXURY_BRANDS
    if not OPENAI_API_KEY:
        print("VISION: OPENAI_API_KEY absente -> Autres / À vérifier", flush=True)
        return "Autres / À vérifier"

    file_id = _telegram_visual_file_id(m)
    raw, mime = _download_telegram_file(file_id)
    if not raw:
        return "Autres / À vérifier"

    import base64
    data_url = f"data:{mime};base64," + base64.b64encode(raw).decode("ascii")
    prompt = (
        "Tu classes une chaussure pour un catalogue Telegram. "
        "Observe uniquement la paire visible et identifie sa marque. "
        "Réponds avec UNE SEULE valeur exactement parmi cette liste : "
        + " | ".join(allowed)
        + ". Si le logo/modèle n'est pas suffisamment fiable, réponds exactement Autres / À vérifier. "
        "Ne devine pas."
    )
    try:
        r = requests.post(
            "https://api.openai.com/v1/responses",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": VISION_MODEL,
                "input": [{
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {"type": "input_image", "image_url": data_url, "detail": "low"},
                    ],
                }],
                "max_output_tokens": 40,
            },
            timeout=90,
        )
        payload = r.json()
        if not r.ok:
            print("VISION API ERROR:", payload, flush=True)
            return "Autres / À vérifier"
        answer = _extract_response_text(payload).strip()
        for brand in allowed:
            if answer.casefold() == brand.casefold():
                return brand
        # Tolérance si le modèle ajoute un peu de texte.
        for brand in allowed:
            if brand.casefold() in answer.casefold():
                return brand
    except Exception as e:
        print("VISION error:", repr(e), flush=True)
    return "Autres / À vérifier"

def register_brand_message(m, topic_id, message_id, kind):
    if str(topic_id) not in BRAND_TOPIC_IDS or kind not in ("photo", "video"):
        return
    brand = classify_brand_with_vision(m, topic_id)
    with BRAND_LOCK:
        topic_map = BRAND_CATALOG.setdefault(str(topic_id), {})
        ids = topic_map.setdefault(brand, [])
        if message_id not in ids:
            ids.append(message_id)
            ids.sort()
            save_brands()
    print(f"MARQUE ✅ topic={topic_id} message={message_id} -> {brand}", flush=True)

def register_new_content(m):
    """Ajoute automatiquement les NOUVEAUX textes, photos et vidéos du forum source."""
    if not is_source_message(m):
        return False

    kind = message_kind(m)
    if not kind:
        return False

    # In a Telegram forum, every message posted inside a topic carries message_thread_id.
    thread_id = m.get("message_thread_id")
    message_id = m.get("message_id")
    if not isinstance(thread_id, int) or not isinstance(message_id, int):
        print(f"AUTO IGNORE: message {message_id}, aucun message_thread_id", flush=True)
        return False

    key = str(thread_id)
    with CATALOG_LOCK:
        if key not in CATALOG:
            CATALOG[key] = {
                "title": f"Nouveau catalogue {thread_id}",
                "message_ids": [],
                "photos": 0,
                "videos": 0,
                "texts": 0,
            }

        c = CATALOG[key]
        ids = c.setdefault("message_ids", [])
        if message_id in ids:
            return False

        ids.append(message_id)
        ids.sort()

        if kind == "photo":
            c["photos"] = int(c.get("photos", 0)) + 1
        elif kind == "video":
            c["videos"] = int(c.get("videos", 0)) + 1
        else:
            c["texts"] = int(c.get("texts", 0)) + 1

        save_catalog()

    print(
        f"AUTO AJOUT ✅ topic={thread_id} message={message_id} type={kind}",
        flush=True
    )

    # V4 : les photos/vidéos des deux catalogues chaussures sont classées par marque.
    if key in BRAND_TOPIC_IDS and kind in ("photo", "video"):
        register_brand_message(m, key, message_id, kind)

    return True

def register_topic_title(m):
    created = m.get("forum_topic_created")
    if not created:
        return
    thread_id = m.get("message_thread_id") or m.get("message_id")
    if not isinstance(thread_id, int):
        return
    key = str(thread_id)
    title = (created.get("name") or f"Catalogue {thread_id}").strip()
    with CATALOG_LOCK:
        if key in CATALOG:
            CATALOG[key]["title"] = title
            save_catalog()

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
        [{"text":"📦  Articles disponibles sur place","callback_data":"articlesplace"}],
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
        logo_path = "web/logo.png" if os.path.exists("web/logo.png") else "logo.png"
        with open(logo_path, "rb") as f:
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
        "📦 Articles disponibles":"📦 Articles disponibles sur place",
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
                "texts": c.get("texts", 0),
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

    # V5.3 : recherche visible immédiatement dans la rubrique Chaussures.
    if group_id == "shoes":
        rows.append([{"text":"🔎 Rechercher Homme / Femme","callback_data":"searchbrand:64"}])
        rows.append([{"text":"🔎 Rechercher Chaussures de luxe","callback_data":"searchbrand:3616"}])

    for tid in g["topics"]:
        c=CATALOG.get(str(tid))
        if not c:
            continue
        p,v,t=c.get("photos",0),c.get("videos",0),c.get("texts",0)
        suffix=f"📷 {p}"
        if v:
            suffix += f" · 🎬 {v}"
        if t:
            suffix += f" · 📝 {t}"
        callback = f"brandroot:{tid}" if str(tid) in BRAND_TOPIC_IDS else f"cat:{tid}:0"
        rows.append([{"text":f"{clean_title(c['title'])}  |  {suffix}","callback_data":callback}])

    rows.append([{"text":"🏠 Accueil","callback_data":"home"}])
    return {"inline_keyboard":rows}

def brand_keyboard(tid):
    tid = str(tid)
    allowed = REGULAR_BRANDS if tid == "64" else LUXURY_BRANDS
    rows = [
        [{"text": "🔎 RECHERCHER une marque / un modèle", "callback_data": f"searchbrand:{tid}"}],
        [{"text": "👟 Tous les modèles", "callback_data": f"cat:{tid}:0"}],
    ]
    topic_map = BRAND_CATALOG.get(tid, {})

    # 2 marques par ligne pour aller plus vite
    current = []
    for idx, brand in enumerate(allowed):
        count = len(topic_map.get(brand, []))
        current.append({
            "text": f"{brand} · {count}",
            "callback_data": f"brand:{tid}:{idx}:0"
        })
        if len(current) == 2:
            rows.append(current)
            current = []
    if current:
        rows.append(current)

    rows.append([{"text":"⬅️ Chaussures","callback_data":"group:shoes"}])
    rows.append([{"text":"🏠 Accueil","callback_data":"home"}])
    return {"inline_keyboard": rows}

def send_brand_root(chat_id, tid):
    tid = str(tid)
    c = CATALOG.get(tid)
    if not c:
        return
    title = clean_title(c["title"])
    if tid == "64":
        intro = (
            "👟 <b>CHAUSSURES HOMME / FEMME</b>\n"
            "Choisissez directement votre marque 👇\n\n"
            "Nike · New Balance · On Running · Adidas · ASICS · Jordan · Puma…\n\n"
            "🔎 Vous pouvez aussi rechercher une marque ou un modèle."
        )
    else:
        intro = (
            "💎 <b>CHAUSSURES DE LUXE</b>\n"
            "Choisissez directement votre marque 👇\n\n"
            "Dior · Louis Vuitton · Prada · Chanel · Hermès · Gucci · Balenciaga…\n\n"
            "🔎 Vous pouvez aussi rechercher une marque ou un modèle."
        )
    return api(
        "sendMessage",
        chat_id=chat_id,
        text=intro,
        parse_mode="HTML",
        reply_markup=brand_keyboard(tid)
    )

def send_brand_page(chat_id, tid, brand_index, offset=0):
    tid = str(tid)
    allowed = REGULAR_BRANDS if tid == "64" else LUXURY_BRANDS
    if brand_index < 0 or brand_index >= len(allowed):
        return
    brand = allowed[brand_index]
    ids = BRAND_CATALOG.get(tid, {}).get(brand, [])
    total = len(ids)
    if total == 0:
        return api(
            "sendMessage",
            chat_id=chat_id,
            text=f"👟 <b>{brand}</b>\n\nAucun article classé dans cette marque pour le moment.",
            parse_mode="HTML",
            reply_markup={"inline_keyboard":[
                [{"text":"⬅️ Retour","callback_data":("articlesplace" if tid == "2" else f"brandroot:{tid}")}],
                [{"text":"🏠 Accueil","callback_data":"home"}]
            ]}
        )

    page = ids[offset:offset+PAGE_SIZE]
    end = offset + len(page)
    api("sendMessage", chat_id=chat_id,
        text=f"👟 <b>{brand}</b>\nAffichage {offset+1}–{end} sur {total}",
        parse_mode="HTML")
    res = api("copyMessages", chat_id=chat_id, from_chat_id=SOURCE_CHAT, message_ids=page)
    if not res.get("ok"):
        return api("sendMessage", chat_id=chat_id,
                   text=f"⚠️ Impossible d'afficher ces articles.\n<code>{res.get('description','Erreur')}</code>",
                   parse_mode="HTML")
    nav=[]
    if offset > 0:
        nav.append({"text":"⬅️ Précédents","callback_data":f"brand:{tid}:{brand_index}:{max(0,offset-PAGE_SIZE)}"})
    if end < total:
        nav.append({"text":"Suivants ➡️","callback_data":f"brand:{tid}:{brand_index}:{end}"})
    rows=[nav] if nav else []
    rows.append([{"text":"⬅️ Marques","callback_data":f"brandroot:{tid}"}])
    rows.append([{"text":"🏠 Accueil","callback_data":"home"}])
    return api("sendMessage", chat_id=chat_id,
        text=f"✅ <b>{end} / {total} articles {brand}</b>",
        parse_mode="HTML", reply_markup={"inline_keyboard":rows})

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
    p,v,t=c.get("photos",0),c.get("videos",0),c.get("texts",0)
    title=clean_title(c["title"])
    api("sendMessage", chat_id=chat_id,
        text=f"✨ <b>{title}</b>\n📷 {p} photos  ·  🎬 {v} vidéos  ·  📝 {t} textes\n\nAffichage {offset+1}–{end} sur {total}",
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
        text=f"✅ <b>{end} / {total} éléments affichés</b>",
        parse_mode="HTML", reply_markup={"inline_keyboard":rows})

def handle(u):
    # Telegram can deliver group content as message/edited_message/channel_post.
    m = (
        u.get("message")
        or u.get("edited_message")
        or u.get("channel_post")
        or u.get("edited_channel_post")
    )

    if m and (m.get("chat") or {}).get("type") in ("supergroup", "group", "channel"):
        register_topic_title(m)
        register_new_content(m)

    # Commands/web-app data are only handled from normal private messages.
    pm = u.get("message")
    if pm and (pm.get("chat") or {}).get("type") == "private":
        txt = pm.get("text", "")
        chat_id = pm["chat"]["id"]

        # V5 : réponse à la recherche marque/modèle
        if chat_id in SEARCH_WAITING and txt and not txt.startswith("/"):
            tid = SEARCH_WAITING.pop(chat_id)
            brand = find_brand_from_query(txt, tid)
            allowed = REGULAR_BRANDS if str(tid) == "64" else LUXURY_BRANDS
            if brand in allowed:
                idx = allowed.index(brand)
                return send_brand_page(chat_id, str(tid), idx, 0)
            return api(
                "sendMessage",
                chat_id=chat_id,
                text=(
                    "❌ Je n’ai pas trouvé cette marque ou ce modèle.\n\n"
                    "Exemples : <b>Nike</b>, <b>TN</b>, <b>New Balance</b>, "
                    "<b>On Running</b>, <b>Dior B30</b>, <b>LV Runner</b>."
                ),
                parse_mode="HTML",
                reply_markup={"inline_keyboard":[
                    [{"text":"🔎 Réessayer","callback_data":f"searchbrand:{tid}"}],
                    [{"text":"⬅️ Retour","callback_data":("articlesplace" if tid == "2" else f"brandroot:{tid}")}],
                    [{"text":"🏠 Accueil","callback_data":"home"}]
                ]}
            )

        if txt.startswith("/cancel"):
            SEARCH_WAITING.pop(chat_id, None)
            return api("sendMessage", chat_id=chat_id, text="✅ Recherche annulée.")

        if txt.startswith(("/start", "/menu")):
            return send_start(pm["chat"]["id"])
        if txt.startswith("/status"):
            total_new = 0
            runtime = RUNTIME_CATALOG.exists()
            return api(
                "sendMessage",
                chat_id=pm["chat"]["id"],
                text=(
                    "✅ <b>Détection automatique active</b>\n"
                    "📝 Textes + 📷 Photos + 🎬 Vidéos\n"
                    f"🤖 Classement marques : {'ACTIF' if OPENAI_API_KEY else 'clé IA manquante'}\n"
                    f"📡 Source : <code>{SOURCE_CHAT}</code>\n"
                    f"💾 Sauvegarde persistante : {'oui' if runtime else 'à initialiser au 1er ajout'}"
                ),
                parse_mode="HTML"
            )
        wad = pm.get("web_app_data")
        if wad:
            try:
                d = json.loads(wad.get("data", "{}"))
                if d.get("action") == "open_topic":
                    return send_page(pm["chat"]["id"], str(d["topic_id"]), 0)
            except Exception as e:
                print("web_app_data:", repr(e), flush=True)

    q = u.get("callback_query")
    if not q:
        return
    api("answerCallbackQuery", callback_query_id=q["id"])
    chat_id = q["message"]["chat"]["id"]
    d = q.get("data", "")
    if d == "home":
        return send_start(chat_id)
    if d.startswith("group:"):
        gid = d.split(":", 1)[1]
        g = next((x for x in MENU["groups"] if x["id"] == gid), None)
        if g:
            return api(
                "sendMessage",
                chat_id=chat_id,
                text=f"{g['emoji']} <b>{g['title']}</b>\n<i>{g['subtitle']}</i>",
                parse_mode="HTML",
                reply_markup=group_keyboard(gid)
            )
    if d == "articlesplace":
        return api(
            "sendMessage",
            chat_id=chat_id,
            text="📦 <b>Articles disponibles sur place</b>\n\nChoisissez :",
            parse_mode="HTML",
            reply_markup={"inline_keyboard":[
                [{"text":"🔎 Rechercher un article","callback_data":"searchbrand:2"}],
                [{"text":"📦 Voir tous les articles","callback_data":"cat:2:0"}],
                [{"text":"🏠 Accueil","callback_data":"home"}]
            ]}
        )
    if d.startswith("searchbrand:"):
        tid = d.split(":", 1)[1]
        SEARCH_WAITING[chat_id] = tid
        if tid == "2":
            title = "🔎 <b>Recherche — Articles disponibles sur place</b>"
            instruction = "Écrivez le nom de l'<b>article</b>, de la <b>marque</b> ou du <b>modèle</b> recherché."
            examples = "Exemples : sacoche, parfum, Nike, montre, casque."
        else:
            label = "Homme / Femme" if tid == "64" else "Luxe"
            title = f"🔎 <b>Recherche chaussures {label}</b>"
            instruction = "Écrivez maintenant une <b>marque</b> ou un <b>modèle</b>."
            examples = "Exemples : Nike, TN, New Balance, On Running, Dior B30, LV Runner."
        return api(
            "sendMessage",
            chat_id=chat_id,
            text=f"{title}\n\n{instruction}\n{examples}\n\nPour annuler : /cancel",
            parse_mode="HTML"
        )
    if d.startswith("brandroot:"):
        tid = d.split(":", 1)[1]
        return send_brand_root(chat_id, tid)
    if d.startswith("brand:"):
        _, tid, brand_index, off = d.split(":", 3)
        return send_brand_page(chat_id, tid, int(brand_index), int(off))
    if d.startswith("cat:"):
        _, tid, off = d.split(":", 2)
        return send_page(chat_id, tid, int(off))

def poll():
    offset=0
    while True:
        try:
            r=requests.get(
                f"{API}/getUpdates",
                params={"timeout": 50, "offset": offset},
                timeout=60
            ).json()
            for u in r.get("result",[]):
                offset=u["update_id"]+1
                handle(u)
        except Exception as e:
            print("Polling:",repr(e),flush=True)
            time.sleep(3)

def main():
    if not TOKEN:
        raise SystemExit("BOT_TOKEN manquant")
    resolve_source_chat_id()
    print(f"Catalogue dynamique: {RUNTIME_CATALOG}", flush=True)
    print(f"AUTO {BUILD_VERSION}: RECHERCHE VISIBLE Homme/Femme + Luxe + Articles sur place = ACTIVÉ", flush=True)
    print("TOPIC 2: Articles disponibles sur place = ACTIVÉ", flush=True)
    print(f"VISION MARQUES: {'ACTIVÉ' if OPENAI_API_KEY else 'OPENAI_API_KEY MANQUANTE'} ({VISION_MODEL})", flush=True)
    threading.Thread(target=poll,daemon=True).start()
    port=int(os.environ.get("PORT","8080"))
    app.run(host="0.0.0.0",port=port,threaded=True)

if __name__=="__main__":
    main()
