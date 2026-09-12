# LE COIN MALIN 34 — V5.5 DÉTECTION DES MARQUES

Cette version classe automatiquement les NOUVELLES photos/vidéos des deux rubriques :
- `Chaussures homme/femme` (topic 64)
- `Chaussures de luxe` (topic 3616)

La recherche `Dior`, `Hermès`, `ASICS`, `Nike`, etc. renvoie ensuite uniquement les médias classés dans cette marque.

## Important
Pour reconnaître une marque uniquement depuis l'image, Railway doit avoir la variable :
`OPENAI_API_KEY`

Dans les logs Railway, vérifier :
`VISION DETECTION: ACTIVÉE`

Les anciens médias déjà présents avant que le bot les reçoive ne peuvent pas être relus automatiquement par le Bot API Telegram. Ils peuvent être classés si :
- ils sont modifiés/republiés et donc reçus de nouveau par le bot, ou
- on refait un export Telegram avec les médias pour une migration complète.

## Log attendu
`AUTO V5.5-VISION-BRANDS: détection images + recherche marques Homme/Femme & Luxe = ACTIVÉ`
