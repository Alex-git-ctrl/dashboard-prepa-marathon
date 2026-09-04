"""Regles d'alerte sur la preparation marathon.

Chaque regle repond a une question simple : est-ce que quelque chose est en
train de deraper ? Le but n'est pas de signaler du bruit, mais de reperer
les trois causes classiques d'echec d'une preparation :

  1. la charge monte trop vite (blessure),
  2. l'endurance ne progresse pas (derive cardiaque qui stagne ou remonte),
  3. la recuperation decroche (VFC et FC de repos qui se degradent).

Toutes les regles renvoient None tant qu'il n'y a pas assez de donnees.
Mieux vaut ne rien dire que dire n'importe quoi sur trois mesures.
"""

from statistics import mean

NIVEAUX = {"critique": 3, "attention": 2, "info": 1}


def _alerte(niveau, titre, detail, quoi_faire):
    return {"niveau": niveau, "titre": titre, "detail": detail,
            "quoi_faire": quoi_faire}


def _serie(wellness, champ, n=None):
    vals = [w[champ] for w in wellness if w.get(champ) is not None]
    return vals[-n:] if n else vals


def charge(semaines, plan_semaines, semaine_courante):
    """Montee de charge : compare la semaine ecoulee aux trois precedentes.

    La regle des 10% est une approximation, mais l'ecart au plan est plus
    parlant : si le realise depasse largement le planifie, c'est un choix
    de l'instant, pas une progression construite.
    """
    faits = {int(k): v["km"] for k, v in semaines.items()}
    precedente = semaine_courante - 1
    if precedente < 1 or precedente not in faits:
        return None
    ref = [faits[n] for n in range(max(1, precedente - 3), precedente) if n in faits]
    if len(ref) < 2:
        return None
    base = mean(ref)
    if base <= 0:
        return None
    hausse = (faits[precedente] - base) / base * 100

    prevu = next((w["volume_km"] for w in plan_semaines
                  if w["semaine"] == precedente), None)
    ecart = ((faits[precedente] - prevu) / prevu * 100) if prevu else 0

    if hausse > 25 or ecart > 20:
        return _alerte(
            "critique", "Montée de charge trop rapide",
            f"Semaine {precedente} : {faits[precedente]:.0f} km, "
            f"soit {hausse:+.0f} % par rapport à la moyenne des semaines "
            f"précédentes et {ecart:+.0f} % par rapport au plan.",
            "Reviens au volume planifié cette semaine. La blessure de "
            "préparation vient presque toujours d'une semaine trop ambitieuse, "
            "pas d'un manque d'ambition.")
    if hausse > 12:
        return _alerte(
            "attention", "Charge en hausse marquée",
            f"Semaine {precedente} : {faits[precedente]:.0f} km, "
            f"{hausse:+.0f} % contre la moyenne récente.",
            "Rien d'alarmant, mais tiens le volume prévu et surveille "
            "les sensations sur la prochaine sortie longue.")
    return None


def derive_cardiaque(derives):
    """Derive cardiaque sur les sorties longues.

    Au-dessus de 5% la sortie etait trop rapide ou trop longue pour la forme
    du moment. Trois hausses consecutives signalent une fatigue de fond.
    """
    if len(derives) < 2:
        return None
    vals = [d["derive_pct"] for d in derives]
    dernier = vals[-1]

    if dernier > 8:
        return _alerte(
            "critique", "Dérive cardiaque élevée",
            f"Dernière sortie longue : {dernier:.1f} % d'écart entre la "
            f"deuxième et la première moitié.",
            "Ralentis les sorties longues d'environ 20 secondes au kilomètre. "
            "À ce niveau de dérive, la sortie coûte plus qu'elle ne construit.")
    if len(vals) >= 3 and vals[-1] > vals[-2] > vals[-3]:
        return _alerte(
            "attention", "Dérive cardiaque en hausse continue",
            f"Trois sorties de suite en augmentation : "
            f"{vals[-3]:.1f} % puis {vals[-2]:.1f} % puis {vals[-1]:.1f} %.",
            "Le signe habituel d'une fatigue accumulée. Une semaine de "
            "décharge remet généralement la courbe dans le bon sens.")
    if dernier > 5:
        return _alerte(
            "attention", "Dérive au-dessus du seuil",
            f"Dernière sortie longue : {dernier:.1f} %, pour une cible sous 5 %.",
            "Pars plus lentement sur la prochaine sortie longue. "
            "La première moitié doit sembler trop facile.")
    return None


