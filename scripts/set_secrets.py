"""Envoie les valeurs du .env local vers les secrets GitHub du depot.

Les valeurs transitent par gh sans jamais etre affichees.
Prerequis : `gh auth login` deja fait.
Usage : python scripts/set_secrets.py
"""
import os
import subprocess
import sys

from dotenv import load_dotenv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(ROOT, ".env"))

for nom in ("INTERVALS_API_KEY", "INTERVALS_ATHLETE_ID"):
    val = os.getenv(nom, "").strip()
    if not val:
        sys.exit(f"{nom} absent du .env")
    r = subprocess.run(["gh", "secret", "set", nom, "--body", val],
                       cwd=ROOT, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"Echec sur {nom} : {r.stderr.strip()}")
    print(f"{nom} : envoye ({len(val)} caracteres, valeur non affichee)")

print("\nLes deux secrets sont en place. Le job quotidien peut tourner.")
