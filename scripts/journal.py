"""Journal de seance : note le ressenti dans Intervals.icu.

Les donnees objectives viennent de la montre. Le ressenti, lui, n'existe que
si tu le notes : c'est pourtant le meilleur detecteur precoce de blessure,
bien avant que la montre ne voie quoi que ce soit.

Tout est ecrit dans Intervals.icu, jamais dans un fichier local : le pipeline
le relit ensuite comme n'importe quelle autre donnee, et tu peux aussi saisir
depuis l'appli Intervals.icu sur ton telephone.

Exemples
--------
    python scripts/journal.py --rpe 4
    python scripts/journal.py --rpe 7 --douleur "genou droit sur les 3 derniers km"
    python scripts/journal.py --fatigue 3 --courbatures 2 --note "jambes lourdes"
    python scripts/journal.py --date 2026-09-12 --rpe 5

Echelles Intervals.icu : 1 = tres bien, 4 = tres mauvais.
"""

import argparse
import os
import sys
from datetime import date

import requests
from dotenv import load_dotenv

BASE = "https://intervals.icu/api/v1"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def connect():
    load_dotenv(os.path.join(ROOT, ".env"))
    key = os.getenv("INTERVALS_API_KEY", "").strip()
    ath = os.getenv("INTERVALS_ATHLETE_ID", "").strip()
    if not key or not ath:
        sys.exit("Manque INTERVALS_API_KEY / INTERVALS_ATHLETE_ID dans .env")
    s = requests.Session()
    s.auth = ("API_KEY", key)
    return s, (ath if ath.startswith("i") else "i" + ath)


def main():
    p = argparse.ArgumentParser(
        description="Note le ressenti d'une seance dans Intervals.icu.")
    p.add_argument("--date", default=date.today().isoformat(),
                   help="jour concerne, format AAAA-MM-JJ (defaut : aujourd'hui)")
    p.add_argument("--rpe", type=int, choices=range(1, 11), metavar="1-10",
                   help="effort percu. L'endurance fondamentale doit tourner a 3-4")
    p.add_argument("--douleur", metavar="TEXTE",
                   help="localisation et moment, ex: \"genou droit, dernier tiers\"")
    p.add_argument("--courbatures", type=int, choices=range(1, 5), metavar="1-4")
    p.add_argument("--fatigue", type=int, choices=range(1, 5), metavar="1-4")
    p.add_argument("--moral", type=int, choices=range(1, 5), metavar="1-4")
    p.add_argument("--note", metavar="TEXTE", help="commentaire libre sur la seance")
    args = p.parse_args()

    if not any([args.rpe, args.douleur, args.courbatures, args.fatigue,
                args.moral, args.note]):
        p.error("rien a enregistrer. Ajoute au moins --rpe, --douleur ou --note.")

    s, ath = connect()
    fait = []

    # --- Ressenti du jour, sur le wellness ---
    corps = {}
    if args.courbatures:
        corps["soreness"] = args.courbatures
    if args.fatigue:
        corps["fatigue"] = args.fatigue
    if args.moral:
        corps["mood"] = args.moral
    if args.douleur:
        # injury sert de drapeau, le texte va dans les commentaires
        corps["injury"] = 3
        corps["comments"] = "DOULEUR : " + args.douleur
    elif args.note:
        corps["comments"] = args.note

    if corps:
        r = s.put(f"{BASE}/athlete/{ath}/wellness/{args.date}",
                  json=corps, timeout=30)
        if r.status_code >= 300:
            sys.exit(f"Echec sur le ressenti : HTTP {r.status_code} {r.text[:200]}")
        fait.append("ressenti du " + args.date)

    # --- RPE, sur la derniere seance du jour ---
    if args.rpe:
        acts = s.get(f"{BASE}/athlete/{ath}/activities",
                     params={"oldest": args.date, "newest": args.date}, timeout=30)
        acts.raise_for_status()
        jour = acts.json()
        if not jour:
            print(f"Aucune activite le {args.date} : le RPE n'a pas ete enregistre.")
            print("La montre a peut-etre encore a se synchroniser.")
        else:
            cible = sorted(jour, key=lambda a: a.get("start_date_local", ""))[-1]
            r = s.put(f"{BASE}/activity/{cible['id']}",
                      json={"icu_rpe": args.rpe}, timeout=30)
            if r.status_code >= 300:
                sys.exit(f"Echec sur le RPE : HTTP {r.status_code} {r.text[:200]}")
            fait.append(f"RPE {args.rpe} sur « {cible.get('name', 'seance')} »")

    print("Enregistre : " + ", ".join(fait))
    print("Le tableau de bord le reprendra a la prochaine mise a jour, "
          "7h ou 21h. Pour le voir tout de suite :")
    print("  python scripts/fetch_data.py && python scripts/build_site.py")


if __name__ == "__main__":
    main()
