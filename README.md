# Marketing digital & opérationnel, compté

Site qui compte le marché du métier de **chargé(e) de marketing digital et opérationnel** à partir des offres d'emploi
publiées sur France Travail, et qui se met à jour seul chaque mardi et vendredi.

> **Origine du code.** Ce projet est une adaptation du projet
> [« Community manager, compté »](https://github.com/lolabodoin-design/community-manager-marche) :
> même chaîne de collecte, d'analyse et d'affichage, transposée à un autre métier.

## Le métier ciblé

- **Intitulé :** Chargé(e) de marketing digital et opérationnel (marketing de performance, marketing client, événementiel)
- **Requêtes :** mots-clés « marketing digital », « marketing operationnel », « webmarketing » (pas de code ROME)
- **Sélection :** seules les offres dont l'intitulé contient « marketing digital » ou « marketing opérationnel » (ou web,
  e-marketing, digital marketing) sont gardées ; les autres sont comptées puis écartées.

## Ce qui a changé par rapport au projet d'origine

| Élément | Projet d'origine | Cette version |
|---|---|---|
| Sélection | code ROME E1101 + mots-clés | mots-clés + filtre sur l'intitulé (pas de code ROME) |
| Mots-clés | « community manager » | « marketing digital », « marketing operationnel », « webmarketing » |
| Outils et compétences repérés | réseaux sociaux, création visuelle… | acquisition (Google Ads, Meta Ads), data (GA4, Looker Studio), CRM et automation, SEO et e-commerce, événementiel, print… |
| Marché caché (63) | agences de pub, régie, conseil en communication | agences de pub, conseil en communication, études de marché, e-commerce |
| Repère salaire MétierScope | fiche Community manager | à renseigner (voir `scripts/analyse_offres.py`) |
| Textes personnels | ceux de l'autrice | vides, à écrire (`data/contenu.json`, `data/formation.json`) |

## Fichiers à remplir soi-même

- `data/contenu.json` : source sur l'évolution du métier, professionnels rencontrés, repérage LinkedIn,
  plan d'action, position. Un modèle commenté est dans `data/contenu_EXEMPLE.json`.
- `data/formation.json` : outils et compétences déjà vus (pour marquer « déjà vu » / « à acquérir »).

## Comment les données sont produites

| Étape | Script | Sortie |
|---|---|---|
| Collecte des offres (API France Travail « Offres d'emploi v2 ») | `scripts/fetch_offres.py` | `data/offres.json` |
| Collecte des entreprises du 63 (API Recherche d'entreprises, sans clé) | `scripts/fetch_entreprises.py` | `data/entreprises.json` |
| Calculs (volumes, zones, contrats, salaires, outils, recruteurs, marché caché) | `scripts/analyse_offres.py` | `data/analyse.json`, `data/offres_site.json`, `data/historique.json`, `data/csv/*.csv` |

La GitHub Action `.github/workflows/veille.yml` enchaîne ces trois scripts chaque mardi et vendredi à 5 h UTC (6 h à Paris en hiver).

## Règle RGPD

- Seules des données d'annonces et d'entreprises publiques sont conservées.
- Le champ `contact` de l'API France Travail (recruteurs) est supprimé dès la collecte.
- Aucun dirigeant ni salarié n'est nommé ; les entreprises opposées à la diffusion commerciale sont exclues.
- Les clés API sont dans les *secrets* GitHub, jamais dans le dépôt (`.env` est ignoré).

## Limites

- Seules les offres diffusées par France Travail (et ses partenaires) sont visibles.
- Le filtre sur l'intitulé garde assistant, chargé et responsable : le niveau de poste varie.
- Une offre de marketing au titre différent (ex. « chargé de marketing » seul) est écartée.
- Outils et compétences sont repérés par mots-clés : une mention n'est pas une exigence.
- Les salaires ne sont comptés que lorsqu'ils sont affichés.

## Sources

- API France Travail — Offres d'emploi v2 (https://francetravail.io/data/api/offres-emploi)
- API Recherche d'entreprises — data.gouv.fr (https://recherche-entreprises.api.gouv.fr)
