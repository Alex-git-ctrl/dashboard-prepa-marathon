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

# Reference de depart : 10 km en 48 min, couru sans montre avant le plan.
SEED = {"distance_m": 10000, "temps_s": 48 * 60, "source": "10 km de référence",
        "date": None, "estime": True}

# Fractions de la vitesse a VO2max. Bornes basse et haute de chaque zone.
ZONES = [
    ("ef", "Endurance fondamentale", 0.66, 0.73,
     "La majorité du volume, sorties longues comprises"),
    ("marathon", "Allure marathon", 0.79, 0.83,
     "Fractions spécifiques à partir de la semaine 13"),
    ("seuil", "Seuil", 0.86, 0.89, "Séances de 3 × 10 min, blocs 3 et 4"),
    ("dix", "Allure 10 km", 0.90, 0.93, "Rythme de course sur 10 km"),
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


def trouve_reference(seances, courses):
    """La performance la plus recente qui fasse foi.

    Une course officielle prime toujours sur un entrainement : c'est le seul
    contexte ou l'effort est reellement maximal. On retient la plus recente,
    pas la meilleure, parce que c'est l'etat de forme actuel qui interesse.
    """
    dates_courses = {c["date"]: c for c in courses}
    candidates = []
    for s in seances:
        if not s.get("km") or not s.get("minutes"):
            continue
        officielle = s["date"] in dates_courses
        if not officielle:
            continue
        candidates.append({
            "distance_m": s["km"] * 1000,
            "temps_s": s["minutes"] * 60,
            "source": dates_courses[s["date"]]["nom"],
            "date": s["date"],
            "estime": False,
        })
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
