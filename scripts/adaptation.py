"""Le plan ecoute ce qui s'est passe, et se recalcule.

Deux axes, jamais un seul. L'observance dit ce qui a ete fait, le cout dit ce
que ca a coute. Un plan qui ne regarde que l'observance recompense celui qui
fait tout en se detruisant ; un plan qui ne regarde que le cout finit par
tout alleger des qu'une nuit est mauvaise.

Le plan ecrit a la main reste la reference d'ambition. Ce module le module,
il ne le remplace pas : chaque semaine ajustee garde son volume d'origine a
cote, et la page affiche les deux avec la raison de l'ecart.

Regle d'honnetete qui prime sur tout le reste : quand les mesures manquent,
on ne decide pas. On suit le plan d'origine et on dit pourquoi.
"""

from datetime import date, timedelta

# ---------------------------------------------------------------- reglages
SEMAINES_REGARDEES = 3      # fenetre d'observance, en semaines terminees
SEMAINES_AJUSTEES = 3       # horizon d'application, en semaines a venir
RAMPE_MAX = 0.10            # +10 % d'une semaine a l'autre, la regle classique
MARGE_AMBITION = 0.10       # on peut depasser le plan d'origine de 10 %, pas plus
EF_PACE = 6.1               # min/km, la meme constante que build_plan
MINI_SEANCES = 2            # sous deux seances mesurees, l'observance ne dit rien
MINI_JOURS_VFC = 14         # reference glissante de la VFC et de la FC de repos

# Types de semaine que l'adaptation ne touche jamais.
INTOUCHABLES = {"COURSE", "TEST"}

# La matrice. Cle : (observance, cout) -> (facteur, action, phrase).
MATRICE = {
    ("haute", "faible"):  (1.10, "progresser_fort",
                           "tout a été fait, et ça t'a coûté peu"),
    ("haute", "normal"):  (1.07, "progresser",
                           "tout a été fait pour un coût normal"),
    ("haute", "eleve"):   (1.00, "maintenir",
                           "tout a été fait, mais ça t'a coûté cher"),
    ("moyenne", "faible"): (1.05, "progresser",
                            "presque tout a été fait, et facilement"),
    ("moyenne", "normal"): (1.00, "maintenir",
                            "une partie du plan est passée à la trappe"),
    ("moyenne", "eleve"):  (0.90, "alleger",
                            "le plan n'a pas été tenu, et ce qui l'a été a coûté cher"),
    ("basse", "faible"):   (1.00, "maintenir",
                            "peu de séances faites, mais sans difficulté apparente"),
    ("basse", "normal"):   (0.90, "alleger",
                            "trop de séances manquées pour repartir sur le volume prévu"),
    ("basse", "eleve"):    (0.80, "alleger_fort",
                            "peu de séances faites, et coûteuses : on repart plus bas"),
}


