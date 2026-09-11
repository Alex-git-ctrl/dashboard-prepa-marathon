"""Un resume d'analyse par seance : ai-je bien couru, est-ce conforme au plan,
a quoi servait cette seance.

Deux sources possibles, et la page dit toujours laquelle a parle.

  - Claude, si ANTHROPIC_API_KEY est disponible. Il voit la seance, ce que le
    plan prevoyait, les allures calibrees et l'historique recent. C'est ce qui
    produit une vraie lecture, avec des nuances qu'aucune regle n'attrape.
  - Une analyse par regles sinon. Elle est honnete mais mecanique, et elle est
    etiquetee comme telle sur la page. Elle sert de repli, pas de faux-semblant.

Les resumes sont caches sur disque et cles sur le contenu de la seance : la
collecte tourne deux fois par jour, et rien ne justifie de repayer un appel
pour une sortie qui n'a pas bouge.
"""

import hashlib
import json
import os

CACHE = "docs/resumes.json"
MODELE = "claude-opus-5"

# Le sujet est un coureur precis avec un objectif precis. Le modele doit
# raisonner sur SA preparation, pas reciter des generalites d'entrainement.
SYSTEME = """Tu analyses les séances d'un coureur qui prépare le marathon de \
Barcelone du 14 mars 2027, avec un objectif sous 4 heures, soit 5:41 au \
kilomètre. Il court trois fois par semaine et fait deux séances de musculation.

Tu écris en français, en tutoyant, comme un entraîneur qui connaît le dossier \
et parle à son athlète après la séance. Court, concret, appuyé sur les chiffres \
qu'on te donne. Tu ne félicites pas par politesse et tu n'alarmes pas pour \
faire sérieux : s'il n'y a rien à signaler, tu le dis en une phrase.

Règles d'écriture strictes :
- JAMAIS le caractère tiret cadratin, ni le tiret demi-cadratin. Utilise un \
point, deux points, une virgule ou une parenthèse.
- Pas de superlatifs creux, pas de « n'hésite pas à », pas de « il est \
important de ».
- Tu cites les chiffres réels de la séance, jamais des valeurs inventées.
- Si une donnée manque, tu le dis au lieu de supposer.

Tu réponds UNIQUEMENT par un objet JSON, sans texte autour, avec exactement \
ces clés :
  "verdict"   : un mot parmi "bon", "correct", "attention"
  "titre"     : maximum 7 mots, ce que la séance a été en une formule
  "execution" : 2 à 3 phrases. A-t-il bien couru ? Allure, cardiaque, dérive, \
régularité des kilomètres.
  "conformite": 1 à 2 phrases. Est-ce que ça suit le plan de la semaine ? Si \
la séance n'était pas au plan, dis-le simplement.
  "objectif"  : 1 à 2 phrases. A quoi servait cette séance dans une \
préparation marathon, et est-ce que ce rôle a été rempli."""


