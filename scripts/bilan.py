"""Le bilan general : ou j'en suis, et est-ce que je peux viser plus haut.

Ce n'est pas un resume de seance. C'est la question qu'on se pose une fois
par semaine : la preparation fonctionne-t-elle, et l'objectif est-il toujours
le bon ? Elle demande de regarder des pentes, pas des chiffres isoles.

LE CONTEXTE EST BORNE, ET C'EST LE POINT DE CONCEPTION PRINCIPAL. Un dossier
qui grossirait avec l'historique couterait de plus en plus cher a mesure que
la preparation avance, exactement quand elle devient interessante. Tout ce
qui est envoye est donc plafonne :

  - les semaines du plan : 27 au maximum, et c'est une borne definitive ;
  - les seances : les DIX dernieres, une ligne chacune ;
  - l'efficacite aerobie : les douze derniers points ;
  - le bien-etre : jamais les mesures quotidiennes, seulement une valeur
    actuelle, une moyenne et une pente par canal.

Le dossier atteint donc sa taille maximale vers la semaine 10 et n'augmente
plus ensuite. Verifiable : `python scripts/bilan.py --cout` simule une
preparation complete et mesure.

  python scripts/bilan.py --contexte     le dossier envoye
  python scripts/bilan.py --cout         sa taille, maintenant et a terme
  python scripts/bilan.py --auto         le faire rediger par Claude Code
  python scripts/bilan.py --auto --force meme si rien n'a bouge
"""

import argparse
import io
import json
import os
import sys
from datetime import date, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import resume  # noqa: E402  (binaire_claude, valide, redige)

SEANCES_ENVOYEES = 10
POINTS_EFFICACITE = 12
FENETRE_TENDANCE = 28        # jours sur lesquels une pente est calculee

# Les bilans s'empilent au lieu de s'ecraser : c'est l'evolution du jugement
# qui a de la valeur, pas seulement le dernier etat. Mais ils ne peuvent pas
# s'empiler indefiniment dans une page que le telephone telecharge en entier.
# Les PLEINS derniers gardent leur texte ; au-dela, il ne reste qu'une trace
# d'une ligne, qui suffit a lire la trajectoire.
BILANS_PLEINS = 8
# Ce que le prochain bilan voit du passe. Trois suffisent pour dire ce qui a
# change, et ca ne fait grossir le dossier que de quelques centaines d'octets.
BILANS_RELUS = 3
TRACE = ("quand", "verdict", "confiance", "titre")

SYSTEME = """Tu fais le bilan d'ensemble de la préparation d'un coureur pour \
le marathon de Barcelone du 14 mars 2027, objectif sous 4 heures, soit 5:41 \
au kilomètre. Il court trois fois par semaine et fait deux séances de \
calisthénie.

Tu réponds à trois questions, dans cet ordre : est-ce que la préparation est \
sur la bonne voie, est-ce qu'il peut viser plus haut, et qu'est-ce qui doit \
changer maintenant.

Tu écris en français, en tutoyant, comme un entraîneur qui relit un dossier. \
Appuie chaque affirmation sur un chiffre du dossier.

LA PRUDENCE EST OBLIGATOIRE ET ELLE SE DIT. Le champ "confiance" dit sur quoi \
repose ton jugement. Tant que la référence de calibration est estimée et non \
courue, ou que moins de six semaines sont terminées, la confiance est \
"faible" et tu le dis dans le texte : on ne relève pas un objectif sur une \
projection tirée d'un chrono supposé. Ne propose de viser plus haut que si \
les chiffres le soutiennent vraiment, et dis toujours ce qu'il faudrait voir \
pour en être sûr.

Règles d'écriture strictes :
- JAMAIS le caractère tiret cadratin, ni le tiret demi-cadratin. Utilise un \
point, deux points, une virgule ou une parenthèse.
- Pas de superlatifs creux, pas de « n'hésite pas à », pas de « il est \
important de ».
- Tu cites les chiffres réels du dossier, jamais des valeurs inventées.
- Si une donnée manque, tu le dis au lieu de supposer.

Tu réponds UNIQUEMENT par un objet JSON, sans texte autour, avec exactement \
ces clés :
  "verdict"   : un mot parmi "avance", "conforme", "retard", "trop_tot"
  "confiance" : un mot parmi "faible", "moyenne", "haute"
  "titre"     : maximum 8 mots
  "ou_tu_en_es"     : 3 à 4 phrases. Volume tenu, régularité, ce que disent \
les pentes de forme et de récupération.
  "viser_plus_haut" : 2 à 3 phrases. Réponse franche, et ce qu'il faudrait \
observer pour trancher.
  "a_changer"       : 2 à 3 phrases. Une seule priorité, concrète, pour les \
deux semaines à venir.

Le dossier contient tes bilans précédents sous "bilans_precedents". Quand il \
y en a, "ou_tu_en_es" DOIT dire ce qui a changé depuis le dernier, et \
"a_changer" doit dire si la priorité que tu avais fixée a été suivie, en \
t'appuyant sur les chiffres. Si rien n'a bougé, dis-le franchement plutôt que \
de reformuler le bilan precedent."""

