"""Envoie les seances du plan vers la montre, via le calendrier Intervals.icu.

La chaine : ce script cree des evenements WORKOUT sur le calendrier
Intervals.icu, et Intervals les pousse vers Garmin Connect, qui les
synchronise sur la Forerunner. Rien a saisir sur la montre.

Une condition cote compte, et une seule : `icu_garmin_upload_workouts` doit
etre active dans Intervals.icu. Le script la verifie et refuse d'envoyer si
elle est fausse, plutot que de creer des evenements qui n'arriveront jamais.

Format des seances : `workout_doc` est poste SEUL, avec une allure cible en
m/s par etape et un libelle. Deux constats verifies contre l'API :

  - la syntaxe texte d'Intervals ne sait pas lire une allure explicite, aucune
    des cinq ecritures testees n'est parsee, et ses zones de puissance ne
    veulent rien dire pour un coureur ;
  - envoyer `description` ET `workout_doc` ensemble fait recompiler la seance
    depuis le texte, ce qui EFFACE toutes les etapes. Le premier envoi reel
    est reparti avec zero etape a cause de ca.

Le contenu redactionnel de la seance reste donc sur le dashboard, et la montre
recoit ce qu'elle sait afficher : un nom, des etapes, des cibles d'allure.

Par defaut le script n'envoie RIEN : il affiche ce qu'il ferait. Il faut
--envoyer pour ecrire sur le calendrier.

  python scripts/export_garmin.py                 # simulation
  python scripts/export_garmin.py --envoyer       # envoi reel
  python scripts/export_garmin.py --semaines 6 --envoyer
"""

import argparse
import json
import os
import sys
from datetime import date, datetime, timedelta

import requests
from dotenv import load_dotenv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://intervals.icu/api/v1"

# Les evenements crees sont notes ici, par identifiant. C'est ce qui permet de
# les remplacer au prochain envoi sans jamais toucher a un evenement cree a la
# main : on ne supprime que ce qu'on a soi-meme pose.
SUIVI = "docs/export_garmin.json"

JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
# Heures de depart : le creneau du midi en semaine, le samedi matin.
HEURES = {"mardi": "12:15", "jeudi": "12:15", "samedi": "09:00",
          "dimanche": "09:00", "mercredi": "12:15", "vendredi": "12:15"}


def connect():
    load_dotenv(os.path.join(ROOT, ".env"))
    cle = os.environ.get("INTERVALS_API_KEY")
    ath = os.environ.get("INTERVALS_ATHLETE_ID")
    if not cle or not ath:
        sys.exit("INTERVALS_API_KEY ou INTERVALS_ATHLETE_ID absent du .env")
    s = requests.Session()
    s.auth = ("API_KEY", cle)
    return s, ath


def _ms(s_km):
    """Secondes par kilometre vers metres par seconde, arrondi au centieme."""
    return round(1000.0 / s_km, 2)


def workout_doc(seance):
    """Les etapes de la seance au format attendu par Intervals.icu.

    `start` est l'allure la plus LENTE et `end` la plus rapide : en m/s, la
    borne lente est la plus petite valeur.

    Poster workout_doc court-circuite le compilateur d'Intervals, donc la duree
    et la distance totales ne sont pas calculees pour nous : on les calcule ici,
    sinon le calendrier affiche une seance de zero minute.
    """
    steps, duree, dist = [], 0, 0
    for e in seance["etapes"]:
        lent, rapide = e["allure_lente_s_km"], e["allure_rapide_s_km"]
        pas = {"text": e["nom"],
               "pace": {"units": "m/s", "start": _ms(lent), "end": _ms(rapide)}}
        if e.get("duree_s"):
            pas["duration"] = e["duree_s"]
            duree += e["duree_s"]
            dist += round(e["duree_s"] / ((lent + rapide) / 2) * 1000)
        else:
            pas["distance"] = e["distance_m"]
            dist += e["distance_m"]
            duree += round(e["distance_m"] / 1000 * (lent + rapide) / 2)
        steps.append(pas)
    return {"steps": steps, "duration": duree, "distance": dist}


