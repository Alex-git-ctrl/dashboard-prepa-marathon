"""L'API personnelle Garmin : ce qu'Intervals.icu ne transmet pas.

UNE SOURCE PAR DONNEE. Intervals.icu reste la source de verite pour les
seances, la charge, la forme, le calendrier et le journal, et aussi pour la
duree et le score du sommeil, la VFC et la FC de repos. Ce module n'ajoute
QUE des champs qu'Intervals.icu ne recoit pas : la Body Battery, le stress de
la journee, les phases du sommeil, la respiration et la FC pendant le
sommeil, le statut de la VFC. Aucun champ n'a deux sources : rien ne peut se
contredire, et retirer ce module ne casse rien d'autre.

L'API (ouverte le 21/10/2026) est en lecture seule et a la demande : pas de
webhook, on la tire a chaque collecte, comme Intervals.icu. La cle
GARMIN_PERSONAL_API_KEY (.env en local, secret GitHub en CI) s'echange
contre un jeton de 24 h. Elle expire au plus tard au bout d'un an et se
recree a la main sur Garmin Connect, la page le signale quand elle est
refusee.

Fenetres : 28 jours par requete au plus pour le sommeil (au-dela, Garmin
repond 400 et un corps vide), on decoupe donc tout en tranches de 28 jours.
L'historique s'accumule dans docs/garmin.json : metrics.json est reconstruit
de zero a chaque collecte, et sans ce cache il faudrait tout redemander.

Honnetete : sans cle, ou si Garmin refuse ou ne repond pas, la collecte
continue sans ces champs, garde le cache, et l'etat le dit. Que des
agregats quotidiens : ni trace, ni position, ni horodatage a la seconde.
"""

import json
import os
from datetime import date, timedelta

import requests

BASE = "https://personal.connectapi.garmin.com"
JETON = "/personalapitoken-service/personal-api/personal-api-key/token"
TRANCHE = 28            # jours par requete, la limite du sommeil
RELIRE = 3              # jours recents redemandes : la nuit d'hier peut arriver tard
DELAI = 30

# Les champs que ce module ajoute a la serie sante, et leur sens. Le nom est
# celui de la page, le commentaire dit d'ou il vient chez Garmin.
CHAMPS = (
    "body_battery",        # dailysummaries bodyBattery.maxValue : le pic du jour
    "body_battery_min",    # bodyBattery.minValue
    "bb_recharge",         # bodyBattery.chargedValue
    "bb_depense",          # bodyBattery.drainedValue
    "stress",              # stress.avgLevel, sur 100
    "stress_eleve_min",    # stress.highStressDurationInMillis, en minutes
    "sommeil_profond",     # dailySleepSummaries deepSleepSeconds, en minutes
    "sommeil_paradoxal",   # remSleepSeconds
    "sommeil_leger",       # lightSleepSeconds
    "sommeil_eveil",       # awakeSleepSeconds
    "sommeil_duree",       # sleepTimeSeconds, eveil exclu. Ce total depasse
                           # parfois la somme des trois phases (25/10/2026 :
                           # 7 h 42 pour 5 h 42 classees) : la page montre
                           # l'ecart en "non classe" plutot que de le perdre.
    "respiration_nuit",    # averageRespirationValue, par minute
    "fc_nuit",             # avgHeartRate pendant le sommeil
    "statut_vfc",          # hrvSummaries status : BALANCED, UNBALANCED, LOW...
)


class Refusee(Exception):
    """La cle est refusee : expiree, revoquee, ou mal recopiee."""


def _cle():
    return (os.getenv("GARMIN_PERSONAL_API_KEY") or "").strip()


def _session(cle):
    r = requests.post(BASE + JETON, timeout=DELAI,
                      headers={"Accept": "*/*", "Authorization": "ApiKey " + cle})
    if r.status_code in (401, 403):
        raise Refusee(r.status_code)
    r.raise_for_status()
    s = requests.Session()
    s.headers.update({"Accept": "application/json",
                      "Authorization": "Bearer " + r.text.strip()})
    return s


def _get(s, chemin, params=None):
    r = s.get(BASE + chemin, params=params, timeout=DELAI)
    if r.status_code in (401, 403):
        raise Refusee(r.status_code)
    r.raise_for_status()
    return r.json() if r.content else None


def _tranches(debut, fin):
    d = debut
    while d <= fin:
        f = min(fin, d + timedelta(days=TRANCHE - 1))
        yield d, f
        d = f + timedelta(days=1)


def _min(ms):
    return round(ms / 60000) if ms is not None else None


