"""Calibration : deduit le VDOT et les allures d'entrainement des courses reelles.

Sans ce module, les zones d'allure restent figees sur le 10 km de reference
et le tableau de bord se perime des la premiere course. Ici, chaque course
courue remplace la reference precedente et tout se recalcule : zones,
projections, allure cible.

Modele de Jack Daniels :
  VO2 a une vitesse v (m/min)  = -4.60 + 0.182258 v + 0.000104 v²
  fraction de VO2max tenable sur t minutes
                               = 0.8 + 0.1894393 e^(-0.012778 t)
                                     + 0.2989558 e^(-0.1932605 t)
  VDOT                         = VO2 / fraction

Les allures d'entrainement sont ensuite des fractions de la vitesse a VO2max.
"""

import math
from datetime import date

# Reference de depart : 10 km en 48 min, couru sans montre avant le plan.
SEED = {"distance_m": 10000, "temps_s": 48 * 60, "source": "10 km de référence",
        "date": None, "estime": True}

# Fractions de la vitesse a VO2max. Bornes basse et haute de chaque zone.
# Les usages decrivent le plan tel qu'il est ecrit dans build_plan.py : ils
# parlaient encore de la semaine 13 et des blocs 1 a 4 d'avant le report du
# semi au 05/12, alors que l'allure marathon arrive des la semaine 5.
ZONES = [
    ("ef", "Endurance fondamentale", 0.66, 0.73,
     "La majorité du volume, sorties longues comprises"),
    ("marathon", "Allure marathon", 0.79, 0.83,
     "Fractions dès la semaine 5, puis finales de sorties longues"),
    ("seuil", "Seuil", 0.86, 0.89, "Séances de 2 ou 3 × 8 à 10 min, environ une par mois"),
    ("dix", "Allure 10 km", 0.90, 0.93, "Rythme de course sur 10 km"),
    # Le fractionne court se court au-dessus de l'allure 10 km. La borne
    # haute reste sous la vitesse a VO2max : on cherche l'economie de
    # foulee, pas un record sur 400 m.
    ("vma", "Fractionné court", 0.95, 0.98,
     "Répétitions d’une minute et lignes droites, tout le plan"),
]


def vo2_a_vitesse(v):
    """v en metres par minute."""
    return -4.60 + 0.182258 * v + 0.000104 * v * v


def fraction_tenable(t_min):
    return (0.8 + 0.1894393 * math.exp(-0.012778 * t_min)
            + 0.2989558 * math.exp(-0.1932605 * t_min))


def vdot(distance_m, temps_s):
    t = temps_s / 60
    v = distance_m / t
    return vo2_a_vitesse(v) / fraction_tenable(t)


def vitesse_a_vo2max(cible):
    """Inverse de vo2_a_vitesse : la vitesse qui produit ce VO2, en m/min."""
    a, b, c = 0.000104, 0.182258, -4.60 - cible
    return (-b + math.sqrt(b * b - 4 * a * c)) / (2 * a)


def riegel(t1_s, d1_m, d2_m):
    """Projection d'un chrono sur une autre distance, exposant 1,06."""
    return t1_s * (d2_m / d1_m) ** 1.06


def mmss(sec_par_km):
    s = round(sec_par_km)
    return f"{s // 60}:{s % 60:02d}"


def hhmm(secondes):
    s = round(secondes)
    h, reste = divmod(s, 3600)
    m, sec = divmod(reste, 60)
    return f"{h}h{m:02d}" if h else f"{m}:{sec:02d}"


def allures(v_max):
    """Zones d'allure, en secondes par kilometre, de la plus lente a la plus rapide."""
    out = []
    for cle, nom, bas, haut, usage in ZONES:
        # v_max est en m/min : 1000/v donne des minutes par km, d'ou le x60.
        lent = 1000 / (v_max * bas) * 60
        rapide = 1000 / (v_max * haut) * 60
        out.append({"cle": cle, "nom": nom, "usage": usage,
                    "lent_s_km": round(lent), "rapide_s_km": round(rapide),
                    "texte": f"{mmss(rapide)} à {mmss(lent)}"})
    return out


