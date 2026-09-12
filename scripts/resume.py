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

  python scripts/resume.py --auto
      La chaine complete, en une commande, pour toutes les seances qui
      attendent. Elle passe par le binaire `claude`, c'est-a-dire Claude
      Code, qui tourne sur l'ABONNEMENT et non sur l'API facturee.
      L'installer ne coute rien :

          npm i -g @anthropic-ai/claude-code

      Il reutilise la session deja ouverte dans ~/.claude : ni nouvelle
      connexion, ni cle API. Ce mode ne peut pas tourner dans GitHub
      Actions, qui n'a pas cette session : les resumes restent une
      operation locale, ce qui convient a leur rythme reel, trois ou
      quatre par semaine.
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


def binaire_claude():
    """Le chemin du VRAI binaire Claude Code, pas du lanceur .cmd.

    Sous Windows, npm installe un shim claude.CMD a cote du binaire. Ce shim
    passe par cmd.exe, qui redecoupe les arguments sur les espaces : un long
    JSON arrivait vide, et --system-prompt "Reponds uniquement par OK"
    arrivait comme le seul mot "uniquement". On cherche donc l'executable
    reel d'abord, et le shim seulement en dernier recours.
    """
    import shutil, subprocess
    # Le chemin pose par npm, le plus direct.
    try:
        racine = subprocess.run(["npm", "root", "-g"], capture_output=True,
                                text=True, timeout=30, shell=(os.name == "nt"))
        if racine.returncode == 0:
            exe = os.path.join(racine.stdout.strip(), "@anthropic-ai",
                               "claude-code", "bin",
                               "claude.exe" if os.name == "nt" else "claude")
            if os.path.exists(exe):
                return exe
    except (OSError, subprocess.SubprocessError):
        pass
    for nom in ("claude.exe", "claude"):
        chemin = shutil.which(nom)
        # Un .cmd ou .bat est un shim : il casserait les arguments.
        if chemin and not chemin.lower().endswith((".cmd", ".bat")):
            return chemin
    return shutil.which("claude")


def redige_avec(cible, systeme, contenu):
    """Fait ecrire un texte par Claude Code, donc sur l'abonnement.

    Trois precautions, toutes apprises du premier essai rate.

    --system-prompt REMPLACE le prompt par defaut. Sans lui, Claude Code
    reste un assistant de code : il a repondu en Markdown, avec des titres,
    apres etre alle lire le depot de lui-meme.

    Le repertoire de travail est un dossier vide et temporaire. Claude Code
    est un agent : lance dans le depot, il explore, lit CLAUDE.md, et se met
    a raisonner sur le projet au lieu du dossier qu'on lui donne. Dans un
    dossier vide, il n'a rien a trouver.

    Enfin on ne garde que -p et --output-format text, les deux drapeaux les
    plus stables.
    """
    import subprocess, tempfile, shutil
    bac = tempfile.mkdtemp(prefix="claude-")
    try:
        r = subprocess.run(
            [cible, "-p", contenu, "--system-prompt", systeme,
             "--output-format", "text"],
            cwd=bac, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=300)
    except subprocess.TimeoutExpired:
        return None, "pas de reponse en 5 minutes"
    finally:
        shutil.rmtree(bac, ignore_errors=True)
    if r.returncode != 0:
        return None, (r.stderr or r.stdout or "").strip()[:300]
    sortie = (r.stdout or "").strip()
    d, f = sortie.find("{"), sortie.rfind("}")
    if d < 0 or f < d:
        return None, "aucun objet JSON dans la reponse : " + sortie[:160]
    try:
        return json.loads(sortie[d:f + 1]), None
    except json.JSONDecodeError as e:
        return None, "JSON illisible : %s" % e


def redige(cible, contexte_json):
    """Le cas particulier du resume de seance."""
    return redige_avec(cible, resume_ia.SYSTEME,
                       "Voici la seance a analyser.\n\n" + contexte_json)


# Les sequences que produit un texte UTF-8 relu comme du cp1252. Si l'une
# d'elles apparait, le texte est deja abime et il ne faut pas l'ecrire.
MOJIBAKE = ("\u00c3\u00a9", "\u00c3\u00a8", "\u00c3\u00a0", "\u00c3\u00aa",
            "\u00e2\u20ac", "\u00c3\u00a7", "\u00c5\u0093")


def normalise(out, cles):
    """Repare l'espace avant les deux-points, que le modele oublie parfois.

    Le francais demande une espace devant : ; ! ?. On ne touche QUE le cas
    lettre suivie de deux-points suivie d'une espace : ca laisse tranquilles
    les heures (16:56) et les allures (5:41/km), ou ce serait faux.
    """
    import re
    motif = re.compile(r"(?<=[a-zA-Zà-ÿÀ-ÿ])([:;!?])(?= )")
    for k in cles:
        if isinstance(out.get(k), str):
            out[k] = motif.sub(" \\1", out[k])
    return out


