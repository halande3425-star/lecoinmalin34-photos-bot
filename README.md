# LE COIN MALIN 34 — V5.1

# LE COIN MALIN 34 — V5 MARQUES + RECHERCHE

# LE COIN MALIN 34 — AUTO V4 MARQUES

Nouveautés :
- Chaussures Homme/Femme : sous-menu par marque
- Chaussures de luxe : sous-menu par marque
- reconnaissance automatique sur les nouvelles PHOTOS
- reconnaissance automatique sur la miniature des nouvelles VIDÉOS
- texte/caption utilisé en priorité quand la marque est déjà écrite
- catégorie `Autres / À vérifier` si la marque n'est pas assez sûre
- le catalogue texte/photos/vidéos V3 reste actif

## Variables Railway
- `BOT_TOKEN`
- `SOURCE_CHAT=@Lecoinmalin34`
- `OPENAI_API_KEY` : clé API OpenAI pour la reconnaissance visuelle
- optionnel `VISION_MODEL=gpt-5.6-luna`
- optionnel `DATA_DIR=/data`

## Volume Railway
Monter un Volume sur `/data` pour conserver :
- `catalog_runtime.json`
- `brand_catalog_runtime.json`

## Important
Telegram Bot API ne permet pas au bot de relire visuellement toutes les anciennes photos du groupe.
Les anciennes chaussures restent disponibles via `Tous les modèles`.
Les NOUVELLES photos/vidéos reçues après V4 sont automatiquement classées par marque.


## Nouveautés V5
- `Chaussures homme/femme` (topic 64) ouvre d'abord un menu de marques.
- `Chaussures de luxe` (topic 3616) ouvre d'abord un menu de marques luxe.
- Bouton `🔎 Rechercher une marque / un modèle` dans les deux menus.
- Recherche par marque ou modèle : `Nike`, `TN`, `New Balance`, `On Running`, `Dior B30`, `LV Runner`, etc.
- Marques affichées 2 par ligne pour réduire le défilement.
- `Tous les modèles` reste disponible.
- Les nouvelles photos/vidéos continuent d'être classées automatiquement comme en V4 si la clé Vision est configurée.


## Ajout V5.1
- Bouton `📦 Articles disponibles sur place` directement sur l’accueil.
- Ouvre le topic Telegram `https://t.me/Lecoinmalin34/2`.
- Marques + recherche conservées pour Homme/Femme et Luxe.