def _moy(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def _fr(gabarit, x):
    """Valeur affichee a la francaise : la virgule decimale, pas le point."""
    return (gabarit % x).replace(".", ",")


def _lin(x, x0, y0, x1, y1):
    """Interpolation lineaire bornee entre deux points de reference."""
    if x is None:
        return None
    if x1 == x0:
        return y0
    t = (x - x0) / (x1 - x0)
    return max(min(y0, y1), min(max(y0, y1), y0 + (y1 - y0) * t))


# ============================================================== observance
def observance(metrics, plan, aujourd_hui):
    """Ce qui a ete fait, sur les dernieres semaines TERMINEES.

    La semaine en cours ne compte pas : la juger a mi-parcours reviendrait a
    sanctionner un mardi.
    """
    faites = metrics.get("semaines") or {}
    lignes = []
    for w in plan["semaines"]:
        fin = date.fromisoformat(w["dimanche"])
        if fin >= aujourd_hui:
            continue
        reel = faites.get(str(w["semaine"]), {})
        prevu_km = w["volume_km"] or 0
        prevu_seances = sum(1 for x in (w.get("seance1_min"), w.get("seance2_min")) if x) + 1
        lignes.append({
            "semaine": w["semaine"],
            "km_prevu": prevu_km,
            "km_fait": round(reel.get("km", 0), 1),
            "seances_prevues": prevu_seances,
            "seances_faites": reel.get("seances", 0),
            "renfo_prevu": 2,
            "renfo_fait": reel.get("renfo_seances", 0),
            "ratio": round(reel.get("km", 0) / prevu_km, 3) if prevu_km else None,
        })

    recentes = lignes[-SEMAINES_REGARDEES:]
    km_p = sum(l["km_prevu"] for l in recentes)
    km_f = sum(l["km_fait"] for l in recentes)
    s_p = sum(l["seances_prevues"] for l in recentes)
    s_f = sum(l["seances_faites"] for l in recentes)
    return {
        "semaines": lignes,
        "fenetre": [l["semaine"] for l in recentes],
        "km_prevu": round(km_p, 1),
        "km_fait": round(km_f, 1),
        "seances_prevues": s_p,
        "seances_faites": s_f,
        "ratio": round(km_f / km_p, 3) if km_p else None,
        # Base de rampe : ce qui a VRAIMENT ete couru, jamais ce qui etait ecrit.
        # C'est la regle qui interdit le rattrapage.
        "base_km": round(km_f / len(recentes), 1) if recentes else None,
    }


def _niveau_observance(ratio, seances_faites):
    if ratio is None or seances_faites < MINI_SEANCES:
        return None
    return "haute" if ratio >= .95 else "moyenne" if ratio >= .70 else "basse"


# ==================================================================== cout
def cout(metrics, plan, aujourd_hui):
    """A quel point les dernieres semaines ont coute.

    Chaque composante rend des points de 0 a son maximum, et l'indice final
    est la moyenne ponderee des seules composantes mesurables. Une composante
    absente ne vaut pas zero : elle ne participe pas.
    """
    debut = aujourd_hui - timedelta(days=7 * SEMAINES_REGARDEES)
    seances = [s for s in (metrics.get("seances") or [])
               if date.fromisoformat(s["date"]) >= debut]
    jours = [j for j in ((metrics.get("sante") or {}).get("jours") or [])
             if date.fromisoformat(j["date"]) >= debut]
    serie = (metrics.get("sante") or {}).get("jours") or []

    C = []

    d = _moy([s.get("derive_pct") for s in seances])
    if d is not None:
        C.append(("Dérive cardiaque", _fr("%.1f %%", d), _lin(d, 0, 0, 10, 30), 30))

    rpes = [s["rpe"] for s in seances if s.get("rpe") is not None]
    if rpes:
        r = sum(rpes) / len(rpes)
        C.append(("Effort perçu", _fr("%.1f sur 10", r), _lin(r, 4, 0, 9, 30), 30))

    # Discipline de zone : le temps passe en endurance sur l'ensemble des
    # seances de la fenetre. Courir ses seances faciles trop vite est le
    # premier facteur de cout cache d'une preparation.
    z12 = z_tot = 0
    for s in seances:
        z = s.get("zones_fc") or {}
        z12 += (z.get("z1") or 0) + (z.get("z2") or 0)
        z_tot += sum(z.values())
    if z_tot:
        pct = z12 / z_tot * 100
        C.append(("Temps en endurance", "%d %%" % round(pct),
                  _lin(pct, 85, 0, 50, 25), 25))

    def reference(champ):
        vals = [j[champ] for j in serie[-28 - 7:-7] if j.get(champ) is not None]
        return sum(vals) / len(vals) if len(vals) >= MINI_JOURS_VFC else None

    ref_hrv, ref_fc = reference("hrv"), reference("fc_repos")
    recent_hrv = _moy([j.get("hrv") for j in serie[-7:]])
    recent_fc = _moy([j.get("fc_repos") for j in serie[-7:]])
    if ref_hrv and recent_hrv:
        ecart = (recent_hrv - ref_hrv) / ref_hrv * 100
        C.append(("Variabilité cardiaque", _fr("%+.0f %%", ecart),
                  _lin(ecart, 0, 0, -20, 30), 30))
    if ref_fc and recent_fc:
        ecart = recent_fc - ref_fc
        C.append(("FC de repos", _fr("%+.0f bpm", ecart), _lin(ecart, 0, 0, 5, 20), 20))

    nuits = [j["sommeil_h"] for j in jours if j.get("sommeil_h") is not None]
    if len(nuits) >= 4:
        dette = sum(max(0.0, 7 - h) for h in nuits) / len(nuits) * 7
        C.append(("Dette de sommeil", _fr("%.1f h sur la semaine", dette),
                  _lin(dette, 0, 0, 7, 15), 15))

    if not C:
        return {"indice": None, "niveau": None, "composantes": []}

    pris = sum(c[2] for c in C)
    maxi = sum(c[3] for c in C)
    indice = round(pris / maxi * 100)
    return {
        "indice": indice,
        "niveau": "faible" if indice < 30 else "normal" if indice <= 60 else "eleve",
        "composantes": [{"nom": n, "valeur": v, "points": round(p),
                         "max": m} for n, v, p, m in C],
    }


# =============================================================== decision
def decide(obs, ct):
    """La matrice, puis les garde-fous."""
    n_obs = _niveau_observance(obs["ratio"], obs["seances_faites"])
    n_cout = ct["niveau"]

    if n_obs is None or n_cout is None:
        manque = []
        if n_obs is None:
            manque.append("moins de %d séances mesurées sur la fenêtre"
                          % MINI_SEANCES)
        if n_cout is None:
            manque.append("aucun signal de coût exploitable")
        return {"action": "attendre", "facteur": 1.0,
                "raison": "Le plan d'origine s'applique : " + " et ".join(manque)
                          + ". Le moteur ne décide pas sans mesures.",
                "observance": n_obs, "cout": n_cout}

    facteur, action, phrase = MATRICE[(n_obs, n_cout)]
    return {"action": action, "facteur": facteur, "raison": phrase.capitalize()
            + ".", "observance": n_obs, "cout": n_cout}


# ============================================================ application
def _reecrit(w, facteur, base_km, plafond_km):
    """Reecrit une semaine : la sortie longue et les deux seances suivent.

    Le volume se recalcule avec la formule d'origine, pour que le plan adapte
    reste comparable au plan ecrit a la main.
    """
    longue = w["sortie_longue_km"] * facteur
    m1 = round((w.get("seance1_min") or 0) * facteur / 5) * 5
    m2 = round((w.get("seance2_min") or 0) * facteur / 5) * 5
    longue = round(longue * 2) / 2
    total = round((m1 + m2) / EF_PACE + longue, 1)

    # Garde-fou de rampe : jamais plus de +10 % sur la base reellement courue.
    if base_km and total > base_km * (1 + RAMPE_MAX):
        k = base_km * (1 + RAMPE_MAX) / total
        longue = round(longue * k * 2) / 2
        m1 = round(m1 * k / 5) * 5
        m2 = round(m2 * k / 5) * 5
        total = round((m1 + m2) / EF_PACE + longue, 1)

    # Garde-fou d'ambition : on ne depasse pas le plan d'origine de plus de
    # 10 %. La verification est faite APRES arrondi et repetee : mettre a
    # l'echelle puis arrondir pouvait rendre 28,1 pour un plafond de 28,05, et
    # un garde-fou qu'un arrondi suffit a franchir n'en est pas un.
    for _ in range(6):
        if total <= plafond_km + 1e-9:
            break
        if longue >= 1:
            longue -= .5
        elif m2 >= 5:
            m2 -= 5
        elif m1 >= 5:
            m1 -= 5
        else:
            break
        total = round((m1 + m2) / EF_PACE + longue, 1)

    return longue, m1, m2, total


def applique(plan, metrics, aujourd_hui=None):
    """Produit le plan adapte, la decision, et la trace de ce qui a bouge."""
    aujourd_hui = aujourd_hui or date.today()
    obs = observance(metrics, plan, aujourd_hui)
    ct = cout(metrics, plan, aujourd_hui)
    dec = decide(obs, ct)

    courante = None
    for w in plan["semaines"]:
        if date.fromisoformat(w["lundi"]) <= aujourd_hui <= date.fromisoformat(w["dimanche"]):
            courante = w["semaine"]
            break

    ajustees = []
    if dec["facteur"] != 1.0 and courante:
        cibles = [w for w in plan["semaines"]
                  if courante < w["semaine"] <= courante + SEMAINES_AJUSTEES]
        base = obs["base_km"]
        for w in cibles:
            if w.get("type") in INTOUCHABLES or w.get("course"):
                continue
            if w["semaine"] >= 25:              # affutage : intouchable
                continue
            avant = w["volume_km"]
            plafond = avant * (1 + MARGE_AMBITION)
            longue, m1, m2, total = _reecrit(w, dec["facteur"], base, plafond)
            if abs(total - avant) < .3:
                continue
            ajustees.append({
                "semaine": w["semaine"],
                "volume_origine": avant, "volume_adapte": total,
                "longue_origine": w["sortie_longue_km"], "longue_adapte": longue,
                "seance1_origine": w.get("seance1_min"), "seance1_adapte": m1 or None,
                "seance2_origine": w.get("seance2_min"), "seance2_adapte": m2 or None,
            })
            # On ne touche PAS au plan en memoire : plan.json reste le plan
            # d'ambition, et l'ecart voyage dans semaines_ajustees. La page
            # applique l'ajustement a l'affichage, en gardant l'origine a cote.
            base = total                        # la rampe s'enchaine de proche en proche

    return {
        "semaine_courante": courante,
        "observance": obs,
        "cout": ct,
        "decision": dec,
        "semaines_ajustees": ajustees,
        "reglages": {"rampe_max_pct": round(RAMPE_MAX * 100),
                     "fenetre_semaines": SEMAINES_REGARDEES,
                     "horizon_semaines": SEMAINES_AJUSTEES},
    }
