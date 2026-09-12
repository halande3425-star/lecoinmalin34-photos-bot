# V5.18 — VISION LOCALE GRATUITE POUR LES CHAUSSURES

## Ce que fait cette version
- Analyse réellement les pixels des photos avec un modèle CLIP local.
- Aucun appel OpenAI.
- Analyse les anciens médias des topics :
  - 64 = Chaussures Homme / Femme
  - 3616 = Chaussures de luxe
- Si une paire Dior/LV/Hermès/etc. se trouve dans Homme/Femme, elle est classée dans Luxe.
- Si une TN/Nike/ASICS/etc. se trouve dans Luxe, elle est classée dans Homme/Femme.
- Le résultat est sauvegardé dans `/data/brand_catalog_runtime.json`.
- Après indexation, les recherches `Dior`, `TN`, `ASICS`, etc. sont instantanées.

## Une seule commande après déploiement
Dans le chat privé du bot :
`/indeximages`

Le premier lancement télécharge le modèle local, puis analyse toutes les images accessibles.
Les copies temporaires Telegram sont supprimées automatiquement.

## Railway
Un volume persistant monté sur `/data` est recommandé.

Log attendu :
`AUTO V5.18-LOCAL-VISION: vision locale images + reclassement Homme/Femme/Luxe = ACTIVÉ`

## Important
La vision locale est gratuite côté API, mais une reconnaissance d'image n'est jamais garantie à 100 %.
Le bot analyse réellement toutes les images accessibles et garde son meilleur classement en cache.
