# V5.15 — FIX CACHE

Correction de l'erreur Railway :
`Polling: NameError("name 'text' is not defined")`

- `/indexchaussures` est maintenant traité dans le contexte du message Telegram.
- Les recherches clients restent basées sur le cache et ne lancent plus de scan.
- `/indexchaussures` lance l'indexation Homme/Femme + Luxe une seule fois en arrière-plan.
- Le bouton d'arrêt reste disponible.

Log attendu :
`AUTO V5.15-FIX-CACHE: cache instantané + /indexchaussures FIXÉ = ACTIVÉ`
