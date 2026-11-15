#!/usr/bin/env python3
"""
Récupère les offres d'emploi d'un métier via l'API France Travail
("Offres d'emploi v2") et écrit le résultat dans data/offres.json.

Les métiers visés sont le marketing digital ET le marketing opérationnel. Pas de code ROME :
on cherche par mots-clés, puis on ne garde que les offres dont l'INTITULÉ
correspond au métier (filtre FILTRE_INTITULE ci-dessous).
  1. mots-clés « marketing digital »       -> requête obligatoire
  2. mots-clés « marketing operationnel »  -> requête complémentaire
  3. mots-clés « marketing numerique »     -> requête complémentaire
  4. mots-clés « webmarketing »            -> requête complémentaire
  Si une requête complémentaire échoue, la collecte continue (et l'échec est
  noté dans le fichier de sortie).

Adapté du projet « community-manager-marche » (lolabodoin-design).

On conserve le texte des offres pour pouvoir y compter les compétences et les
outils (scripts/analyse_offres.py). On NE conserve PAS le champ « contact » de
l'API (noms et coordonnées de recruteurs) : ce sont des données personnelles.

Identifiants (jamais versionnés) :
    FRANCE_TRAVAIL_CLIENT_ID
    FRANCE_TRAVAIL_CLIENT_SECRET
En local : fichier .env (voir .env.example). En GitHub Actions : secrets du dépôt.
"""

import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# --- Configuration du métier -------------------------------------------------
# Mots-clés séparés par « ; ». Sans accents : l'API refuse certains caractères.
MOTS_CLES = [m.strip() for m in os.environ.get(
    "MOTS_CLES", "marketing digital;marketing operationnel;marketing numerique;webmarketing").split(";") if m.strip()]
# Seules les offres dont l'intitulé correspond à cette expression sont gardées
# (comparaison sans accents ni majuscules). Les autres sont comptées puis écartées.
FILTRE_INTITULE = re.compile(os.environ.get(
    "FILTRE_INTITULE",
    r"marketing\W+(?:digital|numerique|web|online|en ligne|operationnel)|digital\W+marketing|web\W*marketing|e-?marketing"))
REQUETE_LABEL = os.environ.get("REQUETE_LABEL", "chargé(e) de marketing digital et opérationnel")

# L'API limite à 150 offres par appel et à 1 150 offres par requête.
MAX_OFFRES = int(os.environ.get("MAX_OFFRES", "1150"))
TAILLE_PAGE = 150
DESCRIPTION_MAX = 8000  # caractères conservés par offre

TOKEN_URL = "https://entreprise.pole-emploi.fr/connexion/oauth2/access_token?realm=%2Fpartenaire"
SEARCH_URL = "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_FILE = ROOT / "data" / "offres.json"

REQUETES = [
    {"label": f"mots-clés « {m} »", "params": {"motsCles": m}, "obligatoire": i == 0}
    for i, m in enumerate(MOTS_CLES)
]


