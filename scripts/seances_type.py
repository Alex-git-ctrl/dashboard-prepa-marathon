"""Le programme detaille de la semaine : ce qu'il y a a faire, etape par etape.

Le plan disait "45 min" et "sortie longue 18 km". Ca suffit pour un volume,
pas pour aller courir. Ce module transforme une semaine du plan en cinq
seances decrites pas a pas, avec une allure cible par etape prise dans la
calibration, donc recalculee apres chaque course.

Les seances de qualite etaient jusqu'ici de la prose dans les notes du plan
("3 x 6 min a allure semi"). Ecrites en structure, elles deviennent
exportables vers la montre : c'est la meme description qui nourrit la page et
le fichier envoye a Garmin.
"""

# Les jours ne sont que des SUGGESTIONS. Ce qui compte dans une semaine
# d'entrainement, ce n'est pas le jour mais l'espacement : la sortie longue et
# la seance de qualite ne doivent pas se toucher, le reste se pose ou il veut.
# Chaque seance porte donc sa souplesse :
#   libre    : n'importe quel jour de la semaine
#   espacee  : au moins 48 h d'une autre seance exigeante
#   ancree   : une date imposee, c'est le cas d'une course
JOUR_S1, JOUR_S2, JOUR_LONGUE = "mardi", "jeudi", "samedi"
JOUR_RENFO = ("mercredi", "vendredi")

LIBRE = ("libre", None)
ESPACEE = ("espacee", "Au moins 48 h avant ou après la sortie longue.")
LONGUE = ("espacee", "Au moins 48 h après la séance de qualité.")
RENFO_SOUPLESSE = ("libre", "N'importe quel jour, sauf la veille de la "
                            "sortie longue.")

ECHAUFFEMENT_S = 600     # 10 min avant une seance de qualite
RETOUR_S = 600           # 10 min apres

