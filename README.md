# V5.14 — RECHERCHE INSTANTANÉE

- Dior / Nike / On Running / ASICS : la recherche lit directement le cache, donc aucun scan au moment de la recherche.
- `/indexchaussures` lance une seule indexation des anciens messages Homme/Femme + Luxe en arrière-plan.
- Les nouveaux articles continuent d'être ajoutés automatiquement au cache.
- Bouton d'arrêt de l'indexation conservé.
- 100 % gratuit : classement via texte/légende/modèles connus.

Après déploiement, envoie `/indexchaussures` UNE fois et laisse l'indexation finir.
Ensuite les recherches sont instantanées.

Log attendu :
`AUTO V5.14-INSTANT-CACHE: recherche CACHE instantanée + indexation arrière-plan = ACTIVÉ`