# Une course planifiee est une FENETRE, pas une date. Le 10 km etait inscrit au
# samedi 26/09/2026 et a ete couru le dimanche 27 : un seul jour d'ecart, et la
# course n'etait jamais retenue. Le tableau de bord a donc continue d'afficher
# des zones calculees sur le 10 km ESTIME a 48 min, alors qu'une vraie
# performance existait. Une panne muette, exactement le genre que ce depot
# cherche a eviter.
#
# On tolere donc un ecart de quelques jours, MAIS on exige que la distance
# corresponde. C'est la seconde condition qui fait le travail : sans elle, la
# sortie facile du lendemain d'une course serait prise pour la course.
TOLERANCE_JOURS = 4
TOLERANCE_DISTANCE = 0.20


def _jour(iso):
    a, m, j = (int(v) for v in iso.split("-"))
    return date(a, m, j)


def _temps_s(s):
    """Le chrono le plus juste dont on dispose.

    `minutes` est arrondi a la minute. Sur le 10 km, l'ecart etait de 32 s,
    ce qui deplace le VDOT de 0,4 et toutes les zones d'allure avec lui, dans
    le sens flatteur. `allure_s_km` garde la seconde : on s'en sert des qu'elle
    est disponible, et on ne retombe sur les minutes qu'a defaut.
    """
    if s.get("allure_s_km") and s.get("km"):
        return s["allure_s_km"] * s["km"]
    return s["minutes"] * 60


def trouve_reference(seances, courses):
    """La performance la plus recente qui fasse foi.

    Une course officielle prime toujours sur un entrainement : c'est le seul
    contexte ou l'effort est reellement maximal. On retient la plus recente,
    pas la meilleure, parce que c'est l'etat de forme actuel qui interesse.
    """
    candidates = []
    for s in seances:
        if not s.get("km") or not s.get("minutes"):
            continue
        for c in courses:
            if not c.get("date"):
                continue
            ecart = abs((_jour(s["date"]) - _jour(c["date"])).days)
            if ecart > TOLERANCE_JOURS:
                continue
            attendue = c.get("distance_km")
            if attendue and abs(s["km"] - attendue) / attendue > TOLERANCE_DISTANCE:
                continue
            candidates.append({
                "distance_m": s["km"] * 1000,
                "temps_s": _temps_s(s),
                "source": c["nom"],
                "date": s["date"],
                "estime": False,
            })
            break
    if candidates:
        return sorted(candidates, key=lambda c: c["date"])[-1]
    return dict(SEED)


def calcule(seances, courses, cible_marathon_s_km=341):
    """Renvoie tout ce que le tableau de bord doit afficher sur la calibration.

    cible_marathon_s_km : l'allure visee, 5:41/km pour le sub-4h. C'est une
    decision, pas une deduction : elle reste separee des zones physiologiques.
    """
    ref = trouve_reference(seances, courses)
    v = vdot(ref["distance_m"], ref["temps_s"])
    v_max = vitesse_a_vo2max(v)
    zones = allures(v_max)

    proj = {}
    for cle, d in (("dix", 10000), ("semi", 21097.5), ("marathon", 42195)):
        t = riegel(ref["temps_s"], ref["distance_m"], d)
        proj[cle] = {"temps_s": round(t), "texte": hhmm(t),
                     "allure": mmss(t / (d / 1000)) + "/km"}

    return {
        "reference": {
            "source": ref["source"], "date": ref["date"], "estime": ref["estime"],
            "distance_km": round(ref["distance_m"] / 1000, 2),
            "temps": hhmm(ref["temps_s"]),
            "allure": mmss(ref["temps_s"] / (ref["distance_m"] / 1000)) + "/km",
        },
        "vdot": round(v, 1),
        "zones": zones,
        "projections": proj,
        "cible_marathon": {
            "allure": mmss(cible_marathon_s_km) + "/km",
            "temps": hhmm(cible_marathon_s_km * 42.195),
        },
        # Ecart entre ce que la physiologie autorise et l'objectif retenu.
        "marge_marathon_s": round(cible_marathon_s_km
                                  - proj["marathon"]["temps_s"] / 42.195),
    }