# Les seances de qualite, par semaine du plan.
#
# Une par semaine, le jeudi, sauf quand il n'y a pas la place : semaine de
# course, semaine du test, et les semaines ou la sortie longue porte deja
# l'intensite dans sa finale rapide. Ces semaines-la recoivent des lignes
# droites, qui reveillent la foulee sans couter de recuperation.
#
# La progression suit les blocs. Bloc 1 et 2 : du court et du seuil, pour
# lever le plafond pendant que le volume est encore bas. Bloc 3 et 4 :
# l'allure marathon devient la priorite, le seuil l'entretient. Bloc 5 :
# on rappelle l'allure aux jambes, on ne construit plus.
#
#   forme "intervalles" : echauffement, reps, retour au calme
#   forme "lignes"      : endurance, puis des accelerations breves a la fin
QUALITE = {
    2:  {"forme": "lignes", "reps": 6, "effort_s": 20, "recup_s": 40,
         "zone": "vma",
         "pourquoi": "Réveille la foulée sans coûter de récupération."},
    4:  {"forme": "intervalles", "nom": "8 × 1 min vite", "reps": 8,
         "effort_s": 60, "recup_s": 60, "zone": "vma",
         "pourquoi": "Première séance rapide : de l'économie de foulée, pas "
                     "de la fatigue."},
    5:  {"forme": "intervalles", "nom": "3 × 6 min à allure semi", "reps": 3,
         "effort_s": 360, "recup_s": 120, "zone": "semi",
         "pourquoi": "Habitue la foulée au rythme du semi, sans coûter de "
                     "récupération."},
    6:  {"forme": "lignes", "reps": 6, "effort_s": 20, "recup_s": 40,
         "zone": "vma",
         "pourquoi": "L'intensité est dans la sortie longue de samedi. Jeudi "
                     "reste léger."},
    8:  {"forme": "lignes", "reps": 6, "effort_s": 20, "recup_s": 40,
         "zone": "vma",
         "pourquoi": "Semaine de récupération après le semi. Rien de dur, "
                     "juste de quoi ne pas s'endormir."},
    9:  {"forme": "intervalles", "nom": "5 × 3 min à allure 10 km", "reps": 5,
         "effort_s": 180, "recup_s": 90, "zone": "dix",
         "pourquoi": "Première séance avec les zones recalibrées sur le semi."},
    10: {"forme": "intervalles", "nom": "2 × 10 min au seuil", "reps": 2,
         "effort_s": 600, "recup_s": 180, "zone": "seuil",
         "pourquoi": "Le seuil relève le plafond : l'allure marathon devient "
                     "plus confortable."},
    11: {"forme": "intervalles", "nom": "3 × 8 min à allure semi", "reps": 3,
         "effort_s": 480, "recup_s": 150, "zone": "semi",
         "pourquoi": "Entre le seuil et l'allure marathon, le rythme qui les "
                     "relie."},
    12: {"forme": "intervalles", "nom": "8 × 1 min vite", "reps": 8,
         "effort_s": 60, "recup_s": 60, "zone": "vma",
         "pourquoi": "Semaine de décharge : du court et du vif, rien de long."},
    13: {"forme": "intervalles", "nom": "2 × 15 min à allure marathon",
         "reps": 2, "effort_s": 900, "recup_s": 180, "zone": "marathon",
         "pourquoi": "Installe l'allure marathon comme un automatisme."},
    14: {"forme": "lignes", "reps": 8, "effort_s": 20, "recup_s": 40,
         "zone": "vma",
         "pourquoi": "L'intensité est dans les 5 derniers kilomètres de "
                     "samedi. Jeudi reste léger."},
    15: {"forme": "intervalles", "nom": "3 × 8 min au seuil", "reps": 3,
         "effort_s": 480, "recup_s": 120, "zone": "seuil",
         "pourquoi": "Le seuil entretient le plafond pendant que le volume "
                     "monte."},
    16: {"forme": "intervalles", "nom": "6 × 2 min à allure 10 km", "reps": 6,
         "effort_s": 120, "recup_s": 90, "zone": "dix",
         "pourquoi": "Semaine de décharge : court, vif, et court à finir."},
    17: {"forme": "intervalles", "nom": "3 × 8 min au seuil", "reps": 3,
         "effort_s": 480, "recup_s": 120, "zone": "seuil",
         "pourquoi": "Le seuil relève le plafond : l'allure marathon devient "
                     "plus confortable."},
    18: {"forme": "lignes", "reps": 8, "effort_s": 20, "recup_s": 40,
         "zone": "vma",
         "pourquoi": "L'intensité est dans les 8 derniers kilomètres de "
                     "samedi. Jeudi reste léger."},
    19: {"forme": "intervalles", "nom": "2 × 15 min à allure marathon",
         "reps": 2, "effort_s": 900, "recup_s": 180, "zone": "marathon",
         "pourquoi": "L'allure marathon sur des jambes déjà chargées par le "
                     "volume."},
    20: {"forme": "intervalles", "nom": "6 × 1 min vite", "reps": 6,
         "effort_s": 60, "recup_s": 60, "zone": "vma",
         "pourquoi": "Semaine de décharge avant le dernier bloc."},
    21: {"forme": "lignes", "reps": 8, "effort_s": 20, "recup_s": 40,
         "zone": "vma",
         "pourquoi": "Répétition générale samedi. Jeudi ne doit rien coûter."},
    22: {"forme": "intervalles", "nom": "2 × 10 min au seuil", "reps": 2,
         "effort_s": 600, "recup_s": 180, "zone": "seuil",
         "pourquoi": "Semaine du pic de volume : du seuil, mais court."},
    24: {"forme": "intervalles", "nom": "4 × 3 min à allure 10 km", "reps": 4,
         "effort_s": 180, "recup_s": 90, "zone": "dix",
         "pourquoi": "Assimilation du test : on garde du vif, rien de long."},
    25: {"forme": "intervalles", "nom": "3 × 7 min à allure marathon",
         "reps": 3, "effort_s": 420, "recup_s": 150, "zone": "marathon",
         "pourquoi": "Début de l'affûtage : l'allure reste, le volume baisse."},
    26: {"forme": "intervalles", "nom": "4 × 3 min à allure marathon",
         "reps": 4, "effort_s": 180, "recup_s": 90, "zone": "marathon",
         "pourquoi": "Affûtage : on rappelle l'allure aux jambes, rien de "
                     "plus."},
    27: {"forme": "intervalles", "nom": "3 × 90 s à allure marathon",
         "reps": 3, "effort_s": 90, "recup_s": 90, "zone": "marathon",
         "pourquoi": "Dernier rappel avant Barcelone. Tu dois finir frais."},
}

# Ce qu'une seance de qualite garde comme marge autour du travail. Le
# fractionne et le seuil demandent d'arriver chaud ; l'allure marathon, moins.
MARGE = {"marathon": (8, 4), "semi": (10, 5)}
MARGE_DEFAUT = (12, 5)

