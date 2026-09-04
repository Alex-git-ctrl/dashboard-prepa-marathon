"""Indicateurs de vie quotidienne : pas, sommeil, fatigue.

Ce module ne regarde pas l'entrainement mais ce qui le rend possible.
Un plan tient ou casse sur le sommeil et la recuperation bien plus que sur
la qualite des seances.

L'indice de fatigue est *calcule*, pas mesure. Il compare la VFC et la FC de
repos du jour a leur reference glissante : c'est la deviation qui informe, pas
la valeur absolue, parce que 76 ms de VFC ne veut rien dire dans l'absolu et
tout dire par rapport a ta propre moyenne.
"""

from statistics import mean

# Ce qu'on suit au jour le jour, et comment l'agreger.
CHAMPS = [
    ("pas", "Pas", "pas", 0),
    ("sommeil_h", "Sommeil", "h", 1),
    ("sommeil_score", "Score de sommeil", "/100", 0),
    ("fatigue_indice", "Indice de fatigue", "/100", 0),
    ("fc_repos", "FC de repos", "bpm", 0),
    ("hrv", "Variabilité cardiaque", "ms", 0),
    ("poids", "Poids", "kg", 1),
    ("spo2", "SpO2", "%", 0),
    ("respiration", "Respiration", "/min", 1),
]

JOURS_REFERENCE = 28   # fenetre de la moyenne de reference
JOURS_MINIMUM = 14     # en dessous, on ne dit rien plutot que n'importe quoi


def _reference(serie, champ, i):
    """Moyenne du champ sur les jours precedant l'index i."""
    debut = max(0, i - JOURS_REFERENCE)
    vals = [serie[j][champ] for j in range(debut, i)
            if serie[j].get(champ) is not None]
    return mean(vals) if len(vals) >= JOURS_MINIMUM else None


def indice_fatigue(serie):
    """Ajoute fatigue_indice a chaque jour de la serie, quand c'est possible.

    50 = ta normale. Au-dessus, tu recuperes moins bien que d'habitude.
    Deux entrees seulement, les deux plus fiables au reveil :
      - la VFC, qui chute quand le systeme nerveux est sollicite,
      - la FC de repos, qui monte a la fatigue, au manque de sommeil
        ou au debut d'une infection.
    """
    for i, jour in enumerate(serie):
        points, poids = 0.0, 0.0

        ref_hrv = _reference(serie, "hrv", i)
        if ref_hrv and jour.get("hrv"):
            # -20 % de VFC vaut +30 points de fatigue.
            ecart = (ref_hrv - jour["hrv"]) / ref_hrv
            points += max(-30, min(30, ecart * 150))
            poids += 1

        ref_fc = _reference(serie, "fc_repos", i)
        if ref_fc and jour.get("fc_repos"):
            # +5 bpm vaut +25 points.
            points += max(-25, min(25, (jour["fc_repos"] - ref_fc) * 5))
            poids += 1

        jour["fatigue_indice"] = round(50 + points / poids) if poids else None
    return serie


def construit(wellness):
    """Serie quotidienne prete a agreger, plus l'etat du jour."""
    serie = []
    for w in wellness:
        serie.append({c[0]: w.get(c[0]) for c in CHAMPS if c[0] != "fatigue_indice"}
                     | {"date": w["date"]})
    indice_fatigue(serie)

    def dernier(champ):
        for j in reversed(serie):
            if j.get(champ) is not None:
                return j[champ], j["date"]
        return None, None

    actuel = {}
    for cle, _, _, _ in CHAMPS:
        val, dt = dernier(cle)
        actuel[cle] = val
        actuel[cle + "_date"] = dt

    return {
        "champs": [{"cle": c, "nom": n, "unite": u, "dec": d} for c, n, u, d in CHAMPS],
        "jours": serie,
        "actuel": actuel,
        "reference_jours": JOURS_REFERENCE,
        "minimum_jours": JOURS_MINIMUM,
    }
