"""Le programme detaille de la semaine : ce qu'il y a a faire, etape par etape.

Le plan disait "45 min" et "sortie longue 18 km". Ca suffit pour un volume,
pas pour aller courir. Ce module transforme une semaine du plan en cinq
seances decrites pas a pas, avec une allure cible par etape prise dans la
calibration, donc recalculee apres chaque course.

Les seances de qualite etaient jusqu'ici de la prose dans les notes du plan
("3 x 6 min a allure semi"). Ecrites en structure, elles deviennent
exportables vers la montre : c'est la meme description qui nourrit la page et
le fichier envoye a Garmin.
"""

# Les jours ne sont que des SUGGESTIONS. Ce qui compte dans une semaine
# d'entrainement, ce n'est pas le jour mais l'espacement : la sortie longue et
# la seance de qualite ne doivent pas se toucher, le reste se pose ou il veut.
# Chaque seance porte donc sa souplesse :
#   libre    : n'importe quel jour de la semaine
#   espacee  : au moins 48 h d'une autre seance exigeante
#   ancree   : une date imposee, c'est le cas d'une course
JOUR_S1, JOUR_S2, JOUR_LONGUE = "mardi", "jeudi", "samedi"
JOUR_RENFO = ("mercredi", "vendredi")

LIBRE = ("libre", "N'importe quel jour, c'est une séance facile.")
ESPACEE = ("espacee", "Au moins 48 h avant ou après la sortie longue.")
LONGUE = ("espacee", "Au moins 48 h après la séance de qualité. "
                     "C'est la seule séance qui demande vraiment un créneau.")
RENFO_SOUPLESSE = ("libre", "N'importe quel jour, mais pas la veille de la "
                            "sortie longue.")

ECHAUFFEMENT_S = 600     # 10 min avant une seance de qualite
RETOUR_S = 600           # 10 min apres

# Les seances de qualite, par semaine du plan. Elles viennent des notes ecrites
# a la main, mais en structure plutot qu'en prose.
QUALITE = {
    5:  {"nom": "3 × 6 min à allure semi", "reps": 3, "effort_s": 360,
         "recup_s": 120, "zone": "semi",
         "pourquoi": "Première séance au-dessus de l'endurance. Elle habitue "
                     "la foulée au rythme du semi sans coûter de récupération."},
    13: {"nom": "2 × 15 min à allure marathon", "reps": 2, "effort_s": 900,
         "recup_s": 180, "zone": "marathon",
         "pourquoi": "L'allure marathon doit devenir un automatisme. Quinze "
                     "minutes suffisent pour l'installer sans fatiguer."},
    17: {"nom": "3 × 10 min au seuil", "reps": 3, "effort_s": 600,
         "recup_s": 180, "zone": "seuil",
         "pourquoi": "Le seuil relève le plafond. C'est lui qui rend l'allure "
                     "marathon plus confortable ensuite."},
    26: {"nom": "4 × 3 min à allure marathon", "reps": 4, "effort_s": 180,
         "recup_s": 90, "zone": "marathon",
         "pourquoi": "Affûtage : on rappelle l'allure aux jambes, on ne "
                     "construit plus rien."},
}

# Sorties longues qui se terminent plus vite que leur debut.
FINALE = {
    6:  {"km": 5, "zone": "semi"},
    14: {"km": 5, "zone": "marathon"},
    18: {"km": 8, "zone": "marathon"},
    21: {"km": 6, "zone": "marathon"},
    23: {"km": 30, "zone": "marathon"},
}

RENFO = {
    "mercredi": {"nom": "Haut du corps et tractions",
                 "exos": ["Tractions, 5 séries jusqu'à 2 répétitions de la réserve",
                          "Dips lestés, 4 × 6 à 8",
                          "Rowing haltère, 4 × 8",
                          "Travail de muscle-up : tractions explosives, 5 × 3",
                          "Gainage latéral, 3 × 45 s par côté"],
                 "pourquoi": "Le haut du corps ne fait pas courir plus vite, "
                             "mais un tronc solide tient la posture quand la "
                             "fatigue arrive au 30e kilomètre."},
    "vendredi": {"nom": "Gainage et travail ATR",
                 "exos": ["Squats, 4 × 8",
                          "Fentes bulgares, 3 × 10 par jambe",
                          "Mollets debout, 4 × 15",
                          "Travail ATR contre le mur, 5 × 30 s",
                          "Gainage ventral, 3 × 60 s"],
                 "pourquoi": "Les jambes encaissent 2,5 fois le poids du corps "
                             "à chaque appui. Le renforcement est ce qui "
                             "protège des blessures de volume."},
}