# Sorties longues qui se terminent plus vite que leur debut.
FINALE = {
    6:  {"km": 5, "zone": "semi"},
    14: {"km": 5, "zone": "marathon"},
    18: {"km": 8, "zone": "marathon"},
    21: {"km": 6, "zone": "marathon"},
    23: {"km": 30, "zone": "marathon"},
}

# ---------------------------------------------------------------- calisthenie
# Le renforcement n'est plus generique : l'objectif annonce est de progresser
# en calisthenie. Trois principes tiennent la programmation.
#
#   1. Les jambes appartiennent a la course. Pas de squat lourd ni de fente
#      chargee : elles voleraient la recuperation de la sortie longue. Ce qui
#      reste pour le bas du corps est protecteur, pas constructeur.
#   2. Une seance de calisthenie se construit sur des competences, pas sur des
#      series. Chaque exercice porte donc sa regle de passage : ce qu'il faut
#      atteindre pour avoir le droit de passer a la variante suivante. C'est
#      cette regle qui fait progresser, pas le fait de refaire la seance.
#   3. La charge suit celle du plan de course. Aux semaines de decharge, au
#      pic de volume et pendant l'affutage, le volume baisse ici aussi. Deux
#      entrainements qui montent en meme temps, c'est une blessure.
#
# Les deux competences visees sont le muscle-up et l'ATR libre, parce qu'elles
# sont deja amorcees et qu'aucune des deux ne demande de charger les jambes.

# Semaines ou le volume de calisthenie recule d'une serie par exercice : la
# course y demande deja tout ce qu'il reste.
TYPES_ALLEGES = {"decharge", "pic", "TEST", "COURSE", "recup", "affutage"}

# Derniere ligne droite : une seule seance, et rien qui laisse des courbatures.
SEMAINE_AFFUTAGE = 26


def _ex(nom, series, consigne=None, progression=None):
    return {"nom": nom, "series": series, "consigne": consigne,
            "progression": progression}


