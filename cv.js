// Page « Mon CV » : compare un CV aux offres collectées, entièrement dans le navigateur.
// Le CV (PDF ou texte) est lu localement : il n'est ni envoyé ni enregistré.
// Utilise les fonctions de script.js ($, el, clear, loadJSON, fmt, fmtPct).

(() => {
  if (!$("analyser")) return;

  const foldTxt = (s) => (s || "").normalize("NFKD").replace(/[̀-ͯ]/g, "").toLowerCase();

  // Conseils par compétence (repli : conseil par catégorie).
  const CONSEILS = {
    "Google Ads / SEA": "Citez Google Ads avec un résultat : budget géré, coût par clic, conversions obtenues. Une certification Google Ads (gratuite) se passe en quelques heures.",
    "Meta Ads (Facebook, Instagram)": "Mentionnez les campagnes Meta Ads que vous avez lancées ou suivies : objectif, audience, budget, résultat.",
    "LinkedIn Ads / TikTok Ads": "Si vous avez touché à LinkedIn Ads ou TikTok Ads, même en test, écrivez-le : c'est encore rare sur les CV.",
    "Display / programmatique / retargeting": "Le retargeting et le display sont souvent cités : précisez si vous avez suivi ce type de campagnes.",
    "Affiliation / partenariats": "Valorisez les partenariats ou l'affiliation que vous avez gérés (nombre de partenaires, chiffre généré).",
    "Acquisition / génération de leads": "Parlez « acquisition » et « leads » : combien de contacts ou de clients vos actions ont-elles apportés ?",
    "Google Analytics / GA4": "Ajoutez GA4 dans vos outils et donnez un exemple : un tableau de suivi, une analyse de trafic, une décision prise grâce aux chiffres.",
    "Google Tag Manager / tracking": "Le suivi (Tag Manager, pixels) est un vrai plus : indiquez si vous avez posé ou vérifié des balises.",
    "Looker Studio / Power BI / dashboards": "Mentionnez un tableau de bord que vous avez construit (Looker Studio, Power BI, Excel) et à qui il servait.",
    "Excel (TCD, analyse)": "Écrivez « Excel (tableaux croisés dynamiques) » plutôt que « Pack Office » : c'est ce que lisent les recruteurs.",
    "A/B test / optimisation de la conversion": "Un test A/B, même simple (deux objets d'e-mail, deux visuels), est un excellent exemple à chiffrer.",
    "ROI / budget / ROAS": "Indiquez les budgets que vous avez suivis et le retour obtenu (ROI, ROAS, coût par lead).",
    "CRM (HubSpot, Salesforce…)": "Nommez le CRM utilisé (HubSpot, Salesforce, Brevo…) et ce que vous y faisiez : segmentation, relances, suivi.",
    "Emailing / newsletters": "Ajoutez vos campagnes e-mail avec leurs taux d'ouverture ou de clic : c'est très demandé et facile à chiffrer.",
    "Marketing automation": "Décrivez un scénario automatisé (bienvenue, relance, anniversaire…) : le mot « marketing automation » est recherché.",
    "Fidélisation / marketing client": "Mettez en avant votre marketing client : programme de fidélité, segmentation, parcours client, rétention.",
    "SMS / notifications": "Si vous avez envoyé des campagnes SMS ou push, ajoutez-les à côté de l'emailing.",
    "SEO / référencement naturel": "Le SEO revient dans une offre sur deux : citez une action concrète (optimisation de pages, mots-clés, Search Console).",
    "WordPress / CMS": "Indiquez le CMS que vous savez utiliser (WordPress, Shopify, Wix…) pour mettre à jour un site.",
    "Shopify / PrestaShop / e-commerce": "Si vous avez travaillé sur une boutique en ligne, précisez la plateforme et votre rôle.",
    "UX / ergonomie web": "Une notion d'UX (parcours utilisateur, ergonomie d'une page) est appréciée : un exemple suffit.",
    "HTML / CSS": "Des bases en HTML/CSS (e-mails, pages) peuvent faire la différence : notez-les si vous les avez.",
    "GitHub / Git": "Votre site sur GitHub est une preuve concrète : ajoutez son lien sur votre CV.",
    "Réseaux sociaux": "Citez les réseaux que vous avez gérés et un résultat (abonnés gagnés, taux d'engagement).",
    "Création de contenu / rédaction": "Montrez que vous savez produire du contenu : articles, posts, newsletters, avec un lien si possible.",
    "Canva": "Canva est très souvent demandé : ajoutez-le à vos outils.",
    "Suite Adobe (Photoshop, InDesign…)": "Si vous maîtrisez un logiciel Adobe, précisez lequel et votre niveau.",
    "Vidéo / montage": "La vidéo courte est très demandée : citez un montage réalisé (Reels, TikTok, CapCut).",
    "Influence / UGC": "Une collaboration avec des créateurs ou de l'UGC est un vrai atout à mentionner.",
    "IA / IA générative": "Montrez comment vous utilisez l'IA au travail (rédaction, visuels, analyse) : c'est un signal moderne.",
    "ChatGPT et outils d'IA": "Nommez les outils d'IA que vous utilisez (ChatGPT, Claude, Copilot…) et pour quoi faire.",
    "Automatisation / no-code": "Un outil no-code (Zapier, Make, n8n) est un vrai plus si vous l'avez utilisé.",
    "Événementiel / salons": "Détaillez un événement que vous avez organisé : type, nombre de participants, budget, retombées.",
    "Print / PLV / supports": "Citez les supports print ou PLV que vous avez conçus (flyers, kakémonos, catalogues).",
    "Trade marketing / animation commerciale": "Mentionnez les opérations commerciales ou promotions que vous avez animées.",
    "Plan marketing / stratégie": "Montrez que vous avez contribué à un plan marketing : objectifs, actions, calendrier.",
    "Études de marché / veille": "Ajoutez une veille ou une étude que vous avez menée (concurrents, tendances).",
    "Reporting / KPI": "Le reporting est cité dans plus d'une offre sur deux : écrivez quels indicateurs vous suiviez et à quelle fréquence.",
    "Gestion de projet / coordination": "Donnez un exemple de projet que vous avez coordonné : délais, intervenants, résultat.",
    "Relation agences / prestataires": "Indiquez si vous avez travaillé avec des agences ou des prestataires (brief, suivi, validation).",
    "Marque / branding": "Montrez votre sens de la marque : charte, ton, notoriété, image.",
    "Anglais": "Précisez votre niveau d'anglais (B2, C1, TOEIC…) : beaucoup d'offres le demandent.",
  };
  const CONSEIL_CATEGORIE = "Ajoutez cette compétence avec un exemple concret tiré de votre alternance ou d'un projet.";

  let termes = [], formation = [], offres = [], cible = "toutes", texteCV = "";

  const compiler = (t) => ({ ...t, rx: t.motifs.map((m) => ({ re: new RegExp(m.re, m.casse ? "" : "i"), casse: m.casse })) });
  // Les PDF donnent souvent des espaces multiples ou des retours à la ligne au milieu des mots-clés.
  const normaliser = (s) => (s || "").replace(/[\s\u00a0\u202f]+/g, " ").trim();
  const detecter = (brut) => {
    const texte = normaliser(brut), plie = foldTxt(texte), trouves = new Set();
    termes.forEach((t) => { if (t.rx.some((m) => m.re.test(m.casse ? texte : plie))) trouves.add(t.terme); });
    return trouves;
  };
  const vuEnFormation = (terme) => formation.some((v) => { const a = foldTxt(v), b = foldTxt(terme); return a && (a.includes(b) || b.includes(a)); });

  // ---------- lecture du CV ----------
  const etat = (msg) => { $("cv-etat").textContent = msg; };
  const majBouton = () => {
    const ok = texteCV.trim().length > 30 && (cible === "toutes" || $("offre-select").value);
    $("analyser").disabled = !ok;
  };

  async function lirePDF(buffer) {
    if (!window.pdfjsLib) throw new Error("lecteur PDF indisponible");
    pdfjsLib.GlobalWorkerOptions.workerSrc = "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js";
    const pdf = await pdfjsLib.getDocument({ data: buffer }).promise;
    const pages = [];
    for (let i = 1; i <= pdf.numPages; i++) {
      const contenu = await (await pdf.getPage(i)).getTextContent();
      pages.push(contenu.items.map((it) => it.str).join(" "));
    }
    return pages.join("\n");
  }
  window.__lirePDF = lirePDF; // utile pour tester

  async function chargerFichier(f) {
    if (!f) return;
    etat(`Lecture de « ${f.name} »…`);
    try {
      const estPDF = f.type === "application/pdf" || /\.pdf$/i.test(f.name);
      texteCV = estPDF ? await lirePDF(await f.arrayBuffer()) : await f.text();
      const mots = texteCV.split(/\s+/).filter(Boolean).length;
      if (mots < 30) {
        etat(`« ${f.name} » contient très peu de texte lisible (${mots} mots). Si votre CV est une image (export Canva en image, scan), collez plutôt son texte ci-dessous.`);
      } else etat(`✓ « ${f.name} » lu : ${fmt(mots)} mots.`);
      $("dropzone").classList.add("is-ok");
      $("dropzone").querySelector(".dropzone-titre").textContent = f.name;
      $("dropzone").querySelector(".dropzone-sous").textContent = "Cliquez pour changer de fichier";
    } catch (err) {
      texteCV = "";
      etat("Impossible de lire ce fichier. Essayez un autre PDF, ou collez le texte de votre CV ci-dessous.");
    }
    majBouton();
  }

  $("cv-fichier").addEventListener("change", (e) => chargerFichier(e.target.files[0]));
  const dz = $("dropzone");
  ["dragenter", "dragover"].forEach((ev) => dz.addEventListener(ev, (e) => { e.preventDefault(); dz.classList.add("is-over"); }));
  ["dragleave", "drop"].forEach((ev) => dz.addEventListener(ev, (e) => { e.preventDefault(); dz.classList.remove("is-over"); }));
  dz.addEventListener("drop", (e) => chargerFichier(e.dataTransfer.files[0]));
  $("cv-texte").addEventListener("input", (e) => {
    texteCV = e.target.value;
    if (texteCV.trim()) etat(`✓ Texte collé : ${fmt(texteCV.split(/\s+/).filter(Boolean).length)} mots.`);
    majBouton();
  });

  // ---------- choix de la cible ----------
  const remplirOffres = () => {
    const q = foldTxt($("offre-recherche").value);
    const sel = $("offre-select"), avant = sel.value;
    clear(sel);
    offres.filter((o) => !q || foldTxt(`${o.intitule} ${o.entreprise} ${o.lieu}`).includes(q)).slice(0, 200).forEach((o) =>
      sel.append(el("option", { value: o.id, text: `${o.intitule} — ${o.entreprise}${o.lieu ? ` · ${o.lieu}` : ""}` })));
    if (avant && [...sel.options].some((op) => op.value === avant)) sel.value = avant;
  };
  const majCible = () => {
    document.querySelectorAll("#cible-choix .filter").forEach((b) => b.classList.toggle("is-on", b.dataset.cible === cible));
    $("cible-une").hidden = cible !== "une";
    const choisie = offres.find((o) => String(o.id) === $("offre-select").value);
    $("cible-info").textContent = cible === "toutes"
      ? `Votre CV sera comparé à l'ensemble des ${fmt(offres.length)} offres : les compétences les plus demandées comptent le plus.`
      : choisie ? `Offre choisie : ${choisie.intitule} — ${choisie.entreprise}${choisie.lieu ? ` · ${choisie.lieu}` : ""}.`
      : "Choisissez l'offre qui vous intéresse dans la liste.";
    majBouton();
  };
  document.querySelectorAll("#cible-choix .filter").forEach((b) => b.addEventListener("click", () => { cible = b.dataset.cible; majCible(); }));
  $("offre-recherche").addEventListener("input", remplirOffres);
  $("offre-select").addEventListener("change", majCible);

  // ---------- analyse ----------
  function conseilsGeneraux(brut, offre) {
    const texte = normaliser(brut), plie = foldTxt(texte), liste = [];
    const chiffres = (texte.match(/\d+(?:[.,\s]\d{3})*(?:[.,]\d+)?\s?(?:%|€|euros?|k€|K€|k\b|x\b|abonnés|followers|leads|clients|participants|personnes|visiteurs|vues)/gi) || []).length;
    if (chiffres < 3) liste.push({ titre: "Chiffrez vos résultats",
      texte: `Votre CV contient ${chiffres} résultat(s) chiffré(s). Les recruteurs en marketing attendent des preuves : « +25 % d'ouverture », « 300 participants », « budget de 2 000 € ».` });
    if (!/marketing (digital|operationnel|numerique)|digital marketing|webmarketing/.test(plie))
      liste.push({ titre: "Affichez le bon intitulé en haut du CV",
        texte: `Écrivez sous votre nom le poste visé${offre ? ` (par exemple « ${offre.intitule.replace(/\s*\(.*?\)\s*/g, " ").trim()} »)` : " : « Chargée de marketing digital et opérationnel »"}. Les logiciels de tri et les recruteurs cherchent d'abord ce titre.` });
    if (offre && offre.contrat === "Alternance" && !/alternance|apprenti/.test(plie))
      liste.push({ titre: "Précisez que vous cherchez une alternance", texte: "Indiquez le rythme (ex. 3 semaines entreprise / 1 semaine école) et la formation préparée." });
    if (!/linkedin/.test(plie)) liste.push({ titre: "Ajoutez votre profil LinkedIn", texte: "Un lien vers votre LinkedIn (et vers ce site !) permet au recruteur d'en voir plus." });
    const mots = texte.split(/\s+/).filter(Boolean).length;
    if (mots > 900) liste.push({ titre: "Allégez votre CV", texte: `${fmt(mots)} mots : visez une page, avec des puces courtes et les compétences clés en évidence.` });
    return liste;
  }

  function analyser() {
    const presents = detecter(texteCV);
    let attendus, offre = null, score;
    if (cible === "une") {
      offre = offres.find((o) => String(o.id) === $("offre-select").value);
      attendus = (offre && offre.termes || []).map((nom) => termes.find((t) => t.terme === nom)).filter(Boolean);
      score = attendus.length ? attendus.filter((t) => presents.has(t.terme)).length / attendus.length : 0;
    } else {
      attendus = termes.filter((t) => t.pct >= 10);
      const total = attendus.reduce((s, t) => s + t.pct, 0);
      score = total ? attendus.filter((t) => presents.has(t.terme)).reduce((s, t) => s + t.pct, 0) / total : 0;
    }
    attendus.sort((a, b) => b.pct - a.pct);
    const ok = attendus.filter((t) => presents.has(t.terme)), manque = attendus.filter((t) => !presents.has(t.terme));
    const pctScore = Math.round(score * 100);

    // score
    $("resultat").hidden = false;
    $("score-valeur").textContent = `${pctScore} %`;
    requestAnimationFrame(() => $("score-anneau").style.setProperty("--p", pctScore));
    $("score-titre").textContent = offre ? `Correspondance avec « ${offre.intitule} »` : "Correspondance avec le marché";
    $("score-texte").textContent = pctScore >= 70 ? "Très bon profil pour ce poste : peaufinez les détails ci-dessous."
      : pctScore >= 45 ? "Bonne base : quelques ajouts ciblés rendront votre CV nettement plus visible."
      : "Votre CV montre encore peu de ce que demandent les annonces : suivez les conseils prioritaires ci-dessous.";

    // top 5 des offres : part des compétences de l'offre présentes dans le CV
    // (offres avec au moins 5 compétences repérées, pour éviter les 100 % trop faciles)
    const classement = offres.filter((o) => (o.termes || []).length >= 5).map((o) => {
      const faits = o.termes.filter((n) => presents.has(n));
      return { o, faits: faits.length, total: o.termes.length, pct: Math.round(faits.length / o.termes.length * 100) };
    }).sort((a, b) => b.pct - a.pct || b.faits - a.faits).slice(0, 5);
    $("src-top").textContent = `Calcul : part des compétences demandées dans chaque offre que l'on retrouve dans votre CV (${fmt(offres.length)} offres comparées).`;
    clear($("top-offres"));
    classement.forEach(({ o, faits, total, pct }) => {
      const choisie = offre && String(offre.id) === String(o.id);
      const comparer = el("a", { href: `cv.html?offre=${encodeURIComponent(o.id)}`, class: "offre-cv",
        text: choisie ? "✓ Analyse affichée au-dessus" : "Analyser pour cette offre" });
      comparer.addEventListener("click", (e) => {
        e.preventDefault();
        cible = "une"; $("offre-recherche").value = ""; remplirOffres(); $("offre-select").value = o.id; majCible();
        history.replaceState(null, "", `cv.html?offre=${encodeURIComponent(o.id)}`);
        analyser();
        const carte = document.querySelector(".cv-score-card");
        carte.classList.remove("is-flash"); void carte.offsetWidth; carte.classList.add("is-flash");
      });
      $("top-offres").append(el("li", { class: choisie ? "is-choisie" : null },
        el("span", { class: "cv-top-pct", text: `${pct} %` }),
        el("div", { class: "cv-top-info" },
          el("strong", { text: o.intitule }),
          el("span", { class: "src", text: [o.entreprise, o.lieu, o.contrat_libelle || o.contrat].filter(Boolean).join(" · ") }),
          el("span", { class: "src", text: `${faits} compétence${faits > 1 ? "s" : ""} sur ${total} déjà dans votre CV` })),
        el("div", { class: "offre-liens" },
          el("a", { href: o.url, target: "_blank", rel: "noopener", text: "Voir l'offre →" }), comparer)));
    });

    // compétences
    const pctTxt = (t) => offre ? "" : ` · ${fmtPct(t.pct)}`;
    $("src-presents").textContent = `${ok.length} sur ${attendus.length} ${offre ? "compétences citées dans l'offre" : "compétences demandées dans au moins 10 % des offres"}.`;
    $("src-manquants").textContent = manque.length ? "Les plus demandées en premier." : "Rien ne manque, bravo !";
    clear($("presents")); clear($("manquants"));
    ok.forEach((t) => $("presents").append(el("span", { class: "tag present", text: `${t.terme}${pctTxt(t)}` })));
    manque.forEach((t) => $("manquants").append(el("span", { class: "tag manque", text: `${t.terme}${pctTxt(t)}` })));

    // conseils : d'abord ce qu'on a pratiqué mais pas écrit, puis les compétences manquantes, puis la forme
    const liste = [];
    manque.filter((t) => vuEnFormation(t.terme)).forEach((t) => liste.push({ titre: `${t.terme} : vous l'avez pratiqué, écrivez-le !`,
      texte: `C'est dans vos compétences déjà acquises, mais pas dans votre CV. ${CONSEILS[t.terme] || CONSEIL_CATEGORIE}` }));
    manque.filter((t) => !vuEnFormation(t.terme)).slice(0, 5).forEach((t) => liste.push({
      titre: `${t.terme}${offre ? " (demandé dans l'offre)" : ` (demandé dans ${fmtPct(t.pct)} des offres)`}`,
      texte: CONSEILS[t.terme] || CONSEIL_CATEGORIE }));
    liste.push(...conseilsGeneraux(texteCV, offre));
    clear($("conseils"));
    liste.slice(0, 9).forEach((c) => $("conseils").append(el("li", {}, el("strong", { text: c.titre }), el("p", { class: "src", text: c.texte }))));
    const y = $("resultat").getBoundingClientRect().top + window.scrollY - 90;
    window.scrollTo({ top: y, behavior: "smooth" });
  }
  $("analyser").addEventListener("click", analyser);

  // ---------- chargement des données ----------
  (async () => {
    const [t, s] = await Promise.all([loadJSON("data/termes.json"), loadJSON("data/offres_site.json")]);
    if (!t || !s) { $("cible-info").textContent = "Les données ne sont pas encore disponibles."; return; }
    termes = t.termes.map(compiler);
    formation = t.formation || [];
    offres = s.offres;
    remplirOffres();
    const id = new URLSearchParams(location.search).get("offre");
    if (id && offres.some((o) => String(o.id) === id)) { cible = "une"; $("offre-select").value = id; }
    majCible();
  })();
})();
