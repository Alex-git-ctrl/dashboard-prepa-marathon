"""Assemble plan.json + metrics.json dans docs/index.html, page autonome."""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "docs")


def inline(name):
    with open(os.path.join(D, name), encoding="utf-8") as fh:
        return json.dumps(json.load(fh), ensure_ascii=False, separators=(",", ":"))


with open(os.path.join(D, "_template.html"), encoding="utf-8") as fh:
    html = fh.read()

for token, src in (("__PLAN__", "plan.json"), ("__METRICS__", "metrics.json")):
    if token not in html:
        raise SystemExit(f"Placeholder {token} absent du gabarit.")
    html = html.replace(token, inline(src))

# Deux sorties pour deux destinations :
#  - docs/artifact.html : contenu seul, l'artifact Claude fournit son propre
#    squelette et le rejetterait en double.
#  - docs/index.html : document complet, car GitHub Pages sert le fichier tel
#    quel. Sans doctype ni viewport, un telephone suppose un ecran de 980 px
#    et reduit toute la page.
with open(os.path.join(D, "artifact.html"), "w", encoding="utf-8") as fh:
    fh.write(html)

SQUELETTE = """<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#F2F3F1">
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

# Ce qui doit remonter dans le <head> : titre, description, polices, styles.
coupe = html.index("<div") if "<div" in html else html.index("<header")
tete, corps = html[:coupe].strip(), html[coupe:].strip()

with open(os.path.join(D, "index.html"), "w", encoding="utf-8") as fh:
    fh.write(SQUELETTE.format(tete=tete, corps=corps))

print(f"docs/index.html   : document complet, {len(SQUELETTE) + len(html):,} octets")
print(f"docs/artifact.html: contenu seul, {len(html):,} octets")