def _quotidien(s, d, f, jours):
    rep = _get(s, "/usersummary-service/v2/dailysummaries",
               {"startDate": d.isoformat(), "endDate": f.isoformat()}) or {}
    for x in rep.get("data") or []:
        bb, st = x.get("bodyBattery") or {}, x.get("stress") or {}
        j = jours.setdefault(x["calendarDate"], {})
        j.update({k: v for k, v in {
            "body_battery": bb.get("maxValue"),
            "body_battery_min": bb.get("minValue"),
            "bb_recharge": bb.get("chargedValue"),
            "bb_depense": bb.get("drainedValue"),
            # Garmin marque -1 ou -2 un stress non mesure (montre retiree).
            "stress": st.get("avgLevel") if (st.get("avgLevel") or -1) >= 0 else None,
            "stress_eleve_min": _min(st.get("highStressDurationInMillis")),
        }.items() if v is not None})


def _sommeil(s, d, f, jours):
    rep = _get(s, "/sleep-service/sleep/dailySleepSummariesByDate",
               {"startDate": d.isoformat(), "endDate": f.isoformat()}) or []
    for x in rep:
        if not x.get("calendarDate") or not x.get("sleepTimeSeconds"):
            continue                    # nuit sans montre : rien plutot que zero
        j = jours.setdefault(x["calendarDate"], {})
        j.update({k: v for k, v in {
            "sommeil_profond": _min((x.get("deepSleepSeconds") or 0) * 1000),
            "sommeil_paradoxal": _min((x.get("remSleepSeconds") or 0) * 1000),
            "sommeil_leger": _min((x.get("lightSleepSeconds") or 0) * 1000),
            "sommeil_eveil": _min((x.get("awakeSleepSeconds") or 0) * 1000),
            "sommeil_duree": _min(x["sleepTimeSeconds"] * 1000),
            "respiration_nuit": x.get("averageRespirationValue"),
            "fc_nuit": x.get("avgHeartRate"),
        }.items() if v is not None})


def _vfc(s, d, f, jours):
    rep = _get(s, "/hrv-service/hrv/daily/%s/%s" % (d.isoformat(), f.isoformat())) or {}
    for x in rep.get("hrvSummaries") or []:
        if x.get("calendarDate") and x.get("status"):
            jours.setdefault(x["calendarDate"], {})["statut_vfc"] = x["status"]


def _lis_cache(chemin):
    try:
        with open(chemin, encoding="utf-8") as fh:
            return (json.load(fh) or {}).get("jours") or {}
    except (OSError, ValueError):
        return {}


def met_a_jour(root, depuis, aujourd_hui=None):
    """Complete le cache et renvoie l'etat et les jours.

    Renvoie {"etat", "message", "derniere_date", "nb_jours", "jours"} ; etat
    vaut "ok", "absente" (pas de cle), "refusee" ou "injoignable". Dans les
    deux derniers cas les jours sont ceux du cache, intacts.
    """
    aujourd_hui = aujourd_hui or date.today()
    chemin = os.path.join(root, "docs", "garmin.json")
    jours = _lis_cache(chemin)

    def etat(e, message):
        dates = sorted(jours)
        return {"etat": e, "message": message, "nb_jours": len(dates),
                "derniere_date": dates[-1] if dates else None, "jours": jours}

    cle = _cle()
    if not cle:
        return etat("absente", "Pas de clé GARMIN_PERSONAL_API_KEY : Body Battery, "
                    "stress et phases du sommeil ne sont pas collectés.")
    debut = depuis
    if jours:
        debut = max(depuis, date.fromisoformat(max(jours)) - timedelta(days=RELIRE))
    try:
        s = _session(cle)
        frais = {}
        for d, f in _tranches(debut, aujourd_hui):
            _quotidien(s, d, f, frais)
            _sommeil(s, d, f, frais)
            _vfc(s, d, f, frais)
    except Refusee:
        return etat("refusee", "Garmin refuse la clé : elle a expiré ou a été "
                    "révoquée. À recréer sur Garmin Connect, puis set_secrets.py.")
    except requests.RequestException as e:
        return etat("injoignable", "Garmin n'a pas répondu (%s) : le cache est "
                    "gardé tel quel." % type(e).__name__)

    # Un jour redemande remplace l'ancien : la nuit d'hier peut s'etre
    # completee depuis la derniere collecte.
    for k, v in frais.items():
        jours[k] = v
    jours = {k: jours[k] for k in sorted(jours)}
    with open(chemin, "w", encoding="utf-8") as fh:
        json.dump({"maj": aujourd_hui.isoformat(), "jours": jours}, fh,
                  ensure_ascii=False, indent=1)
    return etat("ok", "Collecte Garmin à jour.")


if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv
    sys.stdout.reconfigure(encoding="utf-8")
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    load_dotenv(os.path.join(ROOT, ".env"))
    r = met_a_jour(ROOT, date(2026, 3, 1))
    print(r["etat"], "|", r["message"], "|", r["nb_jours"], "jours, dernier",
          r["derniere_date"])
