LE COIN MALIN 34 — CORRECTION TELEGRAM

1. Railway doit lancer : python bot.py
2. Variables obligatoires :
   BOT_TOKEN = token de @lecoinmalin34_catalogue_photo
   TELEGRAM_SOURCE_CHAT = @Lecoinmalin34a

Au démarrage, les logs doivent afficher :
- TELEGRAM BOT OK: @lecoinmalin34_catalogue_photo ...
- TELEGRAM WEBHOOK RESET: {'ok': True, ...}
- SOURCE OK: @Lecoinmalin34a -> ...

Quand /start est envoyé au bot, les logs doivent afficher :
- TELEGRAM UPDATES: 1

Si les logs affichent HTTP=409, une autre instance du même bot utilise encore
le token. Il faut arrêter l'ancien service Railway avant de relancer celui-ci.
