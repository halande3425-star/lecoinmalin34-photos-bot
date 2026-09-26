# LE COIN MALIN 34 — Boutique Telegram miroir

Source catalogue: `result(2).json` (4042 messages). Les 42 topics sont conservés dans `telegram_catalog.json`.

## Railway variables
- `BOT_TOKEN` : token du nouveau bot BotFather
- `TELEGRAM_SOURCE_CHAT` : `@Lecoinmalin34`
- `TELEGRAM_SOURCE_CHAT_ID` : `-1003782657059`
- `ADMIN_PASSWORD` : secret admin
- `SHOP_SECRET_KEY` : secret aléatoire
- `BANK_TRANSFER_INSTRUCTIONS` : instructions de virement privées
- `SHOP_DB` : optionnel, par défaut `/data/shop.db` si le volume existe
- `TELEGRAM_MEDIA_DIR` : optionnel, par défaut `/data/telegram_media`

Le serveur utilise `copyMessage` vers le chat source, récupère le vrai `file_id`, appelle `getFile`, télécharge le média puis supprime immédiatement le message temporaire. Les médias sont mis en cache dans `/data/telegram_media`.

Le service démarre avec `python shop.py` et `/health` renvoie 200.
