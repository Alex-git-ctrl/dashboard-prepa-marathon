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
se declenche a l'ouverture de session et rattrape les jours ou la machine
etait eteinte :

  schtasks /Create /TN "Sub4 marathon" /TR "\\"%LOCALAPPDATA%\\..\\..\\
    OneDrive\\Documents\\Claude\\Projects\\Sport\\scripts\\maj_locale.cmd\\""
    /SC DAILY /ST 20:00 /F

Le fichier maj_locale.cmd, a cote, fait le meme travail en un double-clic.
"""

import argparse
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable


def etape(titre, cmd, obligatoire=True, cwd=ROOT):
    """Une etape de l'enchainement. Renvoie True si elle a abouti."""
    # flush explicite : sans lui, la sortie du parent est mise en tampon quand
    # elle ne va pas vers un terminal, et le journal d'une tache planifiee
    # affiche les etapes APRES le texte des commandes qu'elles lancent.
    print("\n== %s" % titre, flush=True)
    t0 = time.time()
    r = subprocess.run(cmd, cwd=cwd)
    d = time.time() - t0
    if r.returncode == 0:
        print("   ok en %.0f s" % d, flush=True)
        return True
    if obligatoire:
        sys.exit("   echec (code %d). On s'arrete ici." % r.returncode)
    print("   ignoree (code %d)." % r.returncode, flush=True)
    return False


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
    etape("Rediger les analyses manquantes",
          [PY, "scripts/resume.py", "--auto"], obligatoire=False)

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
        print("   echec de la publication :")
        print("   " + (p.stderr or "").strip()[:300])
        print("   Le commit est fait. Relance : git pull --rebase && git push")
        return
    print("   publie. La page sera en ligne dans une minute environ.")


if __name__ == "__main__":
    main()