PHASES = [
    {
        "jusqu_a": 9,
        "nom": "Fondations",
        "quoi": "Neuf semaines de volume propre : rien ne tient sans "
                "tractions et dips stricts.",
        "seances": [
            {
                "nom": "Tirage et gainage",
                "pourquoi": "Le dos et la ceinture tiennent la posture quand "
                            "la fatigue arrive.",
                "exos": [
                    _ex("Tractions strictes", "5 séries, 2 répétitions de réserve",
                        "Bras tendus en bas, menton au-dessus, aucun balancement.",
                        "5 × 8 propres : ajoute 5 kg."),
                    _ex("Tractions australiennes lentes", "3 × 10",
                        "Trois secondes de descente, corps aligné.",
                        "3 × 12 sans à-coup : pieds surélevés."),
                    _ex("Suspension à la barre", "3 × 45 s",
                        "Épaules actives, jamais pendues dans le vide.",
                        "60 s, puis un bras en alternance."),
                    _ex("Hollow body", "3 × 30 s",
                        "Bas du dos plaqué. S'il décolle, remonte les jambes.",
                        "45 s : bras tendus au-dessus de la tête."),
                    _ex("Gainage latéral", "3 × 40 s par côté",
                        "Bassin haut, épaule à l'aplomb du coude."),
                ],
            },
            {
                "nom": "Poussée et équilibre",
                "pourquoi": "Poussée verticale. L'ATR vient de la fréquence, "
                            "pas de l'intensité.",
                "exos": [
                    _ex("Dips aux barres parallèles", "4 × 8",
                        "Descends sous l'angle droit, buste légèrement penché.",
                        "4 × 10 : lest de 5 kg."),
                    _ex("Pompes déclinées", "3 × 12",
                        "Pieds surélevés d'environ 40 cm, corps en planche.",
                        "Puis pseudo-planche, mains à hauteur de hanches."),
                    _ex("ATR face au mur", "5 × 30 s",
                        "Ventre au mur, mains à 15 cm. Alignement, pas banane.",
                        "Décolle un pied, puis alterne les deux."),
                    _ex("Pike push-ups", "3 × 8",
                        "Bassin haut, tête entre les bras, front vers le sol.",
                        "Pieds surélevés, puis pompes ATR au mur."),
                    _ex("L-sit", "4 × 20 s",
                        "Genoux groupés si le dos s'arrondit.",
                        "30 s groupé, puis jambes tendues."),
                    _ex("Mollets debout", "3 × 15",
                        "Le seul travail de jambes : il protège le tendon "
                        "d'Achille."),
                ],
            },
        ],
    },
    {
        "jusqu_a": 19,
        "nom": "Force et compétences",
        "quoi": "Dix semaines sur le muscle-up et l'ATR libre, pendant "
                "que la course monte.",
        "seances": [
            {
                "nom": "Vers le muscle-up",
                "pourquoi": "Pas plus de tractions : de la hauteur, une "
                            "transition apprise à part, un dos horizontal.",
                "exos": [
                    _ex("Tractions lestées", "5 × 5, 1 répétition de réserve",
                        "Le lest rend la traction à vide facile, rien de plus.",
                        "5 séries sans ralentir : ajoute 2,5 kg."),
                    _ex("Tractions explosives", "5 × 3",
                        "Le plus haut possible, poitrine vers la barre. Repos "
                        "complet.",
                        "Barre au bas du sternum : tu as la hauteur."),
                    _ex("Négatifs de muscle-up", "4 × 3",
                        "Départ en appui bras tendus, descente en 5 secondes.",
                        "Les 3 contrôlés : tente le mouvement complet."),
                    _ex("Front lever groupé", "5 × 15 s",
                        "Bras tendus, dos rond, bassin à hauteur des épaules.",
                        "Une jambe tendue, puis demi-écart, puis jambes "
                        "tendues."),
                    _ex("Rowing inversé pieds surélevés", "3 × 10",
                        "Le dos horizontal, que la traction verticale ne "
                        "travaille pas."),
                ],
            },
            {
                "nom": "Vers l'ATR libre",
                "pourquoi": "L'équilibre se joue aux poignets, pas aux "
                            "épaules. Le mur s'installe, puis se quitte.",
                "exos": [
                    _ex("Dips lestés", "4 × 6",
                        "Comme la traction : le poids de corps doit rester "
                        "facile.",
                        "4 × 8 : ajoute 2,5 kg."),
                    _ex("ATR dos au mur", "5 × 40 s",
                        "Talons au mur, corps aligné. Cherche à décoller les "
                        "talons.",
                        "40 s tenues : éloigne les mains de 10 cm."),
                    _ex("Pompes ATR au mur", "4 × 5",
                        "Face au mur, tête qui frôle le sol.",
                        "Mains sur des cales pour gagner l'amplitude."),
                    _ex("Pompes pseudo-planche", "3 × 8",
                        "Mains aux hanches, coudes au corps, épaules devant."),
                    _ex("L-sit", "4 × 30 s",
                        "Jambes tendues, pointes de pieds tirées.",
                        "40 s tenues : passe au V-sit."),
                    _ex("Ischios nordiques", "3 × 6",
                        "Descente freinée. C'est l'ischio qui lâche sur les "
                        "sorties longues."),
                ],
            },
        ],
    },
    {
        "jusqu_a": 99,
        "nom": "Entretien",
        "quoi": "La course prend la priorité. On garde l'acquis, on ne "
                "construit plus.",
        "seances": [
            {
                "nom": "Entretien tirage",
                "pourquoi": "Conserver, pas progresser : progresser coûterait "
                            "des jambes lourdes le dimanche.",
                "exos": [
                    _ex("Tractions strictes", "4 × 5",
                        "Sans lest. Sors de la série avec trois répétitions en "
                        "réserve."),
                    _ex("Front lever groupé", "4 × 15 s",
                        "Entretien de la compétence, pas de progression."),
                    _ex("Hollow body", "3 × 30 s",
                        "Il tient la posture au 35e kilomètre."),
                ],
            },
            {
                "nom": "Entretien poussée",
                "pourquoi": "Maintenir l'ATR par la fréquence, sans chercher "
                            "la fatigue.",
                "exos": [
                    _ex("Dips", "4 × 6",
                        "Poids de corps uniquement."),
                    _ex("ATR dos au mur", "4 × 30 s",
                        "La répétition garde l'équilibre, pas la durée."),
                    _ex("L-sit", "3 × 20 s"),
                    _ex("Gainage latéral", "3 × 45 s par côté"),
                ],
            },
        ],
    },
]


def _phase(semaine):
    for ph in PHASES:
        if semaine <= ph["jusqu_a"]:
            return ph
    return PHASES[-1]


