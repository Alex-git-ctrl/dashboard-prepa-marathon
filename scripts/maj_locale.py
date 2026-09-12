"""La mise a jour complete, depuis CETTE machine, sans clef API.

Pourquoi ce script existe. La collecte tourne deja dans GitHub Actions deux
fois par jour, gratuitement, parce que le depot est public. Mais Actions n'a
pas la session Claude de cette machine : la seule facon d'y faire rediger une
analyse serait d'y poser une clef API, qui se facture au token.

Ici, la session existe. Le meme enchainement tourne donc en local et les
resumes sont ecrits par Claude Code, c'est-a-dire par l'abonnement. La
difference avec Actions n'est pas le prix, c'est le moment : la page se met a
jour quand l'ordinateur est allume, pas a heure fixe.

  python scripts/maj_locale.py             # tout l'enchainement
  python scripts/maj_locale.py --sans-git  # sans publier
  python scripts/maj_locale.py --resumes   # seulement les analyses

Pour le rendre automatique, une tache planifiee suffit. La forme ci-dessous
tourne tous les soirs a 23h :

  schtasks /Create /TN "Sub4 marathon" /TR "\\"%LOCALAPPDATA%\\..\\..\\
    OneDrive\\Documents\\Claude\\Projects\\Sport\\scripts\\maj_locale.cmd\\""
    /SC DAILY /ST 23:00 /F

Le fichier maj_locale.cmd, a cote, fait le meme travail en un double-clic.
"""

import argparse
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable


JOURNAL = []
# Combien d'analyses redigees avant et apres l'etape de redaction. Compter
# l'ETAPE ne dit rien : elle reussit aussi quand il n'y avait rien a ecrire,
# et la page annoncait alors "1 analyse redigee" sur un passage a vide.
ANALYSES = {}


def compte_analyses():
    """Le nombre de seances portant une analyse redigee, pas mecanique."""
    import json
    try:
        with open(os.path.join(ROOT, "docs", "resumes.json"),
                  encoding="utf-8") as fh:
            return sum(1 for v in json.load(fh).values()
                       if v.get("source") in ("claude", "claude_conversation"))
    except (OSError, ValueError):
        return 0


def etape(titre, cmd, obligatoire=True, cwd=ROOT):
    """Une etape de l'enchainement. Renvoie True si elle a abouti.

    Chaque passage laisse une trace dans JOURNAL : sans ca, une tache qui
    tourne a 23h pendant qu'on dort ne dit jamais ce qu'elle a fait, ni si
    elle a seulement tourne.
    """
    # flush explicite : sans lui, la sortie du parent est mise en tampon quand
    # elle ne va pas vers un terminal, et le journal d'une tache planifiee
    # affiche les etapes APRES le texte des commandes qu'elles lancent.
    print("\n== %s" % titre, flush=True)
    t0 = time.time()
    r = subprocess.run(cmd, cwd=cwd)
    d = time.time() - t0
    JOURNAL.append({"etape": titre, "secondes": round(d, 1),
                    "ok": r.returncode == 0, "code": r.returncode})
    if r.returncode == 0:
        print("   ok en %.0f s" % d, flush=True)
        return True
    if obligatoire:
        ecris_journal("echec", titre)
        sys.exit("   echec (code %d). On s'arrete ici." % r.returncode)
    print("   ignoree (code %d)." % r.returncode, flush=True)
    return False


def ecris_journal(etat, detail=None):
    """Range le compte rendu dans metrics.json, que la page inline au build.

    Un fichier a part obligerait a inventer un troisieme emplacement dans le
    gabarit. metrics.json est deja transporte jusqu'a la page : le compte
    rendu voyage avec.
    """
    import json
    from datetime import datetime
    chemin = os.path.join(ROOT, "docs", "metrics.json")
    try:
        with open(chemin, encoding="utf-8") as fh:
            m = json.load(fh)
    except (OSError, ValueError):
        return
    redigees = ANALYSES.get("apres", 0) - ANALYSES.get("avant", 0)
    m["maj_locale"] = {
        "quand": datetime.now().isoformat(timespec="seconds"),
        "etat": etat,
        "detail": detail,
        "secondes": round(sum(e["secondes"] for e in JOURNAL), 1),
        "analyses_redigees": redigees,
        "etapes": JOURNAL,
    }
    with open(chemin, "w", encoding="utf-8") as fh:
        json.dump(m, fh, ensure_ascii=False, separators=(",", ":"))


