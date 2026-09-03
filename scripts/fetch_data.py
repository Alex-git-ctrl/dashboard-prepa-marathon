"""Extraction Intervals.icu -> docs/metrics.json (agrege, sans GPS).

Ce fichier est le seul publie. Il ne contient aucune coordonnee, aucun nom de
lieu, aucune trace : uniquement des agregats, des series temporelles et des
indicateurs calcules.
"""

import json
import os
import sys
from collections import defaultdict
from datetime import date, datetime

import requests
from dotenv import load_dotenv

import alerts

BASE = "https://intervals.icu/api/v1"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S1 = date(2026, 9, 7)      # lundi de la semaine 1 du plan
OLDEST = date(2026, 3, 1)

# Dynamique de course : ces streams viennent de la ceinture HRM-Pro Plus.
DYN = ["cadence", "stride_length", "ground_time", "vertical_oscillation",
       "vertical_ratio", "gct_balance"]


def connect():
    load_dotenv(os.path.join(ROOT, ".env"))
    key = os.getenv("INTERVALS_API_KEY", "").strip()
    ath = os.getenv("INTERVALS_ATHLETE_ID", "").strip()
    if not key or not ath:
        sys.exit("Manque INTERVALS_API_KEY / INTERVALS_ATHLETE_ID dans .env")
    s = requests.Session()
    s.auth = ("API_KEY", key)
    return s, (ath if ath.startswith("i") else "i" + ath)


def get(s, path, **params):
    r = s.get(f"{BASE}{path}", params=params, timeout=60)
    r.raise_for_status()
    return r.json()


def plan_week(d):
    n = (d - S1).days // 7 + 1
    return n if 1 <= n <= 27 else None


def mean(xs):
    xs = [x for x in xs if x is not None]
    return round(sum(xs) / len(xs), 1) if xs else None


def analyse_streams(s, activity_id):
    """Derive cardiaque et moyennes de dynamique de course pour une seance.

    La derive compare la FC de la 2e moitie a celle de la 1re, a effort
    theoriquement constant. Au-dessus de 5% la sortie etait trop rapide ou
    trop longue pour la forme du moment : c'est l'indicateur de progression
    le plus parlant sur une preparation marathon.
    """
    out = {"derive_pct": None, "dyn": {}}
    try:
        streams = get(s, f"/activity/{activity_id}/streams",
                      types=",".join(["time", "heartrate"] + DYN))
    except requests.RequestException:
        return out
    by_type = {x.get("type"): (x.get("data") or []) for x in streams}

    hr = [v for v in by_type.get("heartrate", []) if v]
    if len(hr) >= 600:                       # au moins 10 min de FC exploitable
        mid = len(hr) // 2
        h1 = sum(hr[:mid]) / mid
        h2 = sum(hr[mid:]) / (len(hr) - mid)
        if h1:
            out["derive_pct"] = round((h2 - h1) / h1 * 100, 1)

    for k in DYN:
        vals = [v for v in by_type.get(k, []) if v]
        if vals:
            out["dyn"][k] = round(sum(vals) / len(vals), 1)
    return out


