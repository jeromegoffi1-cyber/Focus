# Focus

Entraînement quotidien de la concentration et de la visualisation : la flamme, le point fixe, les respirations, les objectifs vécus comme atteints, le corps, la journée idéale, la diète mentale, la canalisation de l'énergie, et un bouton « Je décroche » pour les moments de procrastination.

L'appli tient dans `index.html`. Les autres fichiers servent à l'installer sur le téléphone et à l'utiliser hors connexion.
`audio/` contient la voix du guide (Damien, ElevenLabs), une phrase par fichier, et `audio/index.json` la liste des phrases enregistrées.
Si un texte de l'appli change, relancer `outils/gen_voix.py` (mode d'emploi en tête du script) pour réenregistrer les phrases nouvelles.
Les données restent dans le navigateur du téléphone (export possible dans Réglages).

## Mettre en ligne sur GitHub Pages

1. Créer un dépôt public, par exemple `Focus`.
2. « Add file », « Upload files », déposer les 7 fichiers de ce dossier, puis « Commit changes ».
3. Settings, Pages : Source « Deploy from a branch », branche `main`, dossier `/ (root)`, Save.
4. Une à deux minutes plus tard, l'appli est à l'adresse `https://<compte>.github.io/Focus/`.
5. Sur iPhone, l'ouvrir dans Safari, bouton Partager, « Sur l'écran d'accueil ».

Pour une mise à jour, remplacer `index.html` dans le dépôt : l'appli installée la récupère à l'ouverture suivante.