def git(*args):
    return subprocess.run(["git"] + list(args), cwd=ROOT,
                          capture_output=True, text=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sans-git", action="store_true",
                    help="ne pas publier le resultat")
    ap.add_argument("--resumes", action="store_true",
                    help="seulement les analyses, sans recollecter")
    args = ap.parse_args()

    print("Mise a jour locale du tableau de bord")
    print("Depot :", ROOT, flush=True)

    # La collecte automatique pousse ses propres commits. Sans ce rattrapage,
    # la publication d'en bas serait rejetee et le travail serait perdu.
    if not args.sans_git:
        propre = not git("status", "--porcelain").stdout.strip()
        if propre:
            etape("Rattraper la collecte automatique",
                  ["git", "pull", "--rebase", "--quiet"], obligatoire=False)
        else:
            print()
            print("== Rattraper la collecte automatique")
            print("   sautee : des modifications locales attendent d'etre "
                  "validees.")

    if not args.resumes:
        etape("Collecter les donnees Intervals.icu",
              [PY, "scripts/fetch_data.py"])
        etape("Recalculer le plan", [PY, "scripts/build_plan.py"])

    # La seule etape qui a besoin de la session Claude de cette machine. Si le
    # binaire manque, le script le dit et l'enchainement continue : une page
    # sans analyse redigee vaut mieux qu'une page pas reconstruite.
    ANALYSES["avant"] = compte_analyses()
    etape("Rediger les analyses manquantes",
          [PY, "scripts/resume.py", "--auto"], obligatoire=False)
    ANALYSES["apres"] = compte_analyses()

    # Avant la reconstruction : la page inline metrics.json, donc le compte
    # rendu doit y etre AVANT que build_site ne la fabrique.
    ecris_journal("ok")
    etape("Reconstruire la page", [PY, "scripts/build_site.py"])

    if args.sans_git:
        print()
        print("Termine. Rien n'a ete publie (--sans-git).")
        return

    change = git("status", "--porcelain", "docs/").stdout.strip()
    if not change:
        print()
        print("Termine. Rien n'a change, rien a publier.")
        return

    print()
    print("== Publier")
    git("add", "docs/")
    from datetime import date
    msg = "Mise a jour locale du %s" % date.today().strftime("%d/%m/%Y")
    c = git("commit", "--quiet", "-m", msg)
    if c.returncode != 0:
        print("   rien a valider.")
        return
    p = git("push", "--quiet")
    if p.returncode != 0:
        # La collecte automatique peut avoir pousse entre le rattrapage du
        # debut et maintenant. Un rejet n'est donc pas une erreur, c'est une
        # course : on se remet a jour et on retente une fois.
        print("   rejete, la collecte automatique est passee entre-temps.")
        r = git("pull", "--rebase", "--quiet")
        if r.returncode != 0:
            print("   rattrapage impossible :")
            print("   " + (r.stderr or "").strip()[:300])
            print("   Le commit est fait, rien n'est perdu.")
            return
        # Le rebase rejoue notre commit sur des donnees plus fraiches : la
        # page doit etre refaite avant d'etre publiee.
        subprocess.run([PY, "scripts/build_site.py"], cwd=ROOT,
                       capture_output=True)
        if git("status", "--porcelain", "docs/").stdout.strip():
            git("add", "docs/")
            git("commit", "--quiet", "--amend", "--no-edit")
        p = git("push", "--quiet")
        if p.returncode != 0:
            print("   echec de la publication :")
            print("   " + (p.stderr or "").strip()[:300])
            print("   Le commit est fait. Relance : git pull --rebase && git push")
            return
    print("   publie. La page sera en ligne dans une minute environ.")


if __name__ == "__main__":
    main()
