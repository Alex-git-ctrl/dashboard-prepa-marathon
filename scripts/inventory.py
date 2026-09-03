"""Etape 0 : inventaire des champs reellement disponibles via l'API Intervals.icu.

Ne calcule rien, ne publie rien. Se connecte, tire un echantillon, et liste
exactement quelles donnees Garmin arrivent jusqu'a nous. C'est ce qui determine
ce que le dashboard pourra afficher.

Usage : python scripts/inventory.py
"""

import json
import os
import sys
from datetime import date, timedelta

import requests
from dotenv import load_dotenv

BASE = "https://intervals.icu/api/v1"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")

# Streams qu'on espere trouver. Le FR265 + HRM-Pro Plus devrait fournir la
# dynamique de course ; on verifie plutot que de supposer.
WANTED_STREAMS = [
    "time", "distance", "heartrate", "velocity_smooth", "pace",
    "cadence", "watts", "altitude", "temp", "moving",
    "respiration", "stride_length", "ground_time", "vertical_oscillation",
    "vertical_ratio", "gct_balance",
]


def load_credentials():
    load_dotenv(os.path.join(ROOT, ".env"))
    key = os.getenv("INTERVALS_API_KEY", "").strip()
    athlete = os.getenv("INTERVALS_ATHLETE_ID", "").strip()
    if not key or not athlete:
        sys.exit(
            "Manque INTERVALS_API_KEY ou INTERVALS_ATHLETE_ID.\n"
            "Copie .env.example en .env et remplis les deux valeurs."
        )
    if not athlete.startswith("i"):
        athlete = "i" + athlete
    return key, athlete


def get(session, path, **params):
    """Appelle l'API et renvoie (ok, payload_ou_message)."""
    try:
        r = session.get(f"{BASE}{path}", params=params, timeout=30)
    except requests.RequestException as exc:
        return False, f"erreur reseau: {exc}"
    if r.status_code != 200:
        return False, f"HTTP {r.status_code}: {r.text[:200]}"
    try:
        return True, r.json()
    except ValueError:
        return False, "reponse non-JSON"


def describe(value):
    """Type lisible d'une valeur, pour l'inventaire."""
    if value is None:
        return "null (vide)"
    if isinstance(value, bool):
        return f"bool = {value}"
    if isinstance(value, (int, float)):
        return f"nombre = {value}"
    if isinstance(value, str):
        return f"texte = {value[:40]!r}"
    if isinstance(value, list):
        return f"liste de {len(value)}"
    if isinstance(value, dict):
        return f"objet ({len(value)} cles)"
    return type(value).__name__


def section(title):
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


def main():
    key, athlete = load_credentials()
    session = requests.Session()
    session.auth = ("API_KEY", key)  # Basic Auth : login litteral "API_KEY"

    os.makedirs(RAW, exist_ok=True)
    today = date.today()

    # --- 1. Le compte repond-il ---
    section("1. CONNEXION")
    ok, profile = get(session, f"/athlete/{athlete}/profile")
    if not ok:
        ok, profile = get(session, f"/athlete/{athlete}")
    if not ok:
        sys.exit(f"Connexion impossible : {profile}\nVerifie la cle API et l'athlete ID.")
    name = profile.get("athlete", profile).get("name", "?") if isinstance(profile, dict) else "?"
    print(f"OK, connecte en tant que : {name}  ({athlete})")

    # --- 2. Quelles activites remontent ---
    section("2. ACTIVITES DISPONIBLES")
    ok, activities = get(
        session, f"/athlete/{athlete}/activities",
        oldest=(today - timedelta(days=365)).isoformat(),
        newest=today.isoformat(),
    )
    if not ok:
        print(f"Echec : {activities}")
        activities = []
    print(f"{len(activities)} activite(s) sur les 12 derniers mois.")
    runs = [a for a in activities if "run" in str(a.get("type", "")).lower()]
    print(f"dont {len(runs)} course(s) a pied.")
    if activities:
        oldest = min(a.get("start_date_local", "") for a in activities)
        print(f"Plus ancienne : {oldest[:10]}")
        with open(os.path.join(RAW, "activities.json"), "w", encoding="utf-8") as fh:
            json.dump(activities, fh, indent=2, ensure_ascii=False)
        print(f"-> sauvegarde dans data/raw/activities.json")

    # --- 3. Champs presents sur une activite ---
    sample = runs[0] if runs else (activities[0] if activities else None)
    if sample:
        section(f"3. CHAMPS D'UNE ACTIVITE  ({sample.get('name','?')})")
        filled = {k: v for k, v in sample.items() if v not in (None, "", [], {})}
        empty = sorted(k for k in sample if k not in filled)
        print(f"{len(filled)} champs remplis, {len(empty)} vides.\n")
        for k in sorted(filled):
            print(f"  {k:32s} {describe(filled[k])}")
        print(f"\nChamps vides ({len(empty)}) : {', '.join(empty)}")

        # --- 4. Streams seconde par seconde ---
        section("4. STREAMS (donnees seconde par seconde)")
        print("Indispensables pour la derive cardiaque et la distribution d'allure.\n")
        act_id = sample.get("id")
        ok, streams = get(session, f"/activity/{act_id}/streams",
                          types=",".join(WANTED_STREAMS))
        if not ok:
            print(f"Echec : {streams}")
        else:
            found = {s.get("type"): s for s in streams} if isinstance(streams, list) else {}
            for want in WANTED_STREAMS:
                if want in found:
                    n = len(found[want].get("data") or [])
                    print(f"  [OK]      {want:24s} {n} points")
                else:
                    print(f"  [ABSENT]  {want}")
            extra = set(found) - set(WANTED_STREAMS)
            if extra:
                print(f"\n  Bonus non demandes : {', '.join(sorted(extra))}")
            with open(os.path.join(RAW, "streams_sample.json"), "w", encoding="utf-8") as fh:
                json.dump(streams, fh, indent=2)
    else:
        print("\nAucune activite : impossible d'inventorier les champs de séance.")

    # --- 5. Wellness : la partie Garmin proprietaire ---
    section("5. WELLNESS (HRV, sommeil, Body Battery, Training Readiness)")
    ok, wellness = get(
        session, f"/athlete/{athlete}/wellness",
        oldest=(today - timedelta(days=30)).isoformat(),
        newest=today.isoformat(),
    )
    if not ok:
        print(f"Echec : {wellness}")
    elif not wellness:
        print("Aucune donnee wellness. Verifie dans Intervals.icu :")
        print("  Settings > Integrations > Garmin Connect > Scopes")
        print("  -> cocher Wellness et Sleep, puis attendre une synchro de la montre.")
    else:
        print(f"{len(wellness)} jour(s) de donnees.\n")
        # Un champ peut etre vide un jour et rempli un autre : on balaie tout.
        seen = {}
        for day in wellness:
            for k, v in day.items():
                if v not in (None, "", [], {}):
                    seen.setdefault(k, v)
        print(f"Champs jamais vides sur la periode ({len(seen)}) :\n")
        for k in sorted(seen):
            print(f"  {k:32s} {describe(seen[k])}")
        all_keys = {k for day in wellness for k in day}
        always_empty = sorted(all_keys - set(seen))
        if always_empty:
            print(f"\nToujours vides ({len(always_empty)}) : {', '.join(always_empty)}")
        with open(os.path.join(RAW, "wellness.json"), "w", encoding="utf-8") as fh:
            json.dump(wellness, fh, indent=2, ensure_ascii=False)

    section("TERMINE")
    print("Donnees brutes dans data/raw/ (exclu de git, rien ne partira sur GitHub).")


if __name__ == "__main__":
    main()