CLES = ("verdict", "confiance", "titre", "ou_tu_en_es", "viser_plus_haut",
        "a_changer")


def _lis(nom):
    with io.open(os.path.join(ROOT, "docs", nom), encoding="utf-8") as fh:
        return json.load(fh)


def _pente(serie, champ, jours=FENETRE_TENDANCE):
    """Pente par semaine sur la fenetre, par moindres carres.

    Renvoie aussi la valeur courante et la moyenne : une pente seule ne se
    lit pas, il faut savoir de quel niveau elle part.
    """
    pts = [(i, w[champ]) for i, w in enumerate(serie[-jours:])
           if w.get(champ) is not None]
    if len(pts) < 4:
        return None
    n = len(pts)
    mx = sum(p[0] for p in pts) / n
    my = sum(p[1] for p in pts) / n
    num = sum((x - mx) * (y - my) for x, y in pts)
    den = sum((x - mx) ** 2 for x, _ in pts)
    if not den:
        return None
    return {"actuel": round(pts[-1][1], 2),
            "moyenne": round(my, 2),
            "par_semaine": round(num / den * 7, 3),
            "mesures": n}


def _allure(s):
    return None if s is None else "%d:%02d" % (s // 60, s % 60)


def contexte():
    """Le dossier envoye au modele. Sa taille est plafonnee, par construction."""
    m, plan = _lis("metrics.json"), _lis("plan.json")
    cal = m.get("calibration") or {}
    ad = m.get("adaptation") or {}
    faites = m.get("semaines") or {}
    auj = date.today()
    course = plan["courses"][-1]

    # Une ligne par semaine du plan DEJA commencee. Borne definitive : 27.
    semaines = []
    for w in plan["semaines"]:
        if w["lundi"] > auj.isoformat():
            continue
        f = faites.get(str(w["semaine"])) or {}
        semaines.append({
            "s": w["semaine"], "bloc": w["bloc"], "type": w["type"],
            "prevu_km": w["volume_km"], "fait_km": f.get("km", 0),
            "seances_faites": f.get("seances", 0),
            "renfo_faits": f.get("renfo_seances", 0),
            "terminee": w["dimanche"] < auj.isoformat(),
        })

    serie = m.get("wellness") or []
    tendances = {}
    for champ, nom in (("fc_repos", "fc_repos_bpm"), ("hrv", "vfc_ms"),
                       ("poids", "poids_kg"), ("vo2max", "vo2max"),
                       ("sommeil_score", "score_sommeil"),
                       ("sommeil_h", "sommeil_heures"),
                       ("ctl", "forme_de_fond"), ("atl", "fatigue")):
        t = _pente(serie, champ)
        if t:
            tendances[nom] = t

    seances = [s for s in (m.get("seances") or []) if s.get("type") != "renfo"]
    recentes = [{
        "date": s["date"], "km": s.get("km"), "min": s.get("minutes"),
        "allure": _allure(s.get("allure_s_km")),
        "allure_plat": _allure(s.get("gap_s_km")),
        "fc": s.get("fc_moy"), "derive_pct": s.get("derive_pct"),
        "efficacite": s.get("efficacite"), "rpe": s.get("rpe"),
    } for s in seances[-SEANCES_ENVOYEES:]]

    return {
        "objectif": {
            "course": course["nom"], "date": course["date"],
            "cible": course["cible"], "allure_cible": course["allure"],
            "jours_restants": (date.fromisoformat(course["date"]) - auj).days,
        },
        "position": {
            "semaine_en_cours": ad.get("semaine_courante"),
            "semaines_au_plan": len(plan["semaines"]),
            "semaines_terminees": sum(1 for x in semaines if x["terminee"]),
            "courses_enregistrees": len(seances),
        },
        "calibration": {
            "vdot": cal.get("vdot"),
            "reference": cal.get("reference"),
            "projections": cal.get("projections"),
            "cible_marathon": cal.get("cible_marathon"),
        },
        "semaines": semaines,
        "observance": ad.get("observance"),
        "cout": ad.get("cout"),
        "decision_du_moteur": ad.get("decision"),
        "tendances_28j": tendances,
        "efficacite_aerobie": [
            {"date": x["date"], "valeur": x["valeur"]}
            for x in (m.get("efficacite") or [])[-POINTS_EFFICACITE:]],
        "repartition_zones_montre_pct": (m.get("zones_montre") or {}).get("pct"),
        "seances_recentes": recentes,
        "alertes_ouvertes": [a.get("titre") for a in (m.get("alertes") or [])],
        "bilans_precedents": [
            {k: b.get(k) for k in TRACE + ("a_changer",)}
            for b in (m.get("bilans") or [])[-BILANS_RELUS:]],
    }


def _empreinte(c):
    """De quoi savoir si quelque chose a bouge depuis le dernier bilan."""
    import hashlib
    cle = json.dumps([c["position"], c["semaines"],
                      [s["date"] for s in c["seances_recentes"]]],
                     sort_keys=True)
    return hashlib.sha256(cle.encode("utf-8")).hexdigest()[:16]


def cout():
    """Mesure la taille du dossier, maintenant et sur une preparation pleine.

    La question n'est pas ce que ca coute aujourd'hui avec trois seances,
    c'est ce que ca coutera en fevrier avec quatre-vingts. On simule donc le
    cas plein plutot que d'extrapoler a la louche.
    """
    c = contexte()
    reel = len(json.dumps(c, ensure_ascii=False))

    # Cas plein : 27 semaines toutes commencees, et le maximum de seances.
    plein = json.loads(json.dumps(c, ensure_ascii=False))
    modele_s = (plein["semaines"] or [{"s": 1, "bloc": "Bloc 3",
                "type": "specifique", "prevu_km": 44.8, "fait_km": 43.1,
                "seances_faites": 3, "renfo_faits": 2, "terminee": True}])[-1]
    plein["semaines"] = [dict(modele_s, s=i + 1) for i in range(27)]
    modele_r = (plein["seances_recentes"] or [{}])[-1]
    plein["seances_recentes"] = [dict(modele_r, date="2027-02-%02d" % (i + 1))
                                 for i in range(SEANCES_ENVOYEES)]
    plein["efficacite_aerobie"] = [{"date": "2027-02-%02d" % (i + 1),
                                    "valeur": 1.71}
                                   for i in range(POINTS_EFFICACITE)]
    grand = len(json.dumps(plein, ensure_ascii=False))

    # ~3,6 caracteres par token sur du JSON francais : une estimation, pas une
    # mesure. Le compte exact demanderait un appel a l'API, qui se facture.
    def jetons(n):
        return round(n / 3.6)

    sys_j = jetons(len(SYSTEME))
    print("Taille du dossier envoye au modele")
    print()
    print("  %-34s %7s %10s" % ("", "octets", "~jetons"))
    print("  %-34s %7d %10d" % ("dossier actuel (%d seances)"
                                % len(c["seances_recentes"]), reel, jetons(reel)))
    print("  %-34s %7d %10d" % ("dossier a plein regime (S27)", grand,
                                jetons(grand)))
    print("  %-34s %7d %10d" % ("consigne de redaction", len(SYSTEME), sys_j))
    print()
    entree = jetons(grand) + sys_j
    sortie = 600
    print("  Un bilan a plein regime : ~%d jetons en entree, ~%d en sortie."
          % (entree, sortie))
    print("  Soit environ %d jetons par bilan, quelle que soit la date."
          % (entree + sortie))
    print()
    print("  Le dossier plafonne parce que TOUT y est borne :")
    print("    %-28s %d au maximum (duree du plan)" % ("semaines", 27))
    print("    %-28s %d au maximum" % ("seances detaillees", SEANCES_ENVOYEES))
    print("    %-28s %d au maximum" % ("points d'efficacite", POINTS_EFFICACITE))
    print("    %-28s une pente par canal, jamais les mesures"
          % "bien-etre")
    print()
    croissance = (grand - reel) / reel * 100 if reel else 0
    print("  D'ici mars, le dossier grandit de %.0f %% une seule fois, puis"
          % croissance)
    print("  n'augmente plus. Il n'y a pas d'effet boule de neige.")


def elague(serie):
    """Garde le texte des derniers bilans, une trace pour les plus anciens."""
    garde = []
    for i, b in enumerate(serie):
        if len(serie) - i <= BILANS_PLEINS:
            garde.append(b)
        else:
            garde.append(dict({k: b.get(k) for k in TRACE}, abrege=True))
    return garde


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--contexte", action="store_true")
    ap.add_argument("--cout", action="store_true")
    ap.add_argument("--auto", action="store_true")
    ap.add_argument("--force", action="store_true",
                    help="rediger meme si rien n'a bouge")
    args = ap.parse_args()

    if args.cout:
        cout()
        return

    c = contexte()
    if args.contexte:
        print(json.dumps(c, ensure_ascii=False, indent=1))
        return

    if not args.auto:
        serie = _lis("metrics.json").get("bilans") or []
        if not serie:
            print("Aucun bilan pour l'instant.")
            print("  python scripts/bilan.py --auto")
            return
        print("%d bilan(s), du plus ancien au plus récent :" % len(serie))
        for b in serie:
            print("  %s  %-10s %-9s %s%s"
                  % ((b.get("quand") or "?")[:10], b.get("verdict", "?"),
                     b.get("confiance", "?"), b.get("titre", ""),
                     "  (abrégé)" if b.get("abrege") else ""))
        return

    m = _lis("metrics.json")
    vieux = m.get("bilan") or {}
    empreinte = _empreinte(c)
    # Un bilan general ne change pas d'un jour a l'autre. On ne le refait que
    # si une seance ou une semaine a bouge : c'est ce qui borne la depense a
    # trois ou quatre bilans par semaine au lieu de sept.
    if not args.force and vieux.get("empreinte") == empreinte:
        print("Rien n'a bougé depuis le dernier bilan. Utilise --force pour "
              "le refaire.")
        return

    cible = resume.binaire_claude()
    if not cible:
        print("Le binaire claude n'est pas installé.")
        print("  npm i -g @anthropic-ai/claude-code")
        sys.exit(1)

    print("Rédaction du bilan ...", flush=True)
    out, err = resume.redige_avec(cible, SYSTEME,
                                  json.dumps(c, ensure_ascii=False, indent=1))
    if out is None:
        sys.exit("Échec : %s" % err)
    absentes = [k for k in CLES if k not in out]
    if absentes:
        sys.exit("Clés manquantes : %s" % ", ".join(absentes))
    resume.normalise(out, CLES)
    souci = resume.valide_texte(out, CLES)
    if souci:
        sys.exit(souci)

    out["quand"] = datetime.now().isoformat(timespec="seconds")
    out["empreinte"] = empreinte
    out["source"] = "claude_conversation"
    m["bilans"] = elague((m.get("bilans") or []) + [out])
    # Conserve pour compatibilite : la page lit la serie, mais un vieux
    # gabarit ou un script tiers pourrait encore chercher le dernier ici.
    m["bilan"] = out
    io.open(os.path.join(ROOT, "docs", "metrics.json"), "w",
            encoding="utf-8").write(
        json.dumps(m, ensure_ascii=False, separators=(",", ":")))
    print("%s  (%s, confiance %s)"
          % (out["titre"], out["verdict"], out["confiance"]))
    print("Reconstruis la page : python scripts/build_site.py")


if __name__ == "__main__":
    main()