def _cle(charge):
    """Empreinte du contenu envoye : si la seance ne bouge pas, on ne repaie pas."""
    return hashlib.sha256(
        json.dumps(charge, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()[:16]


def _allure(s):
    return None if s is None else "%d:%02d" % (s // 60, s % 60)


def _fr(x):
    """Virgule decimale : le repli ecrit du francais, pas du float Python."""
    return ("%g" % x).replace(".", ",")


def contexte(seance, plan, calibration, precedentes):
    """Ce qu'on met sous les yeux de l'analyste, humain ou modele."""
    sem = next((w for w in plan["semaines"]
                if w["lundi"] <= seance["date"] <= w["dimanche"]), None)
    jours = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
    from datetime import date
    jd = jours[date.fromisoformat(seance["date"]).weekday()]

    prevu = None
    if sem:
        course = next((c for c in plan["courses"]
                       if c["semaine"] == sem["semaine"] and c["jour"] == jd), None)
        if course:
            prevu = "%s, %s km, objectif %s" % (
                course["nom"], course["distance_km"], course["cible"])
        elif jd == "mardi" and sem.get("seance1_min"):
            prevu = "%d min en endurance fondamentale" % sem["seance1_min"]
        elif jd == "jeudi" and sem.get("seance2_min"):
            prevu = "%d min en endurance fondamentale" % sem["seance2_min"]
        elif jd == "samedi":
            prevu = "sortie longue de %s km" % sem["sortie_longue_km"]

    # Les zones de la montre, pas celles d'Intervals : le resume doit citer
    # les memes chiffres que ceux affiches sur la page et sur la Forerunner.
    noms = ["Z1 échauffement", "Z2 facile", "Z3 aérobie", "Z4 seuil",
            "Z5 maximum"]
    zm = seance.get("zones_montre") or {}
    zones = {}
    tot = sum(zm.get("secondes") or [])
    if tot:
        for i, v in enumerate(zm["secondes"]):
            zones[noms[i]] = round(v / tot * 100)

    return {
        "date": seance["date"],
        "jour_de_semaine": jd,
        # Sans cette borne, une seance anterieure au plan sortait avec une
        # semaine vide, et l'analyse concluait "impossible de dire si cette
        # sortie correspond au programme" au lieu de la bonne reponse : elle
        # est anterieure, elle sert de point de depart.
        "premier_jour_du_plan": plan["semaines"][0]["lundi"],
        "jour_de_la_course": plan["courses"][-1]["date"],
        "semaine_du_plan": sem["semaine"] if sem else None,
        "bloc": sem.get("bloc_desc") if sem else None,
        "prevu_au_plan": prevu,
        "objectif_volume_semaine_km": sem["volume_km"] if sem else None,
        "distance_km": seance.get("km"),
        "duree_min": seance.get("minutes"),
        "allure_min_km": _allure(seance.get("allure_s_km")),
        "allure_ajustee_denivele_min_km": _allure(seance.get("gap_s_km")),
        "denivele_positif_m": seance.get("deniv"),
        "fc_moyenne": seance.get("fc_moy"),
        "fc_max": seance.get("fc_max_reelle") or seance.get("fc_max"),
        "derive_cardiaque_pct": seance.get("derive_pct"),
        "puissance_moyenne_w": seance.get("puissance_moy"),
        "cadence_pas_min": (round(seance["cadence"] * 2)
                            if seance.get("cadence") and seance["cadence"] < 120
                            else seance.get("cadence")),
        "dynamique_de_foulee": {
            "contact_au_sol_ms": (seance.get("dyn") or {}).get("stance_time"),
            "ratio_vertical_pct": (seance.get("dyn") or {}).get("vertical_ratio"),
            "oscillation_verticale_mm": (seance.get("dyn") or {})
            .get("vertical_oscillation"),
            "longueur_de_foulee_mm": (seance.get("dyn") or {}).get("step_length"),
        } if seance.get("dyn") else None,
        "repartition_zones_fc_pct": zones or None,
        "premiere_moitie_min_km": _allure(seance.get("premiere_moitie_s_km")),
        "seconde_moitie_min_km": _allure(seance.get("seconde_moitie_s_km")),
        "effort_percu_sur_10": seance.get("rpe"),
        "allures_de_reference": {z["nom"]: z["texte"] for z in calibration["zones"]},
        "allure_cible_marathon": calibration["cible_marathon"]["allure"],
        "seances_precedentes": [
            {"date": p["date"], "km": p.get("km"),
             "allure": _allure(p.get("allure_s_km")), "fc": p.get("fc_moy")}
            for p in precedentes[-4:]
        ],
    }


# ----------------------------------------------------------------- repli
def par_regles(c):
    """Analyse mecanique, sans modele. Etiquetee comme telle sur la page.

    Elle ne remplace pas une lecture, elle evite une case vide. Chaque phrase
    s'appuie sur un seuil explicite, jamais sur une impression.
    """
    z = c.get("repartition_zones_fc_pct") or {}
    # L'endurance sur la montre, c'est Z1 plus Z2 plus Z3 : jusqu'a 160 bpm,
    # soit 80 % de la FC max, l'effort reste aerobie.
    endurance = (z.get("Z1 échauffement", 0) + z.get("Z2 facile", 0)
                 + z.get("Z3 aérobie", 0))
    derive = c.get("derive_cardiaque_pct")

    ex = []
    verdict = "correct"
    if endurance:
        ex.append("%d %% du temps en endurance." % endurance)
        if endurance >= 75:
            verdict = "bon"
        elif endurance < 55:
            verdict = "attention"
            ex.append("C'est trop rapide pour une séance qui doit construire "
                      "la base aérobie.")
    if derive is not None:
        if derive > 8:
            verdict = "attention"
            ex.append("Dérive cardiaque de %s %%, au-delà du seuil de 5 %% : "
                      "la fin de séance a coûté cher." % _fr(derive))
        elif derive > 5:
            ex.append("Dérive cardiaque de %s %%, juste au-dessus du seuil "
                      "de 5 %%." % _fr(derive))
        else:
            ex.append("Dérive cardiaque de %s %%, sous le seuil de 5 %%." % _fr(derive))
    a, b = c.get("premiere_moitie_min_km"), c.get("seconde_moitie_min_km")
    if a and b:
        ex.append("Première moitié à %s/km, seconde à %s/km." % (a, b))
    if c.get("denivele_positif_m") and c.get("allure_ajustee_denivele_min_km"):
        ex.append("Avec %s m de dénivelé, l'allure vaut %s/km sur le plat."
                  % (c["denivele_positif_m"], c["allure_ajustee_denivele_min_km"]))

    if c.get("prevu_au_plan"):
        conf = ("Le plan prévoyait %s pour ce jour, et tu as couru %s km en "
                "%s min." % (c["prevu_au_plan"], _fr(c.get("distance_km") or 0),
                             c.get("duree_min")))
    elif c.get("semaine_du_plan"):
        conf = "Rien n'était prévu ce jour-là dans le plan."
    else:
        conf = "Cette séance est antérieure au démarrage du plan."

    obj = ("Une sortie en endurance fondamentale sert à construire la base "
           "aérobie : plus de capillaires, un cœur qui remplit mieux, une "
           "meilleure utilisation des graisses. Elle ne vaut que si elle "
           "reste lente.")
    if c.get("distance_km") and c["distance_km"] >= 15:
        obj = ("Une sortie longue habitue le corps à durer : réserves de "
               "glycogène, résistance des appuis, tolérance à l'inconfort. "
               "C'est la séance qui décide d'un marathon.")

    return {"verdict": verdict,
            "titre": "Analyse automatique",
            "execution": " ".join(ex) or "Trop peu de mesures pour juger.",
            "conformite": conf,
            "objectif": obj,
            "source": "regles"}


# ----------------------------------------------------------------- Claude
def par_claude(c):
    """Analyse redigee par Claude. Renvoie None si l'appel n'aboutit pas."""
    try:
        import anthropic
    except ImportError:
        return None
    if not (os.environ.get("ANTHROPIC_API_KEY")
            or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
        return None

    client = anthropic.Anthropic()
    try:
        reponse = client.messages.create(
            model=MODELE,
            max_tokens=4000,
            # Effort bas : la tache est courte et cadree, elle ne demande pas
            # une longue reflexion, et ce script tourne deux fois par jour.
            output_config={"effort": "low"},
            system=SYSTEME,
            messages=[{"role": "user", "content":
                       "Voici la séance à analyser.\n\n"
                       + json.dumps(c, ensure_ascii=False, indent=1)}],
        )
    except ImportError:
        return None
    except Exception as e:                     # noqa: BLE001
        # Une panne d'API ne doit jamais faire tomber la collecte : on repli.
        print("  resume : appel Claude impossible (%s)" % type(e).__name__)
        return None

    if reponse.stop_reason == "refusal":
        return None
    texte = "".join(b.text for b in reponse.content if b.type == "text").strip()
    d, f = texte.find("{"), texte.rfind("}")
    if d < 0 or f < d:
        return None
    try:
        out = json.loads(texte[d:f + 1])
    except json.JSONDecodeError:
        return None
    if not all(k in out for k in ("verdict", "execution", "conformite", "objectif")):
        return None
    out["source"] = "claude"
    out["modele"] = MODELE
    return out


# ----------------------------------------------------------------- entree
def construit(seances, plan, calibration, racine, combien=10):
    """Un resume par seance recente, en reutilisant le cache quand il tient."""
    chemin = os.path.join(racine, CACHE)
    try:
        with open(chemin, encoding="utf-8") as fh:
            cache = json.load(fh)
    except (OSError, json.JSONDecodeError):
        cache = {}

    out, appels = {}, 0
    for i, s in enumerate(seances[-combien:]):
        c = contexte(s, plan, calibration, seances[:len(seances) - combien + i])
        cle = _cle(c)
        vieux = cache.get(s["date"])
        # `fige` protege un resume ecrit a la main dans la conversation : sans
        # ca, la prochaine collecte le remplacerait par l'analyse par regles.
        if vieux and (vieux.get("fige") or vieux.get("cle") == cle):
            out[s["date"]] = vieux
            continue
        r = par_claude(c) or par_regles(c)
        r["cle"] = cle
        out[s["date"]] = r
        appels += 1

    with open(chemin, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, ensure_ascii=False)
    if appels:
        srcs = [out[k]["source"] for k in out]
        print("  resumes : %d regenere(s), %d par Claude, %d par regles"
              % (appels, srcs.count("claude"), srcs.count("regles")))
    return out