def calisthenie(w):
    """Les seances de calisthenie de la semaine, adaptees a sa charge."""
    ph = _phase(w["semaine"])
    seances = ph["seances"]
    allege = w.get("type") in TYPES_ALLEGES
    affutage = w["semaine"] >= SEMAINE_AFFUTAGE
    if affutage:
        # Semaine de course : une seule seance, et elle s'arrete tot.
        seances = seances[:1]

    # La consigne de la semaine, dans l'ordre ou elle prime : une course
    # passe avant l'affutage, qui passe avant une simple decharge.
    if w.get("type") == "COURSE":
        consigne = ("Course cette semaine : rien dans les deux jours qui "
                    "la précèdent, rien qui laisse des courbatures.")
    elif affutage:
        consigne = ("Dernière ligne droite : une seule séance, à volume "
                    "réduit.")
    elif allege:
        consigne = ("Semaine allégée : retire une série à chaque exercice "
                    "ici aussi.")
    else:
        consigne = None

    out = []
    for s in seances:
        # La phase est deja nommee dans l'en-tete de la carte et son
        # intention est rappelee une seule fois au-dessus du programme.
        # Ne reste donc ici que ce qui demande une decision cette semaine.
        note = consigne
        out.append({"type": "renfo", "nom": s["nom"], "discipline": "calisthénie",
                    "phase": ph["nom"], "pourquoi": s["pourquoi"],
                    "exos": s["exos"], "note": note,
                    "allege": bool(consigne)})
    return out


