#!/usr/bin/env python3
"""
Calcule, à partir de data/offres.json (collecte France Travail) :
volume, géographie, télétravail, contrats, salaires, compétences et outils,
acteurs (recruteurs + « marché caché »), mouvement dans le temps.

Écrit data/analyse.json (lu par le site) et ajoute un relevé daté à
data/historique.json (sert à voir les mots qui montent d'un relevé à l'autre).

Tout est recalculé à chaque exécution : aucun chiffre n'est écrit à la main.
"""

import csv
import json
import re
import statistics
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
F_OFFRES = DATA / "offres.json"
F_ENTREPRISES = DATA / "entreprises.json"
F_FORMATION = DATA / "formation.json"
F_HISTO = DATA / "historique.json"
F_OUT = DATA / "analyse.json"
F_OFFRES_SITE = DATA / "offres_site.json"
DIR_CSV = DATA / "csv"

# Repère externe affiché à titre de comparaison (cité avec sa source sur le site).
# À remplir à la main depuis une fiche MétierScope proche du métier (candidat.francetravail.fr/metierscope),
# par exemple : {"source": "France Travail, MétierScope (fiche ...), <date>",
#                "salaire_min": ..., "salaire_max": ..., "offres_12_mois": ...}
# Tant qu'il vaut None, le site n'affiche pas de repère.
REPERE_METIERSCOPE = None


