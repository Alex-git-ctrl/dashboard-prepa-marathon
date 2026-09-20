"""Importe les seances du plan dans la bibliotheque de la montre, sans date.

La chaine : ce script cree des seances dans la bibliotheque Intervals.icu
(`POST .../workouts`, sans jour), Intervals les pousse vers Garmin Connect,
qui les synchronise sur la Forerunner comme des entrainements "type" :
demarrables a tout moment depuis le menu Entrainement > Mes entrainements de
la montre, pas rattaches a une date du calendrier.

Deux autres pistes ont ete essayees avant celle-ci, et rejetees :

  - un evenement calendrier par seance (`POST .../events`, avec une date) :
    ca marche, mais colle chaque seance a un jour fixe. Inutilisable pour
    Alex, qui change regulierement son planning de semaine.
  - la meme seance postee sur plusieurs jours de la semaine pour simuler de
    la souplesse : rejete avant meme d'etre envoye, ca remplit le calendrier
    de doublons a ignorer.

La bibliotheque sans date est la bonne reponse : postee une seule fois,
verifiee reçue sur la Forerunner 265 d'Alex le 20/09/2026 (elle y arrive
comme un entrainement "type" ordinaire, demarrable n'importe quel jour).

Format des seances : `workout_doc` est poste SEUL, avec une allure cible en
m/s par etape et un libelle. Deux constats verifies contre l'API :

  - la syntaxe texte d'Intervals ne sait pas lire une allure explicite, aucune
    des cinq ecritures testees n'est parsee, et ses zones de puissance ne
    veulent rien dire pour un coureur ;
  - envoyer `description` ET `workout_doc` ensemble fait recompiler la seance
    depuis le texte, ce qui EFFACE toutes les etapes. Le premier envoi reel
    (calendrier, avant ce changement) est reparti avec zero etape a cause
    de ca. La regle vaut aussi pour la bibliotheque, meme mecanisme.

Le contenu redactionnel de la seance (pourquoi, consignes) reste donc sur le
dashboard, et la montre recoit ce qu'elle sait afficher : un nom, des etapes,
des cibles d'allure. L'ordre et l'espacement conseille entre les seances
restent la responsabilite du dashboard (section "Le programme", qui affiche
la souplesse de chaque seance) : rien de tout ca ne peut se coder dans une
seance de bibliotheque sans date.

Les seances sont rangees dans un dossier dedie ("Plan marathon"), cree s'il
n'existe pas, pour ne jamais toucher aux dossiers qu'Alex gere lui-meme dans
Intervals.icu.

Seules les seances structurees (deux etapes ou plus) sont envoyees : une
seance a une seule etape n'est qu'"endurance pendant X minutes", ca n'a rien
a faire dans une bibliotheque de seances "type" a lancer sur la montre. Voir
`seances()`. Et comme le dossier est entierement remplace a chaque envoi
(les anciennes seances supprimees avant que les nouvelles soient postees),
rien ne s'y accumule d'un envoi a l'autre.

Une condition cote compte, et une seule : `icu_garmin_upload_workouts` doit
etre active dans Intervals.icu. Le script la verifie et signale si elle est
fausse, plutot que de laisser croire a un envoi qui n'arrivera jamais.

Par defaut le script n'envoie RIEN : il affiche ce qu'il ferait. Il faut
--envoyer pour ecrire dans la bibliotheque.

  python scripts/export_garmin.py                 # simulation
  python scripts/export_garmin.py --envoyer       # envoi reel
  python scripts/export_garmin.py --semaines 6 --envoyer
"""

import argparse
import json
import os
import sys
from datetime import datetime

import requests
from dotenv import load_dotenv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://intervals.icu/api/v1"

# Les seances de bibliotheque creees sont notees ici, par identifiant. C'est
# ce qui permet de les remplacer au prochain envoi sans jamais toucher a une
# seance creee a la main : on ne supprime que ce qu'on a soi-meme pose.
SUIVI = "docs/export_garmin.json"

# Dossier bibliotheque dedie a ce depot, pour ne jamais se meler aux dossiers
# qu'Alex gere lui-meme dans Intervals.icu.
DOSSIER = "Plan marathon"


def connect():
    load_dotenv(os.path.join(ROOT, ".env"))
    cle = os.environ.get("INTERVALS_API_KEY")
    ath = os.environ.get("INTERVALS_ATHLETE_ID")
    if not cle or not ath:
        sys.exit("INTERVALS_API_KEY ou INTERVALS_ATHLETE_ID absent du .env")
    s = requests.Session()
    s.auth = ("API_KEY", cle)
    return s, ath


def dossier_id(s, ath):
    """L'id du dossier bibliotheque dedie, cree s'il n'existe pas encore."""
    r = s.get(f"{BASE}/athlete/{ath}/folders", timeout=30)
    r.raise_for_status()
    for f in r.json():
        if f.get("name") == DOSSIER:
            return f["id"]
    r = s.post(f"{BASE}/athlete/{ath}/folders", timeout=30,
               json={"type": "FOLDER", "name": DOSSIER})
    r.raise_for_status()
    return r.json()["id"]