def _allure(s):
    return "%d:%02d" % (s // 60, s % 60)


def zones_par_cle(calibration):
    """Bornes d'allure en secondes par kilometre, indexees par cle.

    L'allure semi n'est pas une zone de Daniels : elle se deduit de la
    projection sur 21,0975 km, qui se recalcule apres chaque course comme le
    reste.
    """
    z = {c["cle"]: (c["rapide_s_km"], c["lent_s_km"]) for c in calibration["zones"]}
    semi = calibration["projections"]["semi"]["temps_s"] / 21.0975
    # La projection sur semi suppose une endurance specifique pas encore
    # construite : elle ressortait plus rapide que le seuil, ce qui est faux.
    # L'allure semi se tient forcement entre l'allure marathon et le seuil.
    plancher = z["seuil"][1] + 3
    plafond = z["marathon"][0] - 3
    semi = max(plancher, min(plafond, semi))
    z["semi"] = (round(semi - 4), round(semi + 4))
    return z


def _etape(nom, zones, cle, duree_s=None, distance_m=None, consigne=None):
    rapide, lent = zones[cle]
    return {"nom": nom, "zone": cle, "duree_s": duree_s, "distance_m": distance_m,
            "allure_rapide_s_km": rapide, "allure_lente_s_km": lent,
            "allure_texte": "%s à %s /km" % (_allure(rapide), _allure(lent)),
            "consigne": consigne}


def _endurance(minutes, zones, nom="Endurance fondamentale"):
    return {
        "type": "course", "nom": nom, "duree_min": minutes,
        "pourquoi": "Construit la base aérobie. Ne compte que si elle "
                    "reste lente.",
        "etapes": [_etape("Endurance", zones, "ef", duree_s=minutes * 60,
                          consigne="Conversation entière possible. Sinon, "
                                   "ralentis.")],
    }


def _travail_s(reps, q):
    """Duree du bloc de travail, recuperations comprises."""
    return reps * q["effort_s"] + max(0, reps - 1) * q["recup_s"]


def _tient(q, minutes):
    """Combien de repetitions tiennent dans le creneau prevu par le plan.

    Le creneau vient du plan, et le plan le tient du midi d'Alex : une
    seance qui deborde ne se fait pas. Plutot que d'allonger la seance, on
    retire des repetitions, en gardant l'echauffement et le retour au calme
    intacts. Une semaine allegee par l'adaptation raccourcit donc aussi sa
    seance de qualite, ce qui est exactement ce qu'on veut.
    """
    ech, ret = MARGE.get(q["zone"], MARGE_DEFAUT)
    place = minutes * 60 - (ech + ret) * 60
    reps = q["reps"]
    while reps > 1 and _travail_s(reps, q) > place:
        reps -= 1
    return reps


def _qualite(q, zones, minutes):
    """Une seance de qualite qui remplit le creneau, sans le deborder.

    Le travail est fixe, c'est l'echauffement et le retour au calme qui
    absorbent ce qui reste. Avant, la seance durait ce qu'elle durait et le
    programme affichait 36 min la ou la semaine en comptait 45.
    """
    reps = _tient(q, minutes)
    ech_min, ret_min = MARGE.get(q["zone"], MARGE_DEFAUT)
    reste = max(0, minutes * 60 - _travail_s(reps, q))
    # Les deux tiers du reste devant, un tiers derriere : on court mieux
    # chaud qu'on ne recupere en trottant.
    ech = max(ech_min * 60, int(reste * .62))
    ret = max(ret_min * 60, reste - ech)

    nom = q.get("nom")
    if reps != q["reps"] and nom:
        nom = nom.replace("%d ×" % q["reps"], "%d ×" % reps, 1)

    et = [_etape("Échauffement", zones, "ef", duree_s=ech,
                 consigne="Progressif, sans jamais forcer.")]
    for i in range(reps):
        et.append(_etape("Effort %d sur %d" % (i + 1, reps), zones,
                         q["zone"], duree_s=q["effort_s"],
                         consigne="Allure régulière du début à la fin."))
        if i < reps - 1:
            et.append(_etape("Récupération", zones, "ef", duree_s=q["recup_s"],
                             consigne="Trot lent, pas d'arrêt complet."))
    et.append(_etape("Retour au calme", zones, "ef", duree_s=ret,
                     consigne="Jusqu'à ce que la respiration redevienne "
                              "normale."))
    return {"type": "course", "nom": nom, "duree_min": sum(
        e["duree_s"] for e in et) // 60, "pourquoi": q["pourquoi"],
        "etapes": et, "qualite": True}


def _lignes(q, zones, minutes):
    """De l'endurance, puis des accelerations breves.

    Une ligne droite n'est pas une seance de qualite : elle dure vingt
    secondes, elle ne creuse aucune fatigue, et elle garde la foulee vive
    les semaines ou la sortie longue porte deja tout le travail.
    """
    bloc = _travail_s(q["reps"], q)
    ef = max(60, minutes * 60 - bloc)
    et = [_etape("Endurance", zones, "ef", duree_s=ef,
                 consigne="Conversation entière possible. Sinon, ralentis.")]
    for i in range(q["reps"]):
        et.append(_etape("Ligne droite %d sur %d" % (i + 1, q["reps"]), zones,
                         q["zone"], duree_s=q["effort_s"],
                         consigne="Vite mais relâché, jamais en force."))
        if i < q["reps"] - 1:
            et.append(_etape("Retour au trot", zones, "ef",
                             duree_s=q["recup_s"],
                             consigne="Marche ou trot, la respiration doit "
                                      "redescendre."))
    return {"type": "course",
            "nom": "Endurance et %d lignes droites" % q["reps"],
            "duree_min": sum(e["duree_s"] for e in et) // 60,
            "pourquoi": q["pourquoi"], "etapes": et}


def _longue(km, zones, finale):
    et = []
    # Quand la finale couvre toute la distance, il s'agit d'un test a allure
    # cible, pas d'une sortie a finale rapide : un echauffement, puis l'effort.
    # Sans ce cas, le test 30K sortait avec une etape d'endurance de 0,0 km.
    if finale and km - finale["km"] <= .5:
        et.append(_etape("Échauffement", zones, "ef", distance_m=2000,
                         consigne="Deux kilomètres tranquilles avant "
                                  "l'allure cible."))
        et.append(_etape("Test à allure marathon", zones, finale["zone"],
                         distance_m=round(km * 1000),
                         consigne="Allure tenue du premier au dernier "
                                  "kilomètre. La seconde moitié décide."))
        return {"type": "course", "nom": "Test %s km à allure marathon" % _km(km),
                "distance_km": km,
                "pourquoi": "L'indicateur le plus fiable avant Barcelone : "
                            "tenir l'allure sur 30 km, ou revoir l'objectif.",
                "etapes": et}
    if finale:
        et.append(_etape("Endurance", zones, "ef",
                         distance_m=round((km - finale["km"]) * 1000),
                         consigne="La première partie doit sembler trop facile."))
        et.append(_etape("Finale à %s" % ("allure marathon" if finale["zone"] == "marathon"
                                          else "allure semi"),
                         zones, finale["zone"],
                         distance_m=round(finale["km"] * 1000),
                         consigne="Accélérer sur des jambes déjà fatiguées."))
        pourquoi = ("Accélérer sur des jambes vides : c'est le 30e "
                    "kilomètre du marathon.")
    else:
        et.append(_etape("Endurance", zones, "ef", distance_m=round(km * 1000),
                         consigne="Allure constante. Bois toutes les "
                                  "20 min au-delà de 1 h 30."))
        pourquoi = ("La séance qui décide d'un marathon : réserves, "
                    "appuis, tolérance à l'inconfort.")
    return {"type": "course", "nom": "Sortie longue %s km" % _km(km),
            "distance_km": km, "pourquoi": pourquoi, "etapes": et}


def _km(v):
    return ("%.1f" % v).rstrip("0").rstrip(".").replace(".", ",")


def programme(w, calibration, courses):
    """Les cinq seances d'une semaine du plan, decrites pas a pas."""
    zones = zones_par_cle(calibration)
    course = next((c for c in courses if c["semaine"] == w["semaine"]), None)
    out = []

    def pose(seance, jour, souplesse):
        seance = dict(seance)
        seance["jour_suggere"] = jour
        seance["souplesse"], seance["contrainte"] = souplesse
        return seance

    s1 = w.get("seance1_min")
    if s1:
        out.append(pose(_endurance(s1, zones), JOUR_S1, LIBRE))

    s2 = w.get("seance2_min")
    q = QUALITE.get(w["semaine"])
    if q and s2 and q["forme"] == "lignes":
        # Des lignes droites ne fatiguent pas : elles peuvent tomber
        # n'importe quel jour, comme une sortie facile.
        out.append(pose(_lignes(q, zones, s2), JOUR_S2, LIBRE))
    elif q and s2:
        out.append(pose(_qualite(q, zones, s2), JOUR_S2, ESPACEE))
    elif s2:
        out.append(pose(_endurance(s2, zones), JOUR_S2, LIBRE))

    if course:
        # Une course a une date, elle. C'est la seule seance vraiment ancree.
        out.append(pose({"type": "course", "course": True,
                         "nom": "%s · %s" % (course["nom"], course["cible"]),
                         "distance_km": course["distance_km"],
                         "pourquoi": course["role"], "etapes": []},
                        course["jour"],
                        ("ancree", "Date imposée par la course.")))
    else:
        out.append(pose(_longue(w["sortie_longue_km"], zones,
                                FINALE.get(w["semaine"])), JOUR_LONGUE, LONGUE))

    for j, s in zip(JOUR_RENFO, calisthenie(w)):
        out.append(pose(s, j, RENFO_SOUPLESSE))

    # L'ordre est celui de la lecture : les courses d'abord, du plus facile au
    # plus exigeant, puis le renforcement. Ce n'est pas un ordre d'execution.
    rang = {"course": 0, "renfo": 1}
    for i, x in enumerate(out):
        x["ordre"] = i + 1
    out.sort(key=lambda x: (rang[x["type"]], x["ordre"]))
    for i, x in enumerate(out):
        x["ordre"] = i + 1
    return out


def construit(plan, calibration, ajustees, semaine_courante, combien=3):
    """Le programme de la semaine en cours et des suivantes.

    Les semaines reecrites par l'adaptation sont prises dans leur version
    adaptee : le programme doit dire ce qu'il faut faire vraiment, pas ce que
    le plan demandait avant de t'ecouter.
    """
    if not semaine_courante:
        semaine_courante = 1
    par_semaine = {a["semaine"]: a for a in (ajustees or [])}
    out = []
    for w in plan["semaines"]:
        if not (semaine_courante <= w["semaine"] < semaine_courante + combien):
            continue
        a = par_semaine.get(w["semaine"])
        eff = dict(w)
        if a:
            eff["sortie_longue_km"] = a["longue_adapte"]
            eff["seance1_min"] = a["seance1_adapte"]
            eff["seance2_min"] = a["seance2_adapte"]
            eff["volume_km"] = a["volume_adapte"]
        out.append({
            "semaine": w["semaine"], "lundi": w["lundi"], "dimanche": w["dimanche"],
            "bloc": w["bloc"], "note": w.get("note"),
            "phase_calisthenie": _phase(w["semaine"])["nom"],
            "phase_quoi": _phase(w["semaine"])["quoi"],
            "volume_km": eff["volume_km"], "adapte": bool(a),
            "seances": programme(eff, calibration, plan["courses"]),
        })
    return out