def main():
    s, ath = connect()
    today = date.today()

    activities = get(s, f"/athlete/{ath}/activities",
                     oldest=OLDEST.isoformat(), newest=today.isoformat())
    runs = [a for a in activities if "run" in str(a.get("type", "")).lower()]
    runs.sort(key=lambda x: x.get("start_date_local", ""))

    semaines = defaultdict(lambda: {"km": 0.0, "seances": 0, "minutes": 0,
                                    "charge": 0, "deniv": 0})
    seances, derives, efficacite = [], [], []
    zfc = defaultdict(int)          # secondes par zone de frequence cardiaque
    zall = defaultdict(int)         # secondes par zone d'allure
    dyn_all = defaultdict(list)

    for a in runs:
        d = datetime.fromisoformat(a["start_date_local"][:19]).date()
        n = plan_week(d)
        km = round((a.get("distance") or 0) / 1000, 2)
        mins = round((a.get("moving_time") or 0) / 60)
        vit = a.get("average_speed")           # m/s
        fc = a.get("average_heartrate")

        if n:
            w = semaines[n]
            w["km"] += km
            w["seances"] += 1
            w["minutes"] += mins
            w["charge"] += a.get("icu_training_load") or 0
            w["deniv"] += a.get("total_elevation_gain") or 0

        for z in range(1, 8):
            zfc[f"z{z}"] += a.get(f"hr_z{z}_secs") or 0
            zall[f"z{z}"] += a.get(f"z{z}_secs") or 0

        st = analyse_streams(s, a["id"]) if km >= 8 else {"derive_pct": None, "dyn": {}}
        for k, v in st["dyn"].items():
            dyn_all[k].append(v)

        # Indice d'efficacite aerobie : vitesse rapportee a la FC.
        # Il monte quand on court plus vite pour le meme cout cardiaque.
        eff = round(vit / fc * 100, 2) if (vit and fc) else None

        rec = {
            "date": d.isoformat(), "semaine": n, "km": km, "minutes": mins,
            "type": a.get("type"),
            "allure_s_km": round(1000 / vit) if vit else None,
            "fc_moy": fc, "fc_max": a.get("max_heartrate"),
            "cadence": a.get("average_cadence"),
            "charge": a.get("icu_training_load"),
            "deniv": a.get("total_elevation_gain"),
            "efficacite": eff,
            "rpe": a.get("icu_rpe"),
            "notes": (a.get("description") or "").strip() or None,
            "derive_pct": st["derive_pct"],
            "dyn": st["dyn"] or None,
        }
        seances.append(rec)
        if st["derive_pct"] is not None:
            derives.append({"date": rec["date"], "km": km,
                            "derive_pct": st["derive_pct"]})
        if eff:
            efficacite.append({"date": rec["date"], "valeur": eff, "fc": fc,
                               "allure_s_km": rec["allure_s_km"]})

    # ---- Wellness ----
    wellness = get(s, f"/athlete/{ath}/wellness",
                   oldest=OLDEST.isoformat(), newest=today.isoformat())
    CHAMPS = {"hrv": "hrv", "restingHR": "fc_repos", "weight": "poids",
              "vo2max": "vo2max", "readiness": "readiness", "sleepScore": "sommeil_score",
              "avgSleepingHR": "fc_sommeil", "spO2": "spo2", "respiration": "respiration",
              "bodyFat": "masse_grasse", "ctl": "ctl", "atl": "atl",
              "rampRate": "ramp_rate", "steps": "pas",
              "soreness": "courbatures", "fatigue": "fatigue", "mood": "moral",
              "injury": "douleur_niveau", "comments": "commentaire"}
    serie = []
    for w in sorted(wellness, key=lambda x: x.get("id", "")):
        row = {"date": w.get("id")}
        for src, dst in CHAMPS.items():
            row[dst] = w.get(src)
        row["sommeil_h"] = round(w["sleepSecs"] / 3600, 1) if w.get("sleepSecs") else None
        if any(v is not None for k, v in row.items() if k != "date"):
            serie.append(row)

    def dernier(champ):
        for w in reversed(serie):
            if w.get(champ) is not None:
                return w[champ]
        return None

    def dispo(champ):
        return sum(1 for w in serie if w.get(champ) is not None)

    tot_fc = sum(zfc.values())
    tot_all = sum(zall.values())

    metrics = {
        "maj": datetime.now().isoformat(timespec="seconds"),
        "nb_activites": len(runs),
        "semaines": {str(k): {"km": round(v["km"], 1), "seances": v["seances"],
                              "minutes": v["minutes"], "charge": round(v["charge"]),
                              "deniv": round(v["deniv"])}
                     for k, v in sorted(semaines.items())},
        "seances": seances[-60:],
        "wellness": serie[-180:],
        "derives": derives[-20:],
        "efficacite": efficacite[-40:],
        "zones_fc_pct": ({k: round(v / tot_fc * 100, 1) for k, v in sorted(zfc.items())}
                         if tot_fc else {}),
        "zones_allure_pct": ({k: round(v / tot_all * 100, 1) for k, v in sorted(zall.items())}
                             if tot_all else {}),
        "dynamique": {k: mean(v) for k, v in dyn_all.items()},
        "actuel": {dst: dernier(dst) for dst in CHAMPS.values()},
        "couverture": {dst: dispo(dst) for dst in CHAMPS.values()},
        "jours_wellness": len(serie),
    }
    metrics["actuel"]["sommeil_h"] = dernier("sommeil_h")
    metrics["actuel"]["derive_pct"] = derives[-1]["derive_pct"] if derives else None
    metrics["actuel"]["efficacite"] = efficacite[-1]["valeur"] if efficacite else None
    metrics["actuel"]["cadence"] = mean([x["cadence"] for x in seances])

    # ---- Journal : une ligne par jour ou il s'est passe quelque chose ----
    par_date = {w["date"]: w for w in serie}
    journal = []
    for rec in seances:
        w = par_date.get(rec["date"], {})
        journal.append({
            "date": rec["date"], "semaine": rec["semaine"],
            "km": rec["km"], "minutes": rec["minutes"],
            "allure_s_km": rec["allure_s_km"], "fc_moy": rec["fc_moy"],
            "derive_pct": rec["derive_pct"],
            "rpe": rec["rpe"], "notes": rec["notes"],
            "courbatures": w.get("courbatures"), "fatigue": w.get("fatigue"),
            "moral": w.get("moral"), "sommeil_h": w.get("sommeil_h"),
            "douleur": w.get("commentaire") if w.get("douleur_niveau") else None,
        })
    # Jours sans course mais avec une note subjective : ils comptent aussi.
    dates_courues = {r["date"] for r in seances}
    for w in serie:
        if w["date"] in dates_courues:
            continue
        if any(w.get(k) is not None for k in
               ("courbatures", "fatigue", "moral", "douleur_niveau", "commentaire")):
            journal.append({
                "date": w["date"], "semaine": None, "km": None, "minutes": None,
                "allure_s_km": None, "fc_moy": None, "derive_pct": None,
                "rpe": None, "notes": None,
                "courbatures": w.get("courbatures"), "fatigue": w.get("fatigue"),
                "moral": w.get("moral"), "sommeil_h": w.get("sommeil_h"),
                "douleur": w.get("commentaire") if w.get("douleur_niveau") else None,
            })
    journal.sort(key=lambda j: j["date"])
    metrics["journal"] = journal[-40:]

    # ---- Alertes ----
    with open(os.path.join(ROOT, "docs", "plan.json"), encoding="utf-8") as fh:
        plan = json.load(fh)
    sem_courante = (today - S1).days // 7 + 1
    metrics["alertes"] = alerts.compute(metrics, plan, sem_courante)

    with open(os.path.join(ROOT, "docs", "metrics.json"), "w", encoding="utf-8") as fh:
        json.dump(metrics, fh, indent=2, ensure_ascii=False)

    print(f"docs/metrics.json : {len(runs)} course(s), {len(serie)} jour(s) de wellness, "
          f"{len(semaines)} semaine(s) du plan")
    dispo_ok = [k for k, v in metrics["couverture"].items() if v]
    absent = [k for k, v in metrics["couverture"].items() if not v]
    print(f"  wellness alimente : {', '.join(dispo_ok) or 'aucun'}")
    print(f"  wellness vide     : {', '.join(absent) or 'aucun'}")
    print(f"  journal : {len(journal)} entree(s) · alertes : "
          f"{len(metrics['alertes'])}")
    for a in metrics["alertes"]:
        print(f"    [{a['niveau']}] {a['titre']}")


if __name__ == "__main__":
    main()