def _ms(s_km):
    """Secondes par kilometre vers metres par seconde, arrondi au centieme."""
    return round(1000.0 / s_km, 2)


def workout_doc(seance):
    """Les etapes de la seance au format attendu par Intervals.icu.

    `start` est l'allure la plus LENTE et `end` la plus rapide : en m/s, la
    borne lente est la plus petite valeur.

    Poster workout_doc court-circuite le compilateur d'Intervals, donc la duree
    et la distance totales ne sont pas calculees pour nous : on les calcule ici,
    sinon la bibliotheque affiche une seance de zero minute.
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


def seances(programme, semaines, folder_id):
    """Les seances de course des N prochaines semaines, pretes pour la
    bibliotheque : pas de jour, pas de date, juste un nom et des etapes.

    Seules les seances structurees (deux etapes ou plus : echauffement puis
    effort, ou endurance puis lignes droites, ou sortie longue avec finale)
    sont retenues. Une seance a une seule etape n'est qu'"endurance pendant
    X minutes" : ca ne vaut pas la peine d'occuper de la place dans la
    bibliotheque de la montre, ca se court sans consigne de structure.
    """
    out = []
    for w in programme[:semaines]:
        for s in w["seances"]:
            if s["type"] != "course" or s.get("course") or not s.get("etapes"):
                continue
            if len(s["etapes"]) < 2:
                continue
            doc = workout_doc(s)
            # Pas de `description` : elle ferait recompiler la seance depuis le
            # texte et effacerait toutes les etapes.
            out.append({
                "folder_id": folder_id,
                "type": "Run",
                "name": "S%d · %s" % (w["semaine"], s["nom"]),
                "moving_time": doc["duration"],
                "workout_doc": doc,
            })
    return out


def lis_suivi():
    try:
        with open(os.path.join(ROOT, SUIVI), encoding="utf-8") as fh:
            d = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return []
    # "evenements" est l'ancienne cle (mecanisme calendrier, abandonne) : un
    # fichier de suivi laisse par l'ancienne version du script ne doit pas
    # faire planter celle-ci, juste ne rien avoir a remplacer.
    return d.get("seances", [])


def ecris_suivi(ids):
    with open(os.path.join(ROOT, SUIVI), "w", encoding="utf-8") as fh:
        json.dump({"maj": datetime.now().isoformat(timespec="seconds"),
                   "seances": ids}, fh, indent=2, ensure_ascii=False)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--semaines", type=int, default=3,
                    help="nombre de semaines a envoyer (defaut 3)")
    ap.add_argument("--envoyer", action="store_true",
                    help="ecrire vraiment dans la bibliotheque")
    args = ap.parse_args()

    with open(os.path.join(ROOT, "docs", "metrics.json"), encoding="utf-8") as fh:
        prog = json.load(fh).get("programme") or []
    if not prog:
        sys.exit("Aucun programme dans metrics.json. Lance fetch_data.py d'abord.")

    s, ath = connect()
    prof = s.get(f"{BASE}/athlete/{ath}", timeout=60).json()
    actif = bool(prof.get("icu_garmin_upload_workouts"))
    dossier = dossier_id(s, ath)

    sems = seances(prog, args.semaines, dossier)
    print("%d séance(s) à envoyer, semaines %s"
          % (len(sems), ", ".join("S%d" % w["semaine"] for w in prog[:args.semaines])))
    for e in sems:
        d = e["workout_doc"]
        total = sum(x.get("duration", 0) for x in d["steps"])
        dist = sum(x.get("distance", 0) for x in d["steps"])
        print("  %-50s %s" % (
            e["name"], "%d min" % (total // 60) if total else "%.1f km" % (dist / 1000)))

    print()
    print("Envoi vers Garmin : %s"
          % ("actif" if actif else
             "DESACTIVE (icu_garmin_upload_workouts est faux)"))
    if not actif:
        print("  Les séances seront visibles dans la bibliothèque Intervals.icu")
        print("  mais n'atteindront pas la montre. Pour activer :")
        print("  intervals.icu, Settings, section Garmin, coche")
        print("  \"Upload planned workouts to Garmin Connect\".")

    if not args.envoyer:
        print()
        print("SIMULATION. Rien n'a été écrit. Relance avec --envoyer.")
        return

    vieux = lis_suivi()
    retires = 0
    for i in vieux:
        if s.delete(f"{BASE}/athlete/{ath}/workouts/{i}", timeout=30).ok:
            retires += 1
    if vieux:
        print("%d ancienne(s) séance(s) remplacée(s) sur %d."
              % (retires, len(vieux)))

    poses = []
    for e in sems:
        r = s.post(f"{BASE}/athlete/{ath}/workouts", json=e, timeout=60)
        if r.ok:
            poses.append(r.json()["id"])
        else:
            print("  echec %s : HTTP %s %s" % (e["name"], r.status_code, r.text[:120]))
    ecris_suivi(poses)
    print("%d séance(s) posée(s) dans la bibliothèque." % len(poses))
    if actif:
        print("Elles seront sur la montre à la prochaine synchronisation Garmin.")


if __name__ == "__main__":
    main()