# ---------------------------------------------------------------- utilitaires
def fold(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def pct(n: int, total: int) -> float:
    return round(100 * n / total, 1) if total else 0.0


# --------------------------------------------------------------- géographie
REGIONS = {
    "Auvergne-Rhône-Alpes": "01 03 07 15 26 38 42 43 63 69 73 74",
    "Bourgogne-Franche-Comté": "21 25 39 58 70 71 89 90",
    "Bretagne": "22 29 35 56",
    "Centre-Val de Loire": "18 28 36 37 41 45",
    "Corse": "2A 2B",
    "Grand Est": "08 10 51 52 54 55 57 67 68 88",
    "Hauts-de-France": "02 59 60 62 80",
    "Île-de-France": "75 77 78 91 92 93 94 95",
    "Normandie": "14 27 50 61 76",
    "Nouvelle-Aquitaine": "16 17 19 23 24 33 40 47 64 79 86 87",
    "Occitanie": "09 11 12 30 31 32 34 46 48 65 66 81 82",
    "Pays de la Loire": "44 49 53 72 85",
    "Provence-Alpes-Côte d'Azur": "04 05 06 13 83 84",
    "Outre-mer": "971 972 973 974 976",
}
REGION_PAR_DEP = {d: r for r, ds in REGIONS.items() for d in ds.split()}
REGION_PAR_NOM = {fold(r): r for r in REGIONS}


def departement_de(o: dict) -> str | None:
    if o.get("departement"):
        return o["departement"]
    m = re.match(r"^\s*(\d{2,3}|2[AB])\s*(?:-|$)", o.get("lieu") or "")
    return m.group(1) if m else None


def zone(o: dict) -> tuple[str, str | None]:
    """(zone d'affichage, région) pour une offre."""
    dep = departement_de(o)
    region = REGION_PAR_DEP.get(dep) if dep else None
    if not region:
        region = REGION_PAR_NOM.get(fold(o.get("lieu") or "").strip())
    if dep == "63":
        return "Puy-de-Dôme (63)", region
    if region == "Auvergne-Rhône-Alpes":
        return "Auvergne-Rhône-Alpes hors Puy-de-Dôme (ou département non précisé)", region
    if region == "Outre-mer":
        return "Outre-mer", region
    if region:
        return "Autres régions de métropole", region
    return "Localisation non précisée (France entière / non renseignée)", None


# ------------------------------------------------------------ grandes villes
# Comptage par commune (pas par agglomération) : Boulogne-Billancourt n'est pas Paris.
GRANDES_VILLES = ["Paris", "Marseille", "Lyon", "Toulouse", "Nice", "Nantes", "Montpellier", "Strasbourg",
                  "Bordeaux", "Lille", "Rennes", "Reims", "Toulon", "Saint-Étienne", "Le Havre", "Grenoble",
                  "Dijon", "Angers", "Tours", "Rouen", "Clermont-Ferrand"]
VILLE_PAR_CLE = {fold(v): v for v in GRANDES_VILLES}


def ville_de(o: dict) -> str | None:
    """Grande ville de l'offre, d'après la commune du lieu de travail (« 75 - Paris 8e Arrondissement »)."""
    lieu = o.get("lieu") or ""
    commune = lieu.split(" - ", 1)[1] if " - " in lieu else lieu
    commune = fold(commune).strip()
    commune = re.sub(r"\s+\d+\s*(?:er|e|eme)?(?:\s+arrondissement)?$", "", commune)  # arrondissements
    commune = re.sub(r"\s*\(.*\)$", "", commune).strip()
    return VILLE_PAR_CLE.get(commune)


# ------------------------------------------------------------------ contrats
def categorie_contrat(o: dict) -> str:
    intit = fold(o.get("intitule"))
    nature = fold(o.get("nature_contrat"))
    if o.get("alternance") or "apprentissage" in nature or "professionnalisation" in nature \
            or re.search(r"alternan|apprenti", intit):
        return "Alternance"
    if re.search(r"\bstage\b|stagiaire", intit):
        return "Stage"
    code = (o.get("type_contrat") or "").upper()
    par_code = {"CDI": "CDI", "CDD": "CDD", "SAI": "CDD", "CCE": "CDD", "DDI": "CDD",
                "MIS": "Intérim", "LIB": "Indépendant / freelance", "FRA": "Indépendant / freelance"}
    if code in par_code:
        return par_code[code]
    # Sans code : on lit le début du libellé (« CDD - 12 Mois », « Intérim - 1 Mois »…).
    base = fold(re.split(r"\s*-\s*", o.get("contrat") or "")[0]).strip()
    if base.startswith("cdi"):
        return "CDI"
    if base.startswith("cdd"):
        return "CDD"
    if base.startswith(("interim", "mission")):
        return "Intérim"
    if base.startswith(("profession liberale", "franchise", "travail independant")):
        return "Indépendant / freelance"
    return (o.get("contrat") or "Autre").split(" - ")[0]


# ------------------------------------------------------------------ salaires
def parse_salaire(libelle: str | None):
    """Salaire brut mensuel (min, max) depuis le libellé de l'offre, ou None."""
    if not libelle:
        return None
    low = fold(libelle).replace(" ", " ")
    if "euro" not in low:
        return None
    mois = 12.0
    m = re.search(r"sur\s*(\d+(?:[.,]\d+)?)\s*mois", low)
    if m:
        mois = float(m.group(1).replace(",", "."))
        low = low[:m.start()] + low[m.end():]
    nums = [float(x.replace(",", ".")) for x in re.findall(r"\d+(?:[.,]\d+)?", low)]
    if not nums:
        return None
    if low.startswith("mensuel"):
        conv = lambda x: x
    elif low.startswith("annuel"):
        conv = lambda x: x / mois
    elif low.startswith("horaire"):
        conv = lambda x: x * 151.67
    else:
        return None
    vals = [conv(x) for x in nums[:2]]
    lo, hi = min(vals), max(vals)
    if lo < 300 or hi > 15000:  # valeurs incohérentes écartées
        return None
    return lo, hi


def stats_salaires(valeurs: list[tuple[float, float]]) -> dict:
    n = len(valeurs)
    if n == 0:
        return {"n": 0}
    mids = sorted((lo + hi) / 2 for lo, hi in valeurs)
    res = {"n": n, "mediane": round(statistics.median(mids)),
           "min": round(min(lo for lo, _ in valeurs)), "max": round(max(hi for _, hi in valeurs))}
    if n >= 8:
        q = statistics.quantiles(mids, n=4)
        res["q1"], res["q3"] = round(q[0]), round(q[2])
    return res


# --------------------------------------------------- compétences et outils
# (nom, catégorie, [(regex, sensible_casse), ...])
def T(nom, cat, *pats):
    return (nom, cat, [(p if isinstance(p, tuple) else (p, False)) for p in pats])


CAT_ACQ = "Acquisition et publicité"
CAT_DATA = "Data et mesure"
CAT_CRM = "CRM, emailing et automation"
CAT_WEB = "Site, e-commerce et SEO"
CAT_SOC = "Réseaux sociaux et contenu"
CAT_IA = "IA et automatisation"
CAT_MET = "Compétences métier"

TERMES = [
    T("Google Ads / SEA", CAT_ACQ, r"google ads|adwords", (r"\bSEA\b", True)),
    T("Meta Ads (Facebook, Instagram)", CAT_ACQ, r"meta ads|facebook ads|instagram ads|ads manager|social ads|paid social"),
    T("LinkedIn Ads / TikTok Ads", CAT_ACQ, r"linkedin ads|tiktok ads|snapchat ads|pinterest ads"),
    T("Display / programmatique / retargeting", CAT_ACQ, r"display|programmatique|retargeting|remarketing|\bdv360\b"),
    T("Affiliation / partenariats", CAT_ACQ, r"affiliation|affilie|marketplace|amazon"),
    T("Acquisition / génération de leads", CAT_ACQ, r"acquisition|generation de leads?|lead gen|\bleads?\b|prospects?"),
    T("Google Analytics / GA4", CAT_DATA, r"google analytics|\bga4\b|analytics"),
    T("Google Tag Manager / tracking", CAT_DATA, r"tag manager|\bgtm\b|tracking|tag(?:ging|s)? de suivi|pixel"),
    T("Looker Studio / Power BI / dashboards", CAT_DATA, r"looker|data studio|power ?bi|tableau software|dashboard|tableaux? de bord"),
    T("Excel (TCD, analyse)", CAT_DATA, r"excel|tableaux? croises|\btcd\b"),
    T("A/B test / optimisation de la conversion", CAT_DATA, r"a/b ?test|ab test|taux de conversion|\bcro\b|optimisation de la conversion|landing pages?"),
    T("ROI / budget / ROAS", CAT_DATA, r"\broi\b|\broas\b|\bcpa\b|\bcpc\b|budget"),
    T("CRM (HubSpot, Salesforce…)", CAT_CRM, r"hubspot|salesforce|\bcrm\b|dynamics|zoho|pipedrive"),
    T("Emailing / newsletters", CAT_CRM, r"emailing|e-mailing|newsletter|mailchimp|brevo|sendinblue|klaviyo|campagnes? (?:d.)?e-?mails?"),
    T("Marketing automation", CAT_CRM, r"marketing automation|automatisation marketing|scenarios? (?:d.)?e-?mail|workflows?|nurturing|plezi|marketo|pardot|selligent|actito|splio"),
    T("Fidélisation / marketing client", CAT_CRM, r"fidelisation|fideliser|programme de fidelite|marketing client|relation client|\bcrm\b|retention|parcours client|segmentation"),
    T("SMS / notifications", CAT_CRM, r"\bsms\b|notifications? push"),
    T("SEO / référencement naturel", CAT_WEB, (r"\bSEO\b", True), r"referencement naturel|search console|semrush|ahrefs"),
    T("WordPress / CMS", CAT_WEB, r"wordpress|\bcms\b|drupal|webflow|wix"),
    T("Shopify / PrestaShop / e-commerce", CAT_WEB, r"shopify|prestashop|magento|woocommerce|e-?commerce|site marchand|boutique en ligne"),
    T("UX / ergonomie web", CAT_WEB, r"\bux\b|\bui\b|ergonomi|experience utilisateur|parcours utilisateur"),
    T("HTML / CSS", CAT_WEB, r"\bhtml\b|\bcss\b"),
    T("GitHub / Git", CAT_WEB, r"github|\bgit\b"),
    T("Réseaux sociaux", CAT_SOC, r"reseaux sociaux|social media|instagram|facebook|linkedin|tiktok"),
    T("Création de contenu / rédaction", CAT_SOC, r"creation de contenu|redact|copywrit|contenus? (?:editorial|digital|web|marketing)|content marketing|storytelling"),
    T("Canva", CAT_SOC, r"canva"),
    T("Suite Adobe (Photoshop, InDesign…)", CAT_SOC, r"photoshop|illustrator|indesign|suite adobe|creative cloud|\badobe\b"),
    T("Vidéo / montage", CAT_SOC, r"montage|video|reels?\b|motion design|capcut|premiere"),
    T("Influence / UGC", CAT_SOC, r"influen|\bugc\b|createurs? de contenu"),
    T("IA / IA générative", CAT_IA, (r"\bIA\b", True), r"intelligence artificielle|ia generative|genai|generative ai"),
    T("ChatGPT et outils d'IA", CAT_IA, r"chat ?gpt|openai|midjourney|copilot|gemini|mistral|claude\b"),
    T("Automatisation / no-code", CAT_IA, r"no-?code|low-?code|zapier|make\.com|n8n"),
    T("Événementiel / salons", CAT_MET, r"evenement|salons?\b|webinaires?|webinars?|seminaires?|soirees?"),
    T("Print / PLV / supports", CAT_MET, r"\bplv\b|print|brochures?|plaquettes?|flyers?|catalogues?|goodies"),
    T("Trade marketing / animation commerciale", CAT_MET, r"trade marketing|animation commerciale|operations? commerciales?|promotion|merchandising"),
    T("Plan marketing / stratégie", CAT_MET, r"plan (?:marketing|d.actions?|de communication)|strategie (?:marketing|digitale?|d.acquisition|de communication)"),
    T("Études de marché / veille", CAT_MET, r"etudes? de marche|\bveille\b|benchmark|analyse concurrentielle"),
    T("Reporting / KPI", CAT_MET, r"reporting|\bkpi|indicateurs?|analyse des performances|statistiques"),
    T("Gestion de projet / coordination", CAT_MET, r"gestion de projet|project management|coordination|coordonner|retroplanning"),
    T("Relation agences / prestataires", CAT_MET, r"agences?|prestataires?|freelances?|fournisseurs?"),
    T("Marque / branding", CAT_MET, r"branding|image de marque|notoriete|identite de marque|plateforme de marque"),
    T("Anglais", CAT_MET, r"anglais|english|bilingue"),
]
TERMES = [(n, c, [(re.compile(p, 0 if cs else re.I), cs) for p, cs in pats]) for n, c, pats in TERMES]

# Termes suivis pour « ce qui monte » (sous-ensemble parlant du tableau ci-dessus).
SUIVI_MONTEE = {"IA / IA générative", "ChatGPT et outils d'IA", "Automatisation / no-code",
                "Marketing automation", "Meta Ads (Facebook, Instagram)", "Google Ads / SEA",
                "Fidélisation / marketing client", "Événementiel / salons", "Vidéo / montage",
                "Looker Studio / Power BI / dashboards"}


def texte_offre(o: dict) -> tuple[str, str]:
    brut = " ".join(filter(None, [o.get("intitule"), o.get("description"),
                                  " ".join(o.get("competences") or []), " ".join(o.get("qualites") or [])]))
    return brut, fold(brut)


def termes_de(o: dict) -> set[str]:
    brut, plie = texte_offre(o)
    trouves = set()
    for nom, _cat, pats in TERMES:
        for rx, cs in pats:
            if rx.search(brut if cs else plie):
                trouves.add(nom)
                break
    return trouves


# ----------------------------------------------------------------- télétravail
RE_TT = re.compile(r"teletravail|tele-travail|remote|a distance|travail a domicile|home office|hybride")
RE_FULL = re.compile(r"full[- ]?remote|100 ?% ?(?:teletravail|remote|a distance)|teletravail (?:total|complet|integral)"
                     r"|entierement a distance|(?:poste|travail) (?:en )?(?:teletravail|remote) (?:complet|total|integral)")


def teletravail(o: dict) -> str:
    plie = fold(" ".join(filter(None, [o.get("intitule"), o.get("description"), o.get("duree_travail")])))
    if RE_FULL.search(plie):
        return "complet"
    if RE_TT.search(plie):
        return "mentionné"
    return "non"


# -------------------------------------------------------------- entreprises
RE_INTERMEDIAIRE = re.compile(
    r"interim|adecco|randstad|manpower|synergie|crit\b|actual|start people|temporis|proman|gi group|expectra|"
    r"page personnel|michael page|hays|walters|recrutement|cabinet|ecole|campus|formation|alternance|\bcfa\b|"
    r"studi\b|openclassrooms|digital campus|isefac|ifocop|sup de pub|iscom|\becv\b|ineo|talent|rh\b|emploi|"
    r"school|academy|academie|institut|iscod|isfoi|\bifc\b|\bcnam\b|greta|afpa|faculte|universite|business")
FORMES = re.compile(r"\b(sas|sarl|sa|sasu|eurl|sci|snc|groupe|group|france)\b")


def cle_entreprise(nom: str) -> str:
    s = re.sub(r"[^a-z0-9 ]", " ", fold(nom))
    s = FORMES.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()


def intitule_normalise(t: str) -> str:
    s = fold(t)
    s = re.sub(r"\(?\b[hf]\s*/\s*[hf]\b\)?|\(?\bf/h\b\)?|\(?\bh/f\b\)?|\(.*?\)", " ", s)
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


# =================================================================== analyse
def main() -> None:
    src = load_json(F_OFFRES, None)
    if not src or not src.get("offres"):
        raise SystemExit("data/offres.json vide ou absent : lancez d'abord scripts/fetch_offres.py")
    # Les offres de franchise (recrutement de franchisés, souvent une même annonce
    # publiée ville par ville) ne sont pas des emplois : on les écarte.
    def est_franchise(o: dict) -> bool:
        return ((o.get("type_contrat") or "").upper() == "FRA" or fold(o.get("contrat")).startswith("franchise")
                # postes d'enseignement du marketing digital : autre métier
                or bool(re.search(r"format(?:eur|rice)|enseignant|professeur|intervenant", fold(o.get("intitule")))))
    franchises = [o for o in src["offres"] if est_franchise(o)]
    offres = [o for o in src["offres"] if not est_franchise(o)]
    n = len(offres)
    maj = src.get("derniere_maj")
    date_maj = datetime.fromisoformat(maj).date() if maj else datetime.now(timezone.utc).date()
    avec_texte = sum(1 for o in offres if o.get("description"))

    # --- volume / dates
    dates = sorted(o["date_publication"] for o in offres if o.get("date_publication"))
    par_mois = Counter(d[:7] for d in dates)
    par_requete = Counter(r for o in offres for r in (o.get("requetes") or []))

    # --- géographie
    zones = Counter(); regions = Counter(); deps = Counter()
    villes = Counter(v for v in (ville_de(o) for o in offres) if v)
    clermont = 0
    for o in offres:
        z, r = zone(o)
        zones[z] += 1
        if r:
            regions[r] += 1
        d = departement_de(o)
        if d:
            deps[d] += 1
        if "clermont-ferrand" in fold(o.get("lieu")):
            clermont += 1
    ordre_zones = ["Puy-de-Dôme (63)", "Auvergne-Rhône-Alpes hors Puy-de-Dôme (ou département non précisé)",
                   "Autres régions de métropole", "Outre-mer",
                   "Localisation non précisée (France entière / non renseignée)"]

    # --- télétravail
    tt = Counter(teletravail(o) for o in offres)

    # --- contrats
    contrats = Counter(categorie_contrat(o) for o in offres)
    cat_de = {id(o): categorie_contrat(o) for o in offres}

    # --- salaires
    par_cat: dict[str, list] = defaultdict(list)
    sans_salaire = 0
    for o in offres:
        s = parse_salaire(o.get("salaire"))
        if s:
            par_cat[cat_de[id(o)]].append(s)
        else:
            sans_salaire += 1
    n_sal = n - sans_salaire
    salaires = {
        "renseigne": n_sal, "part_renseignee": pct(n_sal, n),
        "par_contrat": {c: stats_salaires(v) for c, v in sorted(par_cat.items(), key=lambda kv: -len(kv[1]))},
        "hors_alternance": stats_salaires([s for c, v in par_cat.items() if c != "Alternance" for s in v]),
        "repere_externe": REPERE_METIERSCOPE,
        "unite": "salaire brut mensuel en euros (annuel ÷ durée en mois, horaire × 151,67 h)",
    }

    # --- intitulés
    groupes: dict[str, list] = defaultdict(list)
    for o in offres:
        groupes[intitule_normalise(o.get("intitule") or "")].append(o.get("intitule"))
    intitules = [{"intitule": Counter(v).most_common(1)[0][0], "n": len(v), "pct": pct(len(v), n)}
                 for k, v in sorted(groupes.items(), key=lambda kv: -len(kv[1])) if k][:10]

    # --- compétences et outils
    compte = Counter(); presence: dict[int, set] = {}
    for o in offres:
        t = termes_de(o)
        presence[id(o)] = t
        compte.update(t)
    cats = {nom: cat for nom, cat, _ in TERMES}
    outils = [{"terme": t, "categorie": cats[t], "n": c, "pct": pct(c, n)}
              for t, c in compte.most_common()]
    formation = load_json(F_FORMATION, {"termes_vus_en_formation": []})
    vus = [fold(x) for x in formation.get("termes_vus_en_formation", []) if str(x).strip()]

    def vu(terme: str) -> bool:
        f = fold(terme)
        return any(v and (v in f or f in v) for v in vus)

    formation_renseignee = bool(vus)
    for x in outils:
        x["vu_en_formation"] = vu(x["terme"]) if formation_renseignee else None
    a_acquerir = [x for x in outils if x["vu_en_formation"] is False][:8]

    comp_api = Counter(c for o in offres for c in set(o.get("competences") or []))
    qual_api = Counter(q for o in offres for q in set(o.get("qualites") or []))

    # --- mouvement : (a) récent vs ancien dans ce relevé, (b) relevé précédent
    limite = date_maj - timedelta(days=30)
    recents = [o for o in offres if (o.get("date_publication") or "") >= limite.isoformat()]
    anciens = [o for o in offres if o.get("date_publication") and o["date_publication"] < limite.isoformat()]
    mouvement = {"recent_vs_ancien": None, "vs_releve_precedent": None}
    if len(recents) >= 15 and len(anciens) >= 15 and avec_texte >= 0.8 * n:
        lignes = []
        for t in SUIVI_MONTEE | {x["terme"] for x in outils[:12]}:
            r = sum(1 for o in recents if t in presence[id(o)])
            a = sum(1 for o in anciens if t in presence[id(o)])
            if r + a >= 3:
                lignes.append({"terme": t, "pct_recent": pct(r, len(recents)), "pct_ancien": pct(a, len(anciens)),
                               "ecart": round(pct(r, len(recents)) - pct(a, len(anciens)), 1), "n": r + a})
        lignes.sort(key=lambda x: -x["ecart"])
        mouvement["recent_vs_ancien"] = {"n_recent": len(recents), "n_ancien": len(anciens),
                                         "seuil": limite.isoformat(), "lignes": lignes,
                                         "avertissement": "Comparaison indicative : échantillons modestes, et une offre ancienne encore "
                                                          "ouverte n'est pas représentative de toutes les offres passées."}

    histo = load_json(F_HISTO, {"releves": []})
    releve = {"date": date_maj.isoformat(), "nombre_offres": n,
              "termes": {t: c for t, c in compte.items()}, "avec_texte": avec_texte}
    if avec_texte >= 0.8 * n:  # on ne mémorise que des relevés où le texte est disponible
        histo["releves"] = [r for r in histo.get("releves", []) if r["date"] != releve["date"]] + [releve]
        histo["releves"].sort(key=lambda r: r["date"])
        histo["releves"] = histo["releves"][-400:]
        F_HISTO.write_text(json.dumps(histo, ensure_ascii=False, indent=1), encoding="utf-8")
    ancien = [r for r in histo.get("releves", []) if r["date"] <= (date_maj - timedelta(days=14)).isoformat()
              and r["date"] != releve["date"]]
    if ancien and avec_texte >= 0.8 * n:
        prev = ancien[-1]
        lignes = []
        for t in set(compte) | set(prev["termes"]):
            pn, pp = pct(compte.get(t, 0), n), pct(prev["termes"].get(t, 0), prev["nombre_offres"])
            if compte.get(t, 0) + prev["termes"].get(t, 0) >= 3:
                lignes.append({"terme": t, "pct_actuel": pn, "pct_precedent": pp, "ecart": round(pn - pp, 1)})
        lignes.sort(key=lambda x: -x["ecart"])
        mouvement["vs_releve_precedent"] = {"date_precedent": prev["date"], "n_precedent": prev["nombre_offres"],
                                            "lignes": lignes}
    mouvement["nb_releves"] = len(histo.get("releves", []))

    # --- acteurs : recruteurs
    emp = defaultdict(list)
    sans_nom = 0
    for o in offres:
        nom = o.get("entreprise") or ""
        if not nom or nom.startswith("Entreprise non précisée"):
            sans_nom += 1
            continue
        emp[cle_entreprise(nom)].append(o)
    recruteurs = []
    for k, os_ in sorted(emp.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        nom = Counter(o["entreprise"] for o in os_).most_common(1)[0][0]
        recruteurs.append({
            "entreprise": nom, "n": len(os_),
            "type": "Intermédiaire (recrutement, école, formation)" if RE_INTERMEDIAIRE.search(fold(nom))
            else "Employeur direct (présumé)",
            "lieux": sorted({(o.get("lieu") or "") for o in os_ if o.get("lieu")})[:3],
        })

    # --- marché caché
    ent = load_json(F_ENTREPRISES, None)
    cache = None
    if ent and ent.get("entreprises"):
        visibles = set(emp)
        # on ne garde que les entreprises dont le siège est dans le Puy-de-Dôme (code postal 63xxx)
        liste = [e for e in ent["entreprises"] if str(e.get("code_postal") or "").startswith("63")]
        tr = Counter(e.get("effectif_groupe") for e in liste)
        for e in liste:
            e["publie_une_offre"] = cle_entreprise(e["nom"]) in visibles
        n_pub = sum(1 for e in liste if e["publie_une_offre"])
        cibles = [e for e in liste if (e.get("effectif_rang") or 0) >= 2]  # 3 salariés et plus (peu de grosses structures dans le 63)
        cibles.sort(key=lambda e: (-(e.get("effectif_rang") or 0), e["nom"]))
        cache = {
            "source": ent.get("source"), "date": ent.get("date"), "filtre": (ent.get("filtre") or "") + " · siège dans le 63",
            "total": len(liste),
            "par_naf": dict(Counter(e["naf_libelle"] for e in liste).most_common()),
            "par_effectif": {k: tr.get(k, 0) for k in ["0 salarié ou non renseigné", "1 à 9", "10 à 49", "50 à 249", "250 et plus"]},
            "par_commune": Counter(e["commune"] for e in liste).most_common(8),
            "publient_une_offre": n_pub,
            "part_visible": pct(n_pub, len(liste)),
            "cibles": [{"nom": e["nom"], "commune": e["commune"], "naf": e["naf_libelle"],
                        "effectif": e["effectif_libelle"], "publie_une_offre": e["publie_une_offre"]}
                       for e in cibles[:60]],
            "exclus_opposition_diffusion": ent.get("exclus_opposition"),
        }

    # --- limites (affichées sur le site)
    limites = [
        f"Photographie du {date_maj.strftime('%d/%m/%Y')} : seules les offres déposées à France Travail (et ses partenaires) "
        "et encore ouvertes sont visibles. Ce n'est ni le total annuel ni l'ensemble du marché : beaucoup de "
        "recrutements ne passent jamais par une annonce.",
        f"Seules les offres dont l'intitulé parle de marketing digital (ou numérique, web, e-marketing) sont gardées : "
        f"{src.get('offres_ecartees_intitule') or 0} offres remontées par les mots-clés mais portant un autre intitulé "
        "ont été écartées. Le niveau de poste varie (assistant, chargé, responsable) : voir les intitulés en section 1.",
        f"Le salaire n'est affiché que dans {pct(n_sal, n)} % des offres ; les moyennes ne reflètent que les employeurs "
        "qui le publient. Les salaires d'alternance suivent une grille légale et sont séparés.",
        "Une même offre peut être republiée plusieurs fois, ou par plusieurs agences : les volumes peuvent être gonflés.",
        "Compétences, outils et télétravail sont détectés par mots-clés dans le texte des annonces : "
        "une mention n'est pas une exigence, et un outil non cité peut quand même être utilisé.",
        f"{sans_nom} offres ({pct(sans_nom, n)} %) n'indiquent pas l'employeur (annonces anonymisées).",
        f"{len(franchises)} annonces ont été écartées : recrutement de franchisés (un même réseau publie souvent la même "
        "annonce dans des dizaines de villes) et postes de formateur ou d'enseignant en marketing digital.",
        "Le classement « intermédiaire / employeur direct » est automatique (mots du nom) et à vérifier.",
    ]
    if avec_texte < n:
        limites.append(f"Le texte complet n'est disponible que pour {avec_texte} offres sur {n} : "
                       "les comptages d'outils et de compétences portent sur ces offres seulement.")

    out = {
        "meta": {
            "date_donnees": maj, "date_analyse": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "canal": src.get("canal") or "API France Travail — Offres d'emploi v2",
            "requetes": src.get("requetes") or [{"label": f"code ROME {src.get('code_rome')}"}],
            "code_rome": src.get("code_rome"),
            "metier": src.get("requete"),
            "offres_ecartees_intitule": src.get("offres_ecartees_intitule"),
            "rome_libelle": (Counter(o.get("rome_libelle") for o in offres if o.get("rome_libelle")).most_common(1) or [[None]])[0][0],
            "nombre_offres": n, "offres_avec_texte": avec_texte,
            "date_plus_ancienne": dates[0] if dates else None, "date_plus_recente": dates[-1] if dates else None,
        },
        "volume": {"total": n, "par_requete": dict(par_requete), "par_mois": dict(sorted(par_mois.items())),
                   "publiees_7_jours": sum(1 for d in dates if d >= (date_maj - timedelta(days=7)).isoformat()),
                   "publiees_30_jours": len(recents)},
        "geographie": {
            "zones": [{"zone": z, "n": zones.get(z, 0), "pct": pct(zones.get(z, 0), n)} for z in ordre_zones],
            "clermont_ferrand": clermont, "puy_de_dome": zones.get("Puy-de-Dôme (63)", 0),
            "regions": [{"region": r, "n": c, "pct": pct(c, n)} for r, c in regions.most_common(8)],
            "departements": [{"departement": d, "n": c} for d, c in deps.most_common(8)],
            "villes": [{"ville": v, "n": villes.get(v, 0), "pct": pct(villes.get(v, 0), n)}
                       for v in sorted(GRANDES_VILLES, key=lambda v: (-villes.get(v, 0), v))],
            "villes_total": sum(villes.values()),
        },
        "teletravail": {"mentionne": tt["mentionné"] + tt["complet"], "complet": tt["complet"],
                        "pct_mentionne": pct(tt["mentionné"] + tt["complet"], n), "pct_complet": pct(tt["complet"], n)},
        "contrats": [{"contrat": c, "n": k, "pct": pct(k, n)} for c, k in contrats.most_common()],
        "salaires": salaires,
        "intitules": intitules,
        "competences": {
            "outils": outils, "formation_renseignee": formation_renseignee,
            "a_acquerir": a_acquerir,
            "api_competences": [{"libelle": c, "n": k, "pct": pct(k, n)} for c, k in comp_api.most_common(12)],
            "api_qualites": [{"libelle": c, "n": k, "pct": pct(k, n)} for c, k in qual_api.most_common(10)],
            "methode": "Un terme est compté une fois par offre où il apparaît (intitulé, description, compétences et "
                       "qualités renseignées). Le rapprochement avec la formation se fait par mots-clés (data/formation.json).",
        },
        "mouvement": mouvement,
        "acteurs": {"recruteurs": recruteurs[:25], "n_recruteurs": len(recruteurs),
                    "sans_employeur": sans_nom, "marche_cache": cache},
        "limites": limites,
    }
    F_OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    # Version légère des offres pour la page « Offres en direct » (sans le texte complet).
    outils_seuls = {nom for nom, cat, _ in TERMES if cat != CAT_MET}
    liste = []
    for o in offres:
        s = parse_salaire(o.get("salaire"))
        liste.append({
            "id": o.get("id"), "intitule": o.get("intitule"), "entreprise": o.get("entreprise"),
            "lieu": o.get("lieu"), "zone": zone(o)[0], "ville": ville_de(o), "contrat": cat_de[id(o)], "contrat_libelle": o.get("contrat"),
            "salaire": o.get("salaire"), "salaire_mensuel": [round(s[0]), round(s[1])] if s else None,
            "teletravail": teletravail(o), "date": o.get("date_publication"), "url": o.get("url"),
            "outils": sorted(t for t in presence[id(o)] if t in outils_seuls)[:6],
        })
    F_OFFRES_SITE.write_text(json.dumps({"date_donnees": maj, "offres": liste}, ensure_ascii=False,
                                        separators=(",", ":")), encoding="utf-8")

    # --- exports CSV datés (un fichier par jour : on garde l'historique des relevés)
    DIR_CSV.mkdir(exist_ok=True)
    jour = date_maj.isoformat()
    with open(DIR_CSV / f"offres_{jour}.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date_releve", "canal", "id", "intitule", "entreprise", "lieu", "zone", "contrat",
                    "salaire_affiche", "salaire_mensuel_min", "salaire_mensuel_max", "teletravail_mentionne",
                    "date_publication", "url"])
        for o in liste:
            sm = o["salaire_mensuel"] or ["", ""]
            w.writerow([jour, "API France Travail - Offres d'emploi v2", o["id"], o["intitule"], o["entreprise"],
                        o["lieu"], o["zone"], o["contrat"], o["salaire"] or "", sm[0], sm[1],
                        "oui" if o["teletravail"] != "non" else "non", o["date"], o["url"]])
    with open(DIR_CSV / f"termes_{jour}.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date_releve", "terme", "categorie", "nombre_offres", "part_des_offres_pct", "vu_en_formation"])
        for x in outils:
            vf = x.get("vu_en_formation")
            w.writerow([jour, x["terme"], x["categorie"], x["n"], x["pct"], "" if vf is None else ("oui" if vf else "non")])
    print(f"Analyse écrite : {n} offres, {len(outils)} termes détectés, {len(recruteurs)} employeurs. CSV datés : data/csv/*_{jour}.csv")


if __name__ == "__main__":
    main()
