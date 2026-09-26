# LE COIN MALIN 34 — Catalogue Telegram Bot (fix)

Ce bot transforme le forum Telegram source en catalogue dynamique.

## Ce qu'il fait
- importe les topics depuis `result.json` ;
- conserve les publications associées à leur topic ;
- affiche les publications dans le bot avec `copyMessage`, donc les vraies photos/vidéos Telegram sont recopiées sans stocker de faux chemins locaux ;
- détecte automatiquement les nouveaux messages et nouvelles images/vidéos du groupe ;
- détecte les nouveaux topics du forum ;
- garde la navigation Accueil → Topic → Publications avec pagination ;
- fournit `/status` pour contrôler le nombre de topics/publications/médias ;
- expose `/health` et `/api/topics` pour Railway.

## Variables Railway
- `BOT_TOKEN` : token du bot créé via BotFather (secret)
- `SOURCE_CHAT_ID` : `-1003782657059` par défaut
- `SOURCE_CHAT_USERNAME` : `Lecoinmalin34w` par défaut
- `ADMIN_USER_ID` : facultatif, pour réserver `/status`
- `DATA_DIR=/data` conseillé sur Railway avec volume persistant
- `PORT=8080`

## Telegram
Le nouveau bot doit être administrateur dans le groupe/forum source et la confidentialité du bot doit être désactivée dans BotFather (`/setprivacy` → Disable) pour recevoir les nouveaux messages.

Le bot n'a pas besoin de télécharger les photos sur le disque : lorsqu'un utilisateur ouvre un topic, le bot utilise l'API Telegram `copyMessage` pour afficher directement le vrai média du message source. Ainsi, les nouvelles photos ajoutées dans Telegram sont prises en compte automatiquement.

## Déploiement
Start command : `python bot.py`
Healthcheck : `/health`
