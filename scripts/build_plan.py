"""Genere le plan d'entrainement 27 semaines en JSON.

Contraintes reelles d'Alex :
  - 3 seances de course par semaine, 2 seances de muscu
  - creneaux semaine : pause dejeuner, 40 a 45 min maximum
  - sortie longue le samedi
  - depart : 12 km/sem, plus longue sortie 6 km, 10 km de reference en 48 min

Courses : 10 km le samedi 26/09/2026 (S3), semi le 25/10/2026 (S7),
Zurich Marato de Barcelona le 14/03/2027 (S27).
"""

import json
import os
import sys
from datetime import date, timedelta

# La console Windows est en cp1252 : sans ca, le recapitulatif imprime en fin
# de script plante sur la fleche et le point median, apres avoir pourtant
# ecrit plan.json. L'erreur donnait l'impression que la generation avait echoue.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

S1 = date(2026, 9, 7)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

COURSES = [
    {"cle": "dix", "nom": "10 km", "lieu": "course locale",
     "date": "2026-09-26", "jour": "samedi", "semaine": 3, "distance_km": 10,
     "cible": "46 à 48 min", "allure": "4:36 à 4:48 /km",
     "role": "Première calibration réelle, un samedi matin. Negative split : c'est un test, pas un record."},
    {"cle": "semi", "nom": "Semi-marathon", "lieu": "Paris",
     "date": "2026-10-25", "jour": "dimanche", "semaine": 7, "distance_km": 21.0975,
     "cible": "1h45 à 1h52", "allure": "5:00 à 5:19 /km",
     "role": "Jalon de décision : c'est lui qui fixe l'allure marathon."},
    {"cle": "marathon", "nom": "Marathon de Barcelone", "lieu": "Barcelone",
     "date": "2027-03-14", "jour": "dimanche", "semaine": 27, "distance_km": 42.195,
     "cible": "sub-4h00", "allure": "5:41 /km",
     "role": "Zurich Marató de Barcelona, départ 8h30 Plaça de Catalunya. "
             "Parcours plat, parmi les plus rapides au monde."},
]

# (semaine, km sortie longue, min seance 1, min seance 2, type, consigne)
# Les seances de semaine sont en minutes : le creneau du midi est la contrainte,
# pas la distance. En EF a 6:05/km de moyenne, 40 min font environ 6,5 km.
WEEKS = [
    (1,  8,   35, 35, "base",      "Passage à 3 séances. Tout en endurance fondamentale."),
    (2,  10,  40, 40, "base",      "Première sortie à 10 km. Aucune accélération."),
    (3,  10,  30, 30, "COURSE",    "10 KM samedi 26/09. La course tient lieu de sortie longue."),
    (4,  12,  40, 40, "base",      "Reprise après la course. Zones recalibrées sur le chrono."),
    (5,  15,  45, 45, "specifique","Séance 2 : 3 × 6 min à allure semi, 2 min de trot entre."),
    (6,  18,  45, 40, "specifique","Plus longue sortie avant le semi, dont 5 km a allure semi."),
    (7,  21.1, 30, 25, "COURSE",   "SEMI-MARATHON dimanche 25/10."),
    (8,  10,  30, 35, "recup",     "Récupération. Rien au-dessus de l'endurance fondamentale."),
    (9,  14,  40, 40, "base",      "Reprise du volume avec les nouvelles zones."),
    (10, 16,  45, 45, "base",      ""),
    (11, 18,  45, 45, "base",      "Première sortie longue à 18 km du bloc marathon."),
    (12, 14,  35, 35, "decharge",  ""),
    (13, 20,  45, 45, "specifique","Séance 2 : 2 × 15 min à allure marathon."),
    (14, 22,  45, 45, "specifique","Derniers 5 km de la sortie longue à allure marathon."),
    (15, 24,  45, 45, "specifique","Cap des 24 km. Tester le ravitaillement en course."),
    (16, 16,  35, 40, "decharge",  ""),
    (17, 25,  45, 45, "specifique","Séance 2 : 3 × 10 min au seuil."),
    (18, 27,  45, 45, "specifique","Derniers 8 km à allure marathon."),
    (19, 29,  45, 45, "specifique","Sortie la plus longue avant le test 30K."),
    (20, 18,  35, 40, "decharge",  ""),
    (21, 26,  45, 45, "specifique","Répétition générale : chaussures et ravitaillement de course."),
    (22, 30,  45, 45, "pic",       "Cap des 30 km. Pic de volume de la préparation."),
    (23, 30,  45, 40, "TEST",      "TEST 30K à allure marathon. L'indicateur clé avant Barcelone."),
    (24, 16,  35, 35, "decharge",  "Assimilation du test."),
    (25, 22,  40, 40, "affutage",  "Début de l'affûtage : le volume baisse, l'intensité reste."),
    (26, 14,  35, 30, "affutage",  "Séance 2 : 4 × 3 min à allure marathon."),
    (27, 42.195, 25, 20, "COURSE", "MARATHON DE BARCELONE dimanche 14/03, départ 8h30."),
]