def valide_texte(out, cles):
    """Aucun cadratin, aucun accent casse, dans les champs indiques."""
    for k in cles:
        v = out.get(k)
        if not isinstance(v, str):
            continue
        if "—" in v or "–" in v:
            return "le champ %s contient un tiret cadratin" % k
        for m in MOJIBAKE:
            if m in v:
                return ("le champ %s contient des accents casses (%r) : le "
                        "texte n'a pas ete lu en UTF-8" % (k, m))
    return None


def valide(out):
    """Cles presentes, aucun cadratin, aucun accent casse."""
    absentes = [k for k in CLES if k not in out]
    if absentes:
        return "cles manquantes : " + ", ".join(absentes)
    return valide_texte(out, CLES)


def range_resume(date, out, R, metrics):
    """Ecrit le resume dans le cache ET dans metrics.json, et le fige.

    docs/resumes.json est le cache que lit la collecte ; la page, elle, lit
    metrics.json. Sans ce second report, le resume n'apparaitrait qu'apres le
    prochain fetch_data, donc apres un aller-retour reseau inutile. La
    collecte suivante le gardera de toute facon : fige l'en empeche.
    """
    import datetime
    out["source"] = "claude_conversation"
    out["fige"] = True
    out.setdefault("date_redaction", datetime.date.today().isoformat())
    R[date] = out
    ecris(R)
    metrics["resumes"] = dict(metrics.get("resumes") or {}, **{date: out})
    io.open(os.path.join(ROOT, "docs", "metrics.json"), "w",
            encoding="utf-8").write(
        json.dumps(metrics, ensure_ascii=False, separators=(",", ":")))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--liste", action="store_true")
    ap.add_argument("--contexte", nargs="?", const="", metavar="DATE")
    ap.add_argument("--consigne", action="store_true",
                    help="la consigne de redaction, telle quelle")
    ap.add_argument("--pose", metavar="DATE", help="lire le JSON sur l'entree standard")
    ap.add_argument("--auto", nargs="?", const="", metavar="DATE",
                    help="rediger via le binaire claude, sur l'abonnement")
    args = ap.parse_args()

    if args.consigne:
        print(resume_ia.SYSTEME)
        return

    metrics, plan, calib = charge()
    S = courses(metrics)
    R = resumes()

    if args.liste or not (args.contexte is not None or args.pose
                          or args.auto is not None):
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

    if args.auto is not None:
        cible = binaire_claude()
        if not cible:
            print("Le binaire claude n'est pas installe.")
            print()
            print("  npm i -g @anthropic-ai/claude-code")
            print()
            print("Il ne coute rien et reutilise la session deja ouverte dans")
            print("~/.claude : ni nouvelle connexion, ni cle API. C'est Claude")
            print("Code, donc l'abonnement, pas l'API facturee au token.")
            sys.exit(1)
        a_faire = ([x for x in S if x["date"] == args.auto] if args.auto else
                   [x for x in S
                    if (R.get(x["date"], {}).get("source") not in
                        ("claude", "claude_conversation"))])
        if not a_faire:
            print("Rien a rediger : toutes les seances ont deja une analyse.")
            return
        print("%s" % cible)
        print("%d seance(s) a rediger." % len(a_faire))
        faits = 0
        for seance in a_faire:
            i = next(k for k, x in enumerate(S) if x["date"] == seance["date"])
            c = resume_ia.contexte(S[i], plan, calib, S[:i])
            print("  %s ..." % seance["date"], end=" ", flush=True)
            out, err = redige(cible, json.dumps(c, ensure_ascii=False, indent=1))
            if out is None:
                print("echec (%s)" % err)
                continue
            normalise(out, CLES)
            souci = valide(out)
            if souci:
                print("refuse (%s)" % souci)
                continue
            range_resume(seance["date"], out, R, metrics)
            faits += 1
            print("%s | %s" % (out.get("verdict", "?"), out.get("titre", "")))
        print()
        print("%d resume(s) redige(s) et fige(s)." % faits)
        if faits:
            print("Reconstruis la page : python scripts/build_site.py")
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
        # sys.stdin.read() decode avec l'encodage de la LOCALE, cp1252 sous
        # Windows. Un texte francais en UTF-8 y perd tous ses accents en
        # silence : "reference" devenait "rA©fA©rence", et le controle du
        # tiret cadratin ne voyait plus rien parce que le cadratin arrivait
        # decoupe en trois caracteres. On decode donc explicitement.
        try:
            brut = io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8",
                                    errors="strict").read().strip()
        except UnicodeDecodeError as e:
            sys.exit("L'entrée n'est pas de l'UTF-8 valide : %s" % e)
        d, f = brut.find("{"), brut.rfind("}")
        if d < 0 or f < d:
            sys.exit("Aucun objet JSON sur l'entrée standard.")
        try:
            out = json.loads(brut[d:f + 1])
        except json.JSONDecodeError as e:
            sys.exit("JSON illisible : %s" % e)
        normalise(out, CLES)
        souci = valide(out)
        if souci:
            sys.exit(souci)
        range_resume(args.pose, out, R, metrics)

        print("Résumé du %s enregistré et figé." % args.pose)
        print("Reconstruis la page : python scripts/build_site.py")


if __name__ == "__main__":
    main()
