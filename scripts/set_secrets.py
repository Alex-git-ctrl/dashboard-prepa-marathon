"""Envoie les valeurs du .env local vers les secrets GitHub du depot.

Les valeurs transitent par gh sans jamais etre affichees.
Prerequis : `gh auth login` deja fait.
Usage : python scripts/set_secrets.py

Les deux cles Intervals.icu sont obligatoires : sans elles, la collecte ne
tourne pas. La cle de l'API personnelle Garmin est facultative : absente du
.env, elle est simplement ignoree, et la collecte s'en passe.
"""
import os
import subprocess
import sys

from dotenv import load_dotenv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(ROOT, ".env"))

OBLIGATOIRES = ("INTERVALS_API_KEY", "INTERVALS_ATHLETE_ID")
FACULTATIFS = ("GARMIN_PERSONAL_API_KEY",)


def envoie(nom, val):
    r = subprocess.run(["gh", "secret", "set", nom, "--body", val],
                       cwd=ROOT, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"Echec sur {nom} : {r.stderr.strip()}")
    print(f"{nom} : envoye ({len(val)} caracteres, valeur non affichee)")


for nom in OBLIGATOIRES:
    val = os.getenv(nom, "").strip()
    if not val:
        sys.exit(f"{nom} absent du .env")
    envoie(nom, val)

for nom in FACULTATIFS:
    val = os.getenv(nom, "").strip()
    if val:
        envoie(nom, val)
    else:
        print(f"{nom} : absent du .env, ignore (facultatif)")

print("\nLes secrets sont en place. Le job quotidien peut tourner.")