def _allure(s):
    return "%d:%02d" % (s // 60, s % 60)


def zones_par_cle(calibration):
    """Bornes d'allure en secondes par kilometre, indexees par cle.

    L'allure semi n'est pas une zone de Daniels : elle se deduit de la
    projection sur 21,0975 km, qui se recalcule apres chaque course comme le
    reste.
    """
    z = {c["cle"]: (c["rapide_s_km"], c["lent_s_km"]) for c in calibration["zones"]}
    semi = calibration["projections"]["semi"]["temps_s"] / 21.0975
    # La projection sur semi suppose une endurance specifique pas encore
    # construite : elle ressortait plus rapide que le seuil, ce qui est faux.
    # L'allure semi se tient forcement entre l'allure marathon et le seuil.
    plancher = z["seuil"][1] + 3
    plafond = z["marathon"][0] - 3
    semi = max(plancher, min(plafond, semi))
    z["semi"] = (round(semi - 4), round(semi + 4))
    return z


def _etape(nom, zones, cle, duree_s=None, distance_m=None, consigne=None):
    rapide, lent = zones[cle]
    return {"nom": nom, "zone": cle, "duree_s": duree_s, "distance_m": distance_m,
            "allure_rapide_s_km": rapide, "allure_lente_s_km": lent,
            "allure_texte": "%s à %s /km" % (_allure(rapide), _allure(lent)),
            "consigne": consigne}


def _endurance(minutes, zones, nom="Endurance fondamentale"):
    return {
        "type": "course", "nom": nom, "duree_min": minutes,
        "pourquoi": "La séance qui construit la base aérobie : plus de "
                    "capillaires, un cœur qui remplit mieux, une meilleure "
                    "utilisation des graisses. Elle ne vaut que si elle reste "
                    "lente.",
        "etapes": [_etape("Endurance", zones, "ef", duree_s=minutes * 60,
                          consigne="Tu dois pouvoir tenir une conversation "
                                   "entière. Si ce n'est pas le cas, ralentis.")],
    }


def _qualite(q, zones):
    et = [_etape("Échauffement", zones, "ef", duree_s=ECHAUFFEMENT_S,
                 consigne="Progressif, sans jamais forcer.")]
    for i in range(q["reps"]):
        et.append(_etape("Effort %d sur %d" % (i + 1, q["reps"]), zones,
                         q["zone"], duree_s=q["effort_s"],
                         consigne="Allure régulière du début à la fin de "
                                  "l'intervalle."))
        if i < q["reps"] - 1:
            et.append(_etape("Récupération", zones, "ef", duree_s=q["recup_s"],
                             consigne="Trot lent, pas d'arrêt complet."))
    et.append(_etape("Retour au calme", zones, "ef", duree_s=RETOUR_S))
    duree = sum(e["duree_s"] for e in et) // 60
    return {"type": "course", "nom": q["nom"], "duree_min": duree,
            "pourquoi": q["pourquoi"], "etapes": et}


def _longue(km, zones, finale):
    et = []
    # Quand la finale couvre toute la distance, il s'agit d'un test a allure
    # cible, pas d'une sortie a finale rapide : un echauffement, puis l'effort.
    # Sans ce cas, le test 30K sortait avec une etape d'endurance de 0,0 km.
    if finale and km - finale["km"] <= .5:
        et.append(_etape("Échauffement", zones, "ef", distance_m=2000,
                         consigne="Deux kilomètres tranquilles avant de "
                                  "prendre l'allure cible."))
        et.append(_etape("Test à allure marathon", zones, finale["zone"],
                         distance_m=round(km * 1000),
                         consigne="L'allure doit rester tenue du premier au "
                                  "dernier kilomètre. C'est ce que dira la "
                                  "seconde moitié qui compte."))
        return {"type": "course", "nom": "Test %s km à allure marathon" % _km(km),
                "distance_km": km,
                "pourquoi": "L'indicateur le plus fiable avant Barcelone. Tenir "
                            "l'allure cible sur 30 km valide la préparation, "
                            "ou dit qu'il faut revoir l'objectif.",
                "etapes": et}
    if finale:
        et.append(_etape("Endurance", zones, "ef",
                         distance_m=round((km - finale["km"]) * 1000),
                         consigne="La première partie doit sembler trop facile."))
        et.append(_etape("Finale à %s" % ("allure marathon" if finale["zone"] == "marathon"
                                          else "allure semi"),
                         zones, finale["zone"],
                         distance_m=round(finale["km"] * 1000),
                         consigne="C'est ici que la séance se joue : accélérer "
                                  "sur des jambes déjà fatiguées."))
        pourquoi = ("Une sortie longue à finale rapide reproduit ce qui se "
                    "passe au 30e kilomètre d'un marathon : tenir l'allure "
                    "quand le glycogène baisse.")
    else:
        et.append(_etape("Endurance", zones, "ef", distance_m=round(km * 1000),
                         consigne="Allure constante, aucune accélération. "
                                  "Bois toutes les 20 minutes au-delà de 90 min."))
        pourquoi = ("La séance qui décide d'un marathon : réserves de "
                    "glycogène, résistance des appuis, tolérance à l'inconfort.")
    return {"type": "course", "nom": "Sortie longue %s km" % _km(km),
            "distance_km": km, "pourquoi": pourquoi, "etapes": et}


def _km(v):
    return ("%.1f" % v).rstrip("0").rstrip(".").replace(".", ",")


def programme(w, calibration, courses):
    """Les cinq seances d'une semaine du plan, decrites pas a pas."""
    zones = zones_par_cle(calibration)
    course = next((c for c in courses if c["semaine"] == w["semaine"]), None)
    out = []

    def pose(seance, jour, souplesse):
        seance = dict(seance)
        seance["jour_suggere"] = jour
        seance["souplesse"], seance["contrainte"] = souplesse
        return seance

    s1 = w.get("seance1_min")
    if s1:
        out.append(pose(_endurance(s1, zones), JOUR_S1, LIBRE))

    s2 = w.get("seance2_min")
    q = QUALITE.get(w["semaine"])
    if q and s2:
        out.append(pose(_qualite(q, zones), JOUR_S2, ESPACEE))
    elif s2:
        out.append(pose(_endurance(s2, zones), JOUR_S2, LIBRE))

    if course:
        # Une course a une date, elle. C'est la seule seance vraiment ancree.
        out.append(pose({"type": "course", "course": True,
                         "nom": "%s · %s" % (course["nom"], course["cible"]),
                         "distance_km": course["distance_km"],
                         "pourquoi": course["role"], "etapes": []},
                        course["jour"],
                        ("ancree", "Date imposée par la course.")))
    else:
        out.append(pose(_longue(w["sortie_longue_km"], zones,
                                FINALE.get(w["semaine"])), JOUR_LONGUE, LONGUE))

    for j in JOUR_RENFO:
        out.append(pose(dict(RENFO[j], type="renfo"), j, RENFO_SOUPLESSE))

    # L'ordre est celui de la lecture : les courses d'abord, du plus facile au
    # plus exigeant, puis le renforcement. Ce n'est pas un ordre d'execution.
    rang = {"course": 0, "renfo": 1}
    for i, x in enumerate(out):
        x["ordre"] = i + 1
    out.sort(key=lambda x: (rang[x["type"]], x["ordre"]))
    for i, x in enumerate(out):
        x["ordre"] = i + 1
    return out


def construit(plan, calibration, ajustees, semaine_courante, combien=3):
    """Le programme de la semaine en cours et des suivantes.

    Les semaines reecrites par l'adaptation sont prises dans leur version
    adaptee : le programme doit dire ce qu'il faut faire vraiment, pas ce que
    le plan demandait avant de t'ecouter.
    """
    if not semaine_courante:
        semaine_courante = 1
    par_semaine = {a["semaine"]: a for a in (ajustees or [])}
    out = []
    for w in plan["semaines"]:
        if not (semaine_courante <= w["semaine"] < semaine_courante + combien):
            continue
        a = par_semaine.get(w["semaine"])
        eff = dict(w)
        if a:
            eff["sortie_longue_km"] = a["longue_adapte"]
            eff["seance1_min"] = a["seance1_adapte"]
            eff["seance2_min"] = a["seance2_adapte"]
            eff["volume_km"] = a["volume_adapte"]
        out.append({
            "semaine": w["semaine"], "lundi": w["lundi"], "dimanche": w["dimanche"],
            "bloc": w["bloc"], "note": w.get("note"),
            "volume_km": eff["volume_km"], "adapte": bool(a),
            "seances": programme(eff, calibration, plan["courses"]),
        })
    return out
