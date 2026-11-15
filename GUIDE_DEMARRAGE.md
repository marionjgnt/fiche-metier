# Guide de démarrage — pas à pas

Le site est prêt dans ce dossier. Il te reste à créer tes comptes, ta clé d'accès et à mettre le site
en ligne : ça, personne ne peut le faire à ta place. Compte environ 30 minutes.

À chaque étape, si quelque chose ne marche pas ou si un message d'erreur apparaît, fais une capture
d'écran ou copie-colle le texte, et on regarde ensemble.

---

## Étape 1 — Compte GitHub (5 min)

1. Va sur https://github.com/signup et crée un compte.
2. Installe **GitHub Desktop** : https://desktop.github.com/
   (c'est l'application qui t'évite de taper des commandes : tu cliques sur « Commit » puis « Push »).
3. Ouvre GitHub Desktop et connecte-toi avec ton compte GitHub.

## Étape 2 — Créer ton dépôt et y mettre le site (10 min)

1. Sur github.com, clique sur **New repository** (bouton vert ou « + » en haut à droite).
2. Nom : `marketing-digital-marche`. Coche **Public** (nécessaire pour que le site soit en ligne gratuitement).
3. Ne coche **pas** « Add a README ». Clique sur **Create repository**.
4. Sur la page du dépôt vide, clique sur **Set up in Desktop** / **Open with GitHub Desktop**,
   puis choisis où le ranger sur ton Mac (par exemple dans Documents) et clique sur **Clone**.
5. Ouvre le dossier que GitHub Desktop vient de créer (`marketing-digital-marche`) dans le Finder.
6. Copie dedans **tout le contenu** de ce dossier-ci (y compris les dossiers `data`, `scripts` et `.github`).
   ⚠️ Le dossier `.github` est caché sur Mac : dans le Finder, appuie sur **Cmd + Maj + .** pour voir
   les fichiers cachés avant de copier.
7. Retourne dans GitHub Desktop : la liste des fichiers ajoutés apparaît à gauche.
   En bas à gauche, écris un message (ex. « Première version du site »), clique sur **Commit to main**,
   puis en haut sur **Publish branch** ou **Push origin**.
8. Rafraîchis la page de ton dépôt sur github.com : tes fichiers doivent y être.

## Étape 3 — Ta clé d'accès à l'API France Travail (5 min)

1. Va sur https://francetravail.io/ et crée un compte.
2. Une fois connecté(e), va dans **Mes applications** puis **Créer une application**.
3. Dans la liste des API, ajoute **« Offres d'emploi v2 »**.
4. Note l'**identifiant client** et la **clé secrète** dans un endroit sûr (gestionnaire de mots de passe).

⚠️ Ne colle **jamais** ces identifiants dans un fichier du dossier, ni dans un message à quelqu'un.
Ils vont uniquement dans les « secrets » GitHub (étape suivante).

## Étape 4 — Brancher la clé sur GitHub (5 min)

1. Sur la page de ton dépôt, va dans **Settings** → **Secrets and variables** → **Actions**.
2. Clique sur **New repository secret** :
   - Name : `FRANCE_TRAVAIL_CLIENT_ID` → colle ton identifiant client → **Add secret**.
3. Recommence avec :
   - Name : `FRANCE_TRAVAIL_CLIENT_SECRET` → colle ta clé secrète → **Add secret**.
   (Les noms doivent être écrits exactement comme ça, en majuscules.)

## Étape 5 — Lancer la première collecte (3 min)

1. Va dans l'onglet **Actions** de ton dépôt. Si GitHub te le demande, clique sur
   **I understand my workflows, go ahead and enable them**.
2. Clique à gauche sur **Veille France Travail**, puis à droite sur **Run workflow** → **Run workflow**.
3. Attends 1 à 2 minutes et rafraîchis. Une coche verte ✅ = c'est bon : un nouveau commit
   « Veille automatique : données du … » apparaît avec les offres dans `data/`.
   Une croix rouge ❌ = clique dessus pour voir le message (souvent une clé mal copiée) et envoie-le-moi.
4. Dans GitHub Desktop, clique sur **Fetch origin** puis **Pull origin** pour récupérer ces données
   sur ton Mac aussi.

Ensuite, la collecte se relance **toute seule chaque matin**.

## Étape 6 — Mettre le site en ligne (2 min)

1. Dans ton dépôt : **Settings** → **Pages**.
2. « Source » : **Deploy from a branch**. Branche : `main`, dossier : `/ (root)`. **Save**.
3. Après 1 à 2 minutes, l'adresse apparaît en haut de la page, du type
   `https://ton-pseudo.github.io/marketing-digital-marche/`

## Étape 7 — Écrire ta partie (le plus important)

Le site affiche des cadres « À compléter » tant que ces fichiers sont vides :

- **`data/formation.json`** : liste les outils et compétences que tu as déjà vus ou pratiqués en
  alternance (ex. `"Google Ads"`, `"Meta Ads"`, `"HubSpot"`, `"Événementiel"`, `"Canva"`). Le site
  marquera alors chaque outil « déjà vu » ou « à acquérir ».
- **`data/contenu.json`** : ta source sur l'évolution du métier, les professionnels rencontrés, ton
  repérage LinkedIn, tes 3 actions datées et ta position. Le modèle `data/contenu_EXEMPLE.json` montre
  quoi mettre où.

Tu peux modifier ces fichiers directement sur github.com (ouvre le fichier → icône crayon ✏️ →
**Commit changes**), ou sur ton Mac puis Commit + Push dans GitHub Desktop.

## Optionnel — Repère de salaire externe

Le site d'origine comparait ses salaires à la fiche MétierScope du métier. Pour l'activer ici, relève les
chiffres d'une fiche MétierScope proche du marketing digital (https://candidat.francetravail.fr/metierscope)
et dis-les-moi :
je te montrerai où les mettre dans `scripts/analyse_offres.py`.

---

## Ta liste de contrôle

- [ ] Compte GitHub + GitHub Desktop
- [ ] Dépôt `marketing-digital-marche` créé, fichiers poussés
- [ ] Compte francetravail.io + application « Offres d'emploi v2 »
- [ ] Les 2 secrets ajoutés sur GitHub
- [ ] Première collecte lancée, coche verte
- [ ] GitHub Pages activé, adresse du site notée
- [ ] `formation.json` et `contenu.json` remplis