def fold(s: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def signaler(message: str) -> None:
    """Affiche une erreur lisible. Sur GitHub Actions, elle apparaît aussi en
    « annotation » sur la page du run (et dans l'e-mail d'échec)."""
    message = " ".join(str(message).split())[:600]
    print(message, file=sys.stderr)
    if os.environ.get("GITHUB_ACTIONS"):
        print(f"::error title=Collecte France Travail::{message}")


def get_token(client_id: str, client_secret: str) -> str:
    """Jeton OAuth2 (client_credentials). Le scope doit se terminer par
    application_<client_id>, sinon l'API répond 400."""
    resp = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": f"api_offresdemploiv2 o2dsoffre application_{client_id}",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )
    if not resp.ok:
        signaler(f"Connexion à l'API refusée ({resp.status_code}) : {resp.text[:300]}. "
                 "Vérifier l'identifiant et la clé (secrets GitHub) et que l'API « Offres d'emploi v2 » "
                 "est bien ajoutée à l'application sur francetravail.io.")
    resp.raise_for_status()
    return resp.json()["access_token"]


def fetch_requete(token: str, params_requete: dict) -> tuple[list[dict], int | None]:
    """Pagine par blocs de 150. Renvoie (offres, total annoncé par l'API)."""
    headers = {"Authorization": f"Bearer {token}"}
    offres: list[dict] = []
    total_api = None
    debut = 0
    while len(offres) < MAX_OFFRES and debut <= 1000:
        params = dict(params_requete)
        params["range"] = f"{debut}-{debut + TAILLE_PAGE - 1}"
        params["sort"] = 1  # plus récentes d'abord
        resp = requests.get(SEARCH_URL, headers=headers, params=params, timeout=30)
        if resp.status_code == 204:
            break
        if resp.status_code not in (200, 206):
            signaler(f"Recherche refusée par l'API ({resp.status_code}, paramètres {params_requete}) : {resp.text[:300]}")
            resp.raise_for_status()
        # En-tête du type « Content-Range: offres 0-149/2345 » : total réel.
        m = re.search(r"/(\d+)\s*$", resp.headers.get("Content-Range", ""))
        if m:
            total_api = int(m.group(1))
        page = resp.json().get("resultats", [])
        if not page:
            break
        offres.extend(page)
        if len(page) < TAILLE_PAGE:
            break
        debut += TAILLE_PAGE
        time.sleep(0.2)  # l'API tolère 10 appels/seconde
    return offres[:MAX_OFFRES], total_api


def departement(lieu: dict) -> str | None:
    """Code département : depuis le libellé (« 63 - CLERMONT-FERRAND »),
    sinon depuis le code postal."""
    m = re.match(r"^\s*(\d{2,3}|2[AB])\s*(?:-|$)", lieu.get("libelle") or "")
    if m:
        return m.group(1)
    cp = (lieu.get("codePostal") or "").strip()
    if len(cp) == 5 and cp.isdigit():
        if cp.startswith(("97", "98")):
            return cp[:3]
        if cp.startswith("20"):
            return "2A" if int(cp) < 20200 else "2B"
        return cp[:2]
    return None


def simplifier(offre: dict, label: str) -> dict:
    lieu = offre.get("lieuTravail") or {}
    entreprise = offre.get("entreprise") or {}
    salaire = offre.get("salaire") or {}
    origine = offre.get("origineOffre") or {}
    description = (offre.get("description") or "")[:DESCRIPTION_MAX]
    return {
        "id": offre.get("id"),
        "intitule": offre.get("intitule"),
        "entreprise": entreprise.get("nom") or "Entreprise non précisée",
        "lieu": lieu.get("libelle"),
        "departement": departement(lieu),
        "code_postal": lieu.get("codePostal"),
        "latitude": lieu.get("latitude"),
        "longitude": lieu.get("longitude"),
        "contrat": offre.get("typeContratLibelle"),
        "type_contrat": offre.get("typeContrat"),
        "nature_contrat": offre.get("natureContrat"),
        "alternance": bool(offre.get("alternance")),
        "duree_travail": offre.get("dureeTravailLibelle"),
        "salaire": salaire.get("libelle"),
        "salaire_complement": " ".join(
            x for x in (salaire.get("complement1"), salaire.get("complement2")) if x
        ) or None,
        "experience": offre.get("experienceLibelle"),
        "qualification": offre.get("qualificationLibelle"),
        "secteur": offre.get("secteurActiviteLibelle"),
        "naf": offre.get("codeNAF"),
        "rome_code": offre.get("romeCode"),
        "rome_libelle": offre.get("romeLibelle"),
        "appellation": offre.get("appellationlibelle"),
        "competences": [c.get("libelle") for c in (offre.get("competences") or []) if c.get("libelle")],
        "qualites": [q.get("libelle") for q in (offre.get("qualitesProfessionnelles") or []) if q.get("libelle")],
        "description": description,
        "date_publication": (offre.get("dateCreation") or "")[:10],
        "date_actualisation": (offre.get("dateActualisation") or "")[:10],
        "url": origine.get("urlOrigine")
        or (f"https://candidat.francetravail.fr/offres/recherche/detail/{offre.get('id')}" if offre.get("id") else None),
        "requetes": [label],
        # Champ « contact » volontairement NON conservé (données personnelles).
    }


def main() -> None:
    client_id = os.environ.get("FRANCE_TRAVAIL_CLIENT_ID")
    client_secret = os.environ.get("FRANCE_TRAVAIL_CLIENT_SECRET")
    if not client_id or not client_secret:
        manquants = [n for n, v in (("FRANCE_TRAVAIL_CLIENT_ID", client_id),
                                    ("FRANCE_TRAVAIL_CLIENT_SECRET", client_secret)) if not v]
        signaler(f"Secret(s) manquant(s) ou vide(s) : {', '.join(manquants)}. Vérifier leur nom exact dans "
                 "Settings > Secrets and variables > Actions.")
        sys.exit(1)

    print("Authentification auprès de l'API France Travail...")
    token = get_token(client_id, client_secret)

    fusion: dict[str, dict] = {}
    bilan_requetes = []
    for rq in REQUETES:
        print(f"Requête : {rq['label']} ...")
        try:
            brutes, total_api = fetch_requete(token, rq["params"])
        except Exception as err:  # noqa: BLE001
            if rq["obligatoire"]:
                raise
            signaler(f"Requête « {rq['label']} » en échec (non bloquant) : {err}")
            bilan_requetes.append({"label": rq["label"], "params": rq["params"], "ok": False,
                                   "erreur": str(err)[:200], "recuperees": 0, "total_api": None})
            continue
        print(f"  {len(brutes)} offres récupérées (total annoncé par l'API : {total_api}).")
        for o in brutes:
            s = simplifier(o, rq["label"])
            if s["id"] in fusion:
                if rq["label"] not in fusion[s["id"]]["requetes"]:
                    fusion[s["id"]]["requetes"].append(rq["label"])
            else:
                fusion[s["id"]] = s
        bilan_requetes.append({"label": rq["label"], "params": rq["params"], "ok": True,
                               "recuperees": len(brutes), "total_api": total_api})

    toutes = list(fusion.values())
    offres = [o for o in toutes if FILTRE_INTITULE.search(fold(o.get("intitule")))]
    ecartees = len(toutes) - len(offres)
    print(f"Filtre sur l'intitulé : {len(offres)} offres gardées, {ecartees} écartées (autre métier).")
    offres.sort(key=lambda o: o.get("date_publication") or "", reverse=True)
    resultat = {
        "schema": 2,
        "derniere_maj": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "canal": "API France Travail — Offres d'emploi v2",
        "requete": REQUETE_LABEL,
        "code_rome": None,
        "filtre_intitule": FILTRE_INTITULE.pattern,
        "offres_ecartees_intitule": ecartees,
        "requetes": bilan_requetes,
        "nombre_offres": len(offres),
        "offres": offres,
    }
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(resultat, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(offres)} offres uniques écrites dans {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