def variabilite(wellness):
    """VFC : la valeur brute ne dit rien, seul l'ecart a la reference compte."""
    vals = _serie(wellness, "hrv")
    if len(vals) < 14:
        return None
    recent = mean(vals[-7:])
    base = mean(vals[-28:]) if len(vals) >= 28 else mean(vals[:-7] or vals)
    if base <= 0:
        return None
    ecart = (recent - base) / base * 100

    if ecart < -15:
        return _alerte(
            "critique", "Variabilité cardiaque en net recul",
            f"Moyenne sur 7 jours à {recent:.0f} ms, contre {base:.0f} ms "
            f"de référence, soit {ecart:+.0f} %.",
            "Ton système nerveux ne récupère plus. Deux jours faciles ou de "
            "repos complet, avant que ça ne devienne une blessure ou un virus.")
    if ecart < -8:
        return _alerte(
            "attention", "Variabilité cardiaque en baisse",
            f"Moyenne sur 7 jours à {recent:.0f} ms, contre {base:.0f} ms "
            f"de référence.",
            "Surveille le sommeil et allège la prochaine séance de qualité "
            "si la baisse se poursuit.")
    return None


def fc_repos(wellness):
    vals = _serie(wellness, "fc_repos")
    if len(vals) < 14:
        return None
    recent = mean(vals[-7:])
    base = mean(vals[-28:]) if len(vals) >= 28 else mean(vals[:-7] or vals)
    if recent - base >= 5:
        return _alerte(
            "attention", "FC de repos élevée",
            f"Moyenne sur 7 jours à {recent:.0f} bpm, contre {base:.0f} bpm "
            f"de référence.",
            "Une hausse de 5 bpm ou plus signale une fatigue, un manque de "
            "sommeil ou un début d'infection. Croisée avec une VFC en baisse, "
            "elle demande du repos.")
    return None


def douleurs(journal):
    """Douleur signalee dans le journal : la seule alerte qui vient de toi."""
    recents = [j for j in journal if j.get("douleur")][-3:]
    if not recents:
        return None
    dernier = recents[-1]
    if len(recents) >= 3:
        return _alerte(
            "critique", "Douleur signalée trois fois de suite",
            f"Dernière mention le {dernier['date']} : {dernier['douleur']}",
            "Trois signalements consécutifs, ce n'est plus une courbature. "
            "Fais examiner avant que la préparation ne soit compromise.")
    return _alerte(
        "attention", "Douleur signalée",
        f"Le {dernier['date']} : {dernier['douleur']}",
        "Note-la à chaque séance. Si elle revient deux fois de plus, "
        "l'alerte passera en rouge.")


def rpe(journal):
    """RPE eleve sur des seances censees etre faciles."""
    notes = [j for j in journal if j.get("rpe")][-5:]
    if len(notes) < 3:
        return None
    moy = mean([j["rpe"] for j in notes])
    if moy >= 7:
        return _alerte(
            "attention", "Effort perçu élevé",
            f"RPE moyen de {moy:.1f} sur les {len(notes)} dernières séances.",
            "La majorité du volume doit se courir autour de 3 ou 4 sur 10. "
            "Un RPE durablement haut en endurance signifie que tu cours "
            "tes séances faciles trop vite.")
    return None


def compute(metrics, plan, semaine_courante):
    """Applique toutes les regles et renvoie les alertes, plus graves d'abord."""
    out = [
        charge(metrics["semaines"], plan["semaines"], semaine_courante),
        derive_cardiaque(metrics["derives"]),
        variabilite(metrics["wellness"]),
        fc_repos(metrics["wellness"]),
        douleurs(metrics["journal"]),
        rpe(metrics["journal"]),
    ]
    out = [a for a in out if a]
    out.sort(key=lambda a: -NIVEAUX[a["niveau"]])
    return out