BLOCS = [
    (1, 7,   "Bloc 1", "Base aérobie, 10 km et semi"),
    (8, 12,  "Bloc 2", "Récupération et fondation marathon"),
    (13, 20, "Bloc 3", "Construction spécifique"),
    (21, 24, "Bloc 4", "Pic de volume et test 30K"),
    (25, 27, "Bloc 5", "Affûtage"),
]

EF_PACE = 6.1  # min/km moyen en endurance fondamentale


def bloc_of(n):
    for a, b, nom, desc in BLOCS:
        if a <= n <= b:
            return nom, desc
    return "?", ""


def main():
    par_semaine = {c["semaine"]: c for c in COURSES}
    weeks = []
    for n, longue, m1, m2, typ, note in WEEKS:
        lundi = S1 + timedelta(weeks=n - 1)
        km_sem = round((m1 + m2) / EF_PACE, 1)
        course = par_semaine.get(n)
        # Sur une semaine de course, l'epreuve tient lieu de sortie longue :
        # la distance est deja comptee dans sortie_longue_km.
        total = round(km_sem + longue, 1)
        nom, desc = bloc_of(n)
        weeks.append({
            "semaine": n,
            "lundi": lundi.isoformat(),
            "dimanche": (lundi + timedelta(days=6)).isoformat(),
            "bloc": nom, "bloc_desc": desc, "type": typ,
            "sortie_longue_km": longue,
            "seance1_min": m1, "seance2_min": m2,
            "volume_km": total,
            "course": course["cle"] if course else None,
            "note": note,
        })

    plan = {
        "genere_le": date.today().isoformat(),
        "athlete": "Alex Gourdou",
        "depart": {"volume_km": 12, "sortie_longue_km": 6, "seances": 2,
                   "poids_kg": 82, "ref_10k_min": 48},
        # L'hypothese qui convertit les minutes en kilometres. Elle est publiee
        # parce que la page affiche la distance estimee de chaque seance : sans
        # elle, le gabarit reinventerait sa propre constante et les jours de la
        # semaine ne totaliseraient plus le volume annonce.
        "ef_pace_min_km": EF_PACE,
        "courses": COURSES,
        "blocs": [{"debut": a, "fin": b, "nom": n, "desc": d} for a, b, n, d in BLOCS],
        "semaines": weeks,
        "pic_volume_km": max(w["volume_km"] for w in weeks if w["semaine"] != 27),
        "pic_sortie_longue_km": max(w["sortie_longue_km"] for w in weeks
                                    if w["semaine"] != 27),
    }

    with open(os.path.join(ROOT, "docs", "plan.json"), "w", encoding="utf-8") as fh:
        json.dump(plan, fh, indent=2, ensure_ascii=False)

    print(f"docs/plan.json : {len(weeks)} semaines, {len(COURSES)} courses")
    print(f"Pic volume {plan['pic_volume_km']} km/sem · "
          f"sortie longue max {plan['pic_sortie_longue_km']} km\n")
    for w in weeks:
        flag = f"  <<< {par_semaine[w['semaine']]['nom']}" if w["semaine"] in par_semaine else ""
        print("S%-3d %s→%s  %-7s  longue %5s km  %2d'+%2d'  total %5s km%s" % (
            w["semaine"], w["lundi"][5:], w["dimanche"][5:], w["bloc"],
            w["sortie_longue_km"], w["seance1_min"], w["seance2_min"],
            w["volume_km"], flag))


if __name__ == "__main__":
    main()
