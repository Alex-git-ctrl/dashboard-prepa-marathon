"""Ecrire un resume de seance SANS passer par l'API facturee.

Le probleme. scripts/resume_ia.py sait appeler Claude, mais par l'API
Anthropic, qui se facture au token et n'a rien a voir avec un abonnement
Claude. Sans ANTHROPIC_API_KEY, la page bascule sur l'analyse par regles,
qui est honnete mais mecanique.

Le contournement. Claude Code, lui, tourne sur l'abonnement. Le resume peut
donc etre redige en conversation, puis FIGE dans docs/resumes.json. Le champ
`fige` protege ce texte : la collecte suivante ne le remplacera pas par
l'analyse par regles. C'est exactement ce qui a ete fait pour la seance du
5 septembre 2026, et ce script ne fait que rendre l'operation repetable.

  python scripts/resume.py --liste
      Quelles seances ont un vrai resume, et lesquelles attendent.

  python scripts/resume.py --contexte
      Le dossier complet de la derniere seance sans resume : la seance, ce
      que le plan prevoyait, les allures de reference, les sorties
      precedentes. C'est ce qu'il faut lire pour ecrire l'analyse.

  python scripts/resume.py --pose 2026-09-09 < analyse.json
      Range l'analyse et la fige. Le JSON attendu porte les cles verdict,
      titre, execution, conformite et objectif.

Si un jour le binaire `claude` est installe, la chaine devient automatique
et reste sur l'abonnement :

  python scripts/resume.py --contexte --brut \\
    | claude -p "$(python scripts/resume.py --consigne)" --output-format text \\
    | python scripts/resume.py --pose 2026-09-09
"""

import argparse
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import resume_ia  # noqa: E402

CACHE = os.path.join(ROOT, "docs", "resumes.json")
CLES = ("verdict", "titre", "execution", "conformite", "objectif")


def charge():
    """La calibration n'a pas de fichier a elle : elle voyage dans metrics."""
    m = json.load(io.open(os.path.join(ROOT, "docs", "metrics.json"), encoding="utf-8"))
    p = json.load(io.open(os.path.join(ROOT, "docs", "plan.json"), encoding="utf-8"))
    c = m.get("calibration")
    if not c:
        sys.exit("Pas de calibration dans metrics.json. Lance fetch_data.py.")
    return m, p, c


def resumes():
    try:
        return json.load(io.open(CACHE, encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def ecris(d):
    io.open(CACHE, "w", encoding="utf-8").write(
        json.dumps(d, indent=2, ensure_ascii=False) + "\n")


def courses(metrics):
    return [s for s in metrics.get("seances", []) if s.get("type") != "renfo"]


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--liste", action="store_true")
    ap.add_argument("--contexte", nargs="?", const="", metavar="DATE")
    ap.add_argument("--consigne", action="store_true",
                    help="la consigne de redaction, telle quelle")
    ap.add_argument("--pose", metavar="DATE", help="lire le JSON sur l'entree standard")
    args = ap.parse_args()

    if args.consigne:
        print(resume_ia.SYSTEME)
        return

    metrics, plan, calib = charge()
    S = courses(metrics)
    R = resumes()

    if args.liste or not (args.contexte is not None or args.pose):
        if not S:
            sys.exit("Aucune course dans metrics.json.")
        print("%-12s %-9s %-22s %s" % ("date", "km", "source du resume", "titre"))
        for s in S:
            r = R.get(s["date"]) or {}
            src = r.get("source") or "aucun"
            marque = " (figé)" if r.get("fige") else ""
            print("%-12s %-9s %-22s %s"
                  % (s["date"], "%.2f" % (s.get("km") or 0), src + marque,
                     (r.get("titre") or "")[:44]))
        manque = [s["date"] for s in S
                  if (R.get(s["date"], {}).get("source") not in
                      ("claude", "claude_conversation"))]
        print()
        print("%d séance(s) sans analyse rédigée." % len(manque))
        if manque:
            print("  La plus récente : %s" % manque[-1])
            print("  python scripts/resume.py --contexte %s" % manque[-1])
        return

    if args.contexte is not None:
        date = args.contexte
        if not date:
            reste = [s for s in S
                     if (R.get(s["date"], {}).get("source") not in
                         ("claude", "claude_conversation"))]
            if not reste:
                print("Toutes les séances ont déjà une analyse rédigée.")
                return
            date = reste[-1]["date"]
        i = next((k for k, s in enumerate(S) if s["date"] == date), None)
        if i is None:
            sys.exit("Aucune course le %s." % date)
        c = resume_ia.contexte(S[i], plan, calib, S[:i])
        print(json.dumps(c, ensure_ascii=False, indent=1))
        return

    if args.pose:
        brut = sys.stdin.read().strip()
        d, f = brut.find("{"), brut.rfind("}")
        if d < 0 or f < d:
            sys.exit("Aucun objet JSON sur l'entrée standard.")
        try:
            out = json.loads(brut[d:f + 1])
        except json.JSONDecodeError as e:
            sys.exit("JSON illisible : %s" % e)
        absentes = [k for k in CLES if k not in out]
        if absentes:
            sys.exit("Clés manquantes : %s" % ", ".join(absentes))
        # Le tiret cadratin est interdit dans tout le projet, y compris dans un
        # texte redige par un modele : on refuse plutot que de le laisser passer.
        for k in CLES:
            if isinstance(out[k], str) and ("—" in out[k] or "–" in out[k]):
                sys.exit("Le champ %s contient un tiret cadratin ou "
                         "demi-cadratin." % k)
        out["source"] = "claude_conversation"
        out["fige"] = True
        out.setdefault("date_redaction",
                       __import__("datetime").date.today().isoformat())
        R[args.pose] = out
        ecris(R)

        # docs/resumes.json est le cache que lit la collecte ; la page, elle,
        # lit metrics.json. Sans ce second report, le resume n'apparaitrait
        # qu'apres le prochain fetch_data, donc apres un aller-retour reseau
        # inutile. La collecte suivante le gardera de toute facon : `fige` la
        # empeche de le remplacer.
        mp = os.path.join(ROOT, "docs", "metrics.json")
        metrics["resumes"] = dict(metrics.get("resumes") or {}, **{args.pose: out})
        io.open(mp, "w", encoding="utf-8").write(
            json.dumps(metrics, ensure_ascii=False, separators=(",", ":")))

        print("Résumé du %s enregistré et figé." % args.pose)
        print("Reconstruis la page : python scripts/build_site.py")


if __name__ == "__main__":
    main()
