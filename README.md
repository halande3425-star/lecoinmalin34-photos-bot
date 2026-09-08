# LE COIN MALIN 34 — AUTO V3

Corrections :
- détecte automatiquement les nouveaux messages texte
- détecte automatiquement les nouvelles photos
- détecte automatiquement les nouvelles vidéos
- accepte aussi edited_message / channel_post
- identifie le groupe source avec son ID Telegram
- ajoute `Bonnet d’hiver homme femme ☃️` dans Vêtements
- inclut les anciens textes présents dans l’export `result(2).json`

## IMPORTANT pour la détection automatique
Le bot doit rester administrateur dans `Lecoinmalin34`.

Si Telegram ne transmet toujours pas les messages du groupe :
BotFather → `/setprivacy` → choisir le bot → **Disable**.

## Railway
Variables :
- BOT_TOKEN
- SOURCE_CHAT=@Lecoinmalin34

Pour garder les nouveaux ajouts après un redéploiement Railway :
ajouter un Volume monté sur `/data`.

Commande de test dans le bot privé :
`/status`