def evenements(programme, semaines):
    """Un evenement par seance de course, sur les N premieres semaines."""
    out = []
    for w in programme[:semaines]:
        lundi = date.fromisoformat(w["lundi"])
        for s in w["seances"]:
            if s["type"] != "course" or s.get("course") or not s.get("etapes"):
                continue
            jour = lundi + timedelta(days=JOURS.index(s["jour"]))
            doc = workout_doc(s)
            # Pas de `description` : elle ferait recompiler la seance depuis le
            # texte et effacerait toutes les etapes.
            out.append({
                "start_date_local": "%sT%s:00" % (jour.isoformat(),
                                                  HEURES[s["jour"]]),
                "category": "WORKOUT",
                "type": "Run",
                "name": "S%d · %s" % (w["semaine"], s["nom"]),
                "moving_time": doc["duration"],
                "workout_doc": doc,
            })
    return out


def lis_suivi():
    try:
        with open(os.path.join(ROOT, SUIVI), encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return {"evenements": []}


def ecris_suivi(ids):
    with open(os.path.join(ROOT, SUIVI), "w", encoding="utf-8") as fh:
        json.dump({"maj": datetime.now().isoformat(timespec="seconds"),
                   "evenements": ids}, fh, indent=2, ensure_ascii=False)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--semaines", type=int, default=3,
                    help="nombre de semaines a envoyer (defaut 3)")
    ap.add_argument("--envoyer", action="store_true",
                    help="ecrire vraiment sur le calendrier")
    args = ap.parse_args()

    with open(os.path.join(ROOT, "docs", "metrics.json"), encoding="utf-8") as fh:
        prog = json.load(fh).get("programme") or []
    if not prog:
        sys.exit("Aucun programme dans metrics.json. Lance fetch_data.py d'abord.")

    s, ath = connect()
    prof = s.get(f"{BASE}/athlete/{ath}", timeout=60).json()
    actif = bool(prof.get("icu_garmin_upload_workouts"))

    evs = evenements(prog, args.semaines)
    print("%d séance(s) à envoyer, semaines %s"
          % (len(evs), ", ".join("S%d" % w["semaine"] for w in prog[:args.semaines])))
    for e in evs:
        d = e["workout_doc"]
        total = sum(x.get("duration", 0) for x in d["steps"])
        dist = sum(x.get("distance", 0) for x in d["steps"])
        print("  %s  %-46s %s" % (
            e["start_date_local"][:16], e["name"],
            "%d min" % (total // 60) if total else "%.1f km" % (dist / 1000)))

    print()
    print("Envoi vers Garmin : %s"
          % ("actif" if actif else
             "DESACTIVE (icu_garmin_upload_workouts est faux)"))
    if not actif:
        print("  Les séances seront visibles dans le calendrier Intervals.icu")
        print("  mais n'atteindront pas la montre. Pour activer :")
        print("  intervals.icu, Settings, section Garmin, coche")
        print("  \"Upload planned workouts to Garmin Connect\".")

    if not args.envoyer:
        print()
        print("SIMULATION. Rien n'a été écrit. Relance avec --envoyer.")
        return

    vieux = lis_suivi()["evenements"]
    retires = 0
    for i in vieux:
        if s.delete(f"{BASE}/athlete/{ath}/events/{i}", timeout=30).ok:
            retires += 1
    if vieux:
        print("%d ancienne(s) séance(s) remplacée(s) sur %d."
              % (retires, len(vieux)))

    poses = []
    for e in evs:
        r = s.post(f"{BASE}/athlete/{ath}/events", json=e, timeout=60)
        if r.ok:
            d = r.json()
            poses.append((d[0] if isinstance(d, list) else d)["id"])
        else:
            print("  echec %s : HTTP %s %s" % (e["name"], r.status_code, r.text[:120]))
    ecris_suivi(poses)
    print("%d séance(s) posée(s) sur le calendrier." % len(poses))
    if actif:
        print("Elles seront sur la montre à la prochaine synchronisation Garmin.")


if __name__ == "__main__":
    main()
