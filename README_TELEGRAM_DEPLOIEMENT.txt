LE COIN MALIN 34 — CORRECTION TELEGRAM — NOUVEAUTÉS + RATTRAPAGE HISTORIQUE

1. Railway doit lancer : python bot.py
2. Variable obligatoire : BOT_TOKEN = token de @lecoinmalin34_catalogue_photo

SOURCE TELEGRAM :
- Le result.json fourni identifie le supergroupe historique Lecoinmalin34w
  avec l'id d'export 3782657059.
- La Bot API utilise l'id -1003782657059 pour ce supergroupe.
- @Lecoinmalin34a reste utilisé pour les liens publics du catalogue.
- Le code accepte SOURCE_CHAT ou TELEGRAM_SOURCE_CHAT.

NOUVEAUTÉS + CATÉGORIE :
- Un nouveau message/photo/vidéo reçu dans un topic est ajouté à ce topic.
- Le même message est automatiquement visible dans « Nouveautés ».
- Exemple : une paire postée dans « Chaussures de luxe » (3616)
  reste dans « Chaussures » / la rubrique luxe et apparaît aussi dans « Nouveautés ».

RATTRAPAGE HISTORIQUE :
- Au démarrage, le bot lit d'abord result.json (le dernier export fourni),
  sinon result(2).json.
- Les anciens messages déjà présents sur Telegram mais absents de CATALOG
  sont ajoutés à leur topic automatiquement.
- Les doublons sont ignorés.
- Les mêmes IDs alimentent ensuite « Nouveautés » automatiquement.
- Le rattachement d'un message à son topic est reconstruit à partir de
  topic_created + reply_to_message_id présents dans l'export.
- Les messages pour lesquels l'export ne permet pas de retrouver un topic
  sont laissés de côté plutôt que d'être classés au hasard.

AU DÉMARRAGE, LES LOGS DOIVENT MONTRER :
- TELEGRAM BOT OK: @lecoinmalin34_catalogue_photo ...
- SOURCE OK: -1003782657059 -> ...
- SOURCE BOT MEMBERSHIP: status=...
- TELEGRAM WEBHOOK RESET: {'ok': True, ...}
- BACKFILL ✅ fichier=result.json ajoutés=... topics=... médias_sans_topic=...

SI LES NOUVEAUX MESSAGES N'ARRIVENT PAS :
- Si SOURCE BOT MEMBERSHIP affiche status=member ou restricted,
  désactiver Group Privacy dans @BotFather ou donner les droits administrateur.
- Si les logs affichent HTTP=409, une autre instance du même bot utilise encore
  le token : arrêter l'ancien service Railway.

CLASSEMENT AUTOMATIQUE :
- Le bot analyse le texte et la légende de chaque nouvelle publication.
- S'il détecte une catégorie plus précise que le topic dans lequel le post a été placé,
  il rattache automatiquement l'ID du message à cette catégorie dans le catalogue.
- Les indices prioritaires comprennent notamment : iPhone/AirPods/PC gamer -> High-Tech ;
  Dyson -> Dyson ; Coques -> Coques téléphone ; Meta -> Lunettes Meta ;
  Dior B22/B30/LV/prada/etc. + indice chaussure -> Chaussures de luxe ;
  Nike/Jordan/Adidas/etc. + indice chaussure -> Chaussures homme/femme ;
  G-Shock / montres / bracelets -> Montres & Bijoux ;
  casquettes/sacs/lunettes/parfums/valises -> Accessoires ;
  doudounes/ensembles/maillots/bonnets/vêtements -> les topics vêtements correspondants.
- Une publication automatiquement reclassée reste affichée dans « Nouveautés » sans doublon,
  car la vue Nouveautés déduplique les message_ids.
- Le bot ne déplace pas le message dans Telegram : il corrige son classement dans le catalogue.
- Lorsqu'il n'y a pas assez d'indices textuels, le topic Telegram d'origine est conservé.
