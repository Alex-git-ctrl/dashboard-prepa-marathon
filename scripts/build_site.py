"""Assemble le gabarit, les donnees et un THEME dans docs/index.html.

Le gabarit ne contient plus de style. Il porte la structure, le comportement,
et trois emplacements : __THEME__, __PLAN__ et __METRICS__. La presentation
vit dans docs/themes/<nom>.css, avec un <nom>.json a cote qui declare son
titre, ses polices et ses couleurs de barre systeme.

Changer d'apparence n'est donc pas une reecriture, c'est un argument :

  python scripts/build_site.py --theme apple     # bascule et memorise
  python scripts/build_site.py --theme releve    # retour en arriere
  python scripts/build_site.py --liste           # ce qui existe
  python scripts/build_site.py                   # reprend le theme memorise

Le theme choisi est ecrit dans docs/themes/actif.txt, donc la collecte
automatique qui tourne deux fois par jour rebatit la page dans le dernier
theme demande, sans avoir a toucher au workflow.

LE CONTRAT. Un theme est libre de tout redessiner, a une condition : il doit
definir les tokens que le JavaScript lit pour peindre les graphiques. Ils sont
listes dans TOKENS_EXIGES et verifies a chaque construction, parce qu'un token
manquant ne casse rien de visible : il donne juste une courbe invisible ou
noire, ce qui se remarque beaucoup trop tard.
"""

import argparse
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "docs")
THEMES = os.path.join(D, "themes")
ACTIF = os.path.join(THEMES, "actif.txt")

# Les 27 tokens que le JavaScript va chercher avec var(). Un theme qui en
# oublie un dessine un graphique sans couleur.
TOKENS_EXIGES = [
    "--acier", "--alerte", "--b1", "--b2", "--b3", "--b4", "--b5", "--craie",
    "--creux", "--effort", "--encre", "--m-allure", "--m-alt", "--m-fc",
    "--m-puissance", "--mesure", "--ok", "--s4", "--s5", "--sur-bitume-faible",
    "--veille", "--volt", "--z1", "--z2", "--z3", "--z4", "--z5",
]


def inline(name):
    with open(os.path.join(D, name), encoding="utf-8") as fh:
        return json.dumps(json.load(fh), ensure_ascii=False, separators=(",", ":"))


def themes_dispo():
    if not os.path.isdir(THEMES):
        return []
    return sorted(f[:-4] for f in os.listdir(THEMES) if f.endswith(".css"))


def lis_actif():
    try:
        with open(ACTIF, encoding="utf-8") as fh:
            nom = fh.read().strip()
        return nom or None
    except OSError:
        return None


def charge_theme(nom):
    css_p = os.path.join(THEMES, nom + ".css")
    json_p = os.path.join(THEMES, nom + ".json")
    if not os.path.exists(css_p):
        sys.exit("Theme inconnu : %s. Disponibles : %s"
                 % (nom, ", ".join(themes_dispo()) or "aucun"))
    with open(css_p, encoding="utf-8") as fh:
        css = fh.read()
    meta = {}
    if os.path.exists(json_p):
        with open(json_p, encoding="utf-8") as fh:
            meta = json.load(fh)

    # Les commentaires peuvent contenir un exemple de token : on les retire
    # avant de verifier, sinon un theme passe le controle sans rien definir.
    net = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    definis = set(re.findall(r"(--[a-z0-9-]+)\s*:", net))
    absents = [t for t in TOKENS_EXIGES if t not in definis]
    if absents:
        sys.exit("Le theme %s ne definit pas : %s\n"
                 "Ces tokens sont lus par le JavaScript pour peindre les "
                 "graphiques." % (nom, ", ".join(absents)))
    return css, meta


def tete_theme(css, meta):
    """Le bloc de presentation complet : polices puis feuille de style."""
    out = []
    if meta.get("polices"):
        out.append('<link rel="preconnect" href="https://fonts.googleapis.com">')
        out.append('<link rel="preconnect" href="https://fonts.gstatic.com" '
                   'crossorigin>')
        out.append('<link rel="stylesheet" href="%s">' % meta["polices"])
    out.append("<style>\n%s\n</style>" % css.strip())
    return "\n".join(out)


def metas_couleur(meta):
    """La couleur de la barre systeme du telephone, par mode.

    Un theme sans mode sombre declare theme_color_sombre a null : on n'emet
    alors qu'une seule balise, sinon le telephone teinterait sa barre en sombre
    au-dessus d'une page restee blanche.
    """
    clair = meta.get("theme_color_clair") or "#ffffff"
    sombre = meta.get("theme_color_sombre")
    if not sombre:
        return ('<meta name="theme-color" content="%s">\n'
                '<meta name="color-scheme" content="light">' % clair)
    return ('<meta name="theme-color" content="%s" '
            'media="(prefers-color-scheme: light)">\n'
            '<meta name="theme-color" content="%s" '
            'media="(prefers-color-scheme: dark)">' % (clair, sombre))


SQUELETTE = """<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
{couleurs}
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="apple-mobile-web-app-title" content="Sub-4">
{tete}
</head>
<body>
{corps}
</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--theme", help="theme a appliquer, et a memoriser")
    ap.add_argument("--liste", action="store_true",
                    help="lister les themes disponibles et sortir")
    args = ap.parse_args()

    dispo = themes_dispo()
    if args.liste:
        actif = lis_actif()
        for n in dispo:
            _, meta = charge_theme(n)
            print("%s %-10s %s" % ("*" if n == actif else " ", n,
                                   meta.get("nom", "")))
            if meta.get("resume"):
                print("             %s" % meta["resume"])
        return

    nom = args.theme or lis_actif() or (dispo[0] if dispo else None)
    if not nom:
        sys.exit("Aucun theme dans docs/themes/.")
    css, meta = charge_theme(nom)
    if args.theme:
        with open(ACTIF, "w", encoding="utf-8") as fh:
            fh.write(nom + "\n")

    with open(os.path.join(D, "_template.html"), encoding="utf-8") as fh:
        html = fh.read()

    for token, valeur in (("__THEME__", tete_theme(css, meta)),
                          ("__PLAN__", None), ("__METRICS__", None)):
        if token not in html:
            raise SystemExit("Placeholder %s absent du gabarit." % token)
    html = html.replace("__THEME__", tete_theme(css, meta))
    for token, src in (("__PLAN__", "plan.json"), ("__METRICS__", "metrics.json")):
        html = html.replace(token, inline(src))

    # Deux sorties pour deux destinations :
    #  - docs/artifact.html : contenu seul, l'artifact Claude fournit son propre
    #    squelette et le rejetterait en double.
    #  - docs/index.html : document complet, car GitHub Pages sert le fichier tel
    #    quel. Sans doctype ni viewport, un telephone suppose un ecran de 980 px
    #    et reduit toute la page.
    with open(os.path.join(D, "artifact.html"), "w", encoding="utf-8") as fh:
        fh.write(html)

    coupe = html.index("<header")
    tete, corps = html[:coupe].strip(), html[coupe:].strip()
    doc = SQUELETTE.format(couleurs=metas_couleur(meta), tete=tete, corps=corps)
    with open(os.path.join(D, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(doc)

    print("theme             : %s (%s)" % (nom, meta.get("nom", nom)))
    print("docs/index.html   : document complet, %d octets" % len(doc))
    print("docs/artifact.html: contenu seul, %d octets" % len(html))


if __name__ == "__main__":
    main()
