"""Detail d'une seance : splits au kilometre, derive, dynamique de course.

Une seance resumee a trois chiffres ne se relit pas. Ce qui se relit, c'est le
decoupage : quel kilometre a coute cher, a quel moment la FC est partie, si la
deuxieme moitie a tenu la premiere. Tout se deduit des streams, qui sont deja
telecharges pour calculer la derive cardiaque.
"""

# Streams demandes a Intervals.icu pour une course. Les noms viennent du champ
# stream_types d'une activite reelle, pas d'une supposition : un seul nom
# inconnu fait repondre 422 a la requete entiere, et on perd tout le detail.
DYN = ["cadence", "step_length", "stance_time", "vertical_oscillation",
       "vertical_ratio"]
# velocity_smooth donne l'allure instantanee, watts la puissance de course :
# le Forerunner 265 la produit avec la ceinture HRM-Pro Plus.
TYPES = ["time", "heartrate", "distance", "altitude", "velocity_smooth",
         "watts"] + DYN

POINTS = 150       # points gardes par courbe apres sous-echantillonnage
V_MINI = 0.6       # m/s : au-dessous on est a l'arret, l'allure ne veut rien dire

MIN_ECHANTILLONS = 60      # moins d'une minute de trace : rien a decouper
MIN_RESTE_M = 300          # dernier troncon garde s'il depasse 300 m
MAX_SPLITS = 60            # borne la taille de metrics.json


def _moy(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def splits(temps, distance, fc, alt, pas=1000.0):
    """Un point par kilometre : temps, allure, FC moyenne, denivele positif.

    L'allure est normalisee sur la distance reellement parcourue dans le
    troncon et non sur 1000 m pile : un echantillon peut franchir la borne
    avec quelques metres d'avance, et sur une sortie longue ces metres
    s'accumulent en une erreur visible.
    """
    n = min(len(temps or []), len(distance or []))
    if n < MIN_ECHANTILLONS:
        return []

    fc = fc or []
    alt = alt or []

    def troncon(i0, i1, numero, partiel):
        d0, d1 = distance[i0], distance[i1]
        if d0 is None or d1 is None:
            return None
        dd, dt = d1 - d0, temps[i1] - temps[i0]
        if dd <= 0 or dt <= 0:
            return None
        seg_fc = [x for x in fc[i0:i1] if x]
        seg_alt = [x for x in alt[i0:i1] if x is not None]
        montee = sum(max(0.0, seg_alt[k + 1] - seg_alt[k])
                     for k in range(len(seg_alt) - 1)) if len(seg_alt) > 1 else None
        return {
            "km": numero,
            "distance_m": round(dd),
            "temps_s": round(dt),
            "allure_s_km": round(dt / dd * 1000),
            "fc": round(sum(seg_fc) / len(seg_fc)) if seg_fc else None,
            "deniv": round(montee) if montee is not None else None,
            "partiel": partiel,
        }

    out, i0, borne = [], 0, pas
    for i in range(n):
        d = distance[i]
        if d is None:
            continue
        # Le `i > i0` coupe la boucle apres la premiere fermeture : un
        # echantillon qui sauterait plusieurs bornes ne peut pas tourner en rond.
        while d >= borne and i > i0:
            t = troncon(i0, i, len(out) + 1, False)
            if t:
                out.append(t)
            i0, borne = i, borne + pas
            if len(out) >= MAX_SPLITS:
                return out

    if distance[n - 1] is not None and distance[i0] is not None \
            and distance[n - 1] - distance[i0] >= MIN_RESTE_M:
        t = troncon(i0, n - 1, len(out) + 1, True)
        if t:
            out.append(t)
    return out


def analyse(par_type):
    """Tout ce qu'on sait tirer des streams d'une seance."""
    out = {"derive_pct": None, "dyn": {}, "splits": [], "courbes": None,
           "fc_max_reelle": None, "seconde_moitie_s_km": None,
           "premiere_moitie_s_km": None, "puissance_moy": None}

    temps = par_type.get("time") or []
    hr = par_type.get("heartrate") or []
    dist = par_type.get("distance") or []
    alt = par_type.get("altitude") or []

    # Derive cardiaque : FC de la 2e moitie contre la 1re, a effort cense etre
    # constant. Au-dessus de 5 %, la sortie etait trop rapide ou trop longue
    # pour la forme du moment.
    utiles = [v for v in hr if v]
    if len(utiles) >= 600:                   # au moins 10 min de FC exploitable
        mid = len(utiles) // 2
        h1 = sum(utiles[:mid]) / mid
        h2 = sum(utiles[mid:]) / (len(utiles) - mid)
        if h1:
            out["derive_pct"] = round((h2 - h1) / h1 * 100, 1)
    if utiles:
        out["fc_max_reelle"] = max(utiles)

    for k in DYN:
        m = _moy(par_type.get(k) or [])
        if m is not None:
            out["dyn"][k] = round(m, 1)

    out["splits"] = splits(temps, dist, hr, alt)
    out["courbes"] = courbes(par_type)
    w = [v for v in (par_type.get("watts") or []) if v]
    if w:
        out["puissance_moy"] = round(sum(w) / len(w))

    # Negative split : la moitie de la distance, pas la moitie du temps. C'est
    # la question que se pose un coureur qui prepare un marathon.
    sp = out["splits"]
    if len(sp) >= 4:
        entiers = [x for x in sp if not x["partiel"]]
        if len(entiers) >= 4:
            mid = len(entiers) // 2
            out["premiere_moitie_s_km"] = round(
                sum(x["allure_s_km"] for x in entiers[:mid]) / mid)
            reste = entiers[mid:]
            out["seconde_moitie_s_km"] = round(
                sum(x["allure_s_km"] for x in reste) / len(reste))
    return out


def courbes(par_type, n=POINTS):
    """Series sous-echantillonnees pour les graphiques de seance.

    Une course d'une heure fait 3600 points par canal. On en garde 150, par
    MOYENNE et non par decimation : prendre un point sur vingt-quatre raterait
    les pics de FC et de puissance, qui sont precisement ce qu'on vient lire.
    """
    temps = par_type.get("time") or []
    if len(temps) < 20:
        return None
    N = len(temps)
    n = min(n, N)
    bornes = [round(i * N / n) for i in range(n + 1)]

    def canal(cle, transfo=None):
        src = par_type.get(cle) or []
        if not any(v for v in src):
            return None
        out = []
        for i in range(n):
            seg = [v for v in src[bornes[i]:bornes[i + 1]] if v is not None]
            if not seg:
                out.append(None)
                continue
            m = sum(seg) / len(seg)
            out.append(transfo(m) if transfo else round(m))
        return out if any(v is not None for v in out) else None

    # L'allure vient de la vitesse : a l'arret elle tendrait vers l'infini,
    # donc on la laisse vide plutot que de tracer un pic absurde.
    allure = canal("velocity_smooth",
                   lambda v: round(1000 / v) if v >= V_MINI else None)

    out = {
        "t": [round(temps[bornes[i]]) for i in range(n)],
        "allure": allure,
        "fc": canal("heartrate"),
        "puissance": canal("watts"),
        "altitude": canal("altitude"),
    }
    return out if any(out[k] for k in ("allure", "fc", "puissance")) else None
