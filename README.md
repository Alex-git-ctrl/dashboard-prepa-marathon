# Sub-4 à Barcelone

Tableau de bord de préparation au Zurich Marató de Barcelona du 14 mars 2027.
Objectif : terminer sous 4 heures.

**Le tableau de bord :** https://alex-git-ctrl.github.io/dashboard-prepa-marathon/

## Comment ça marche

```
Forerunner 265 + HRM-Pro Plus
        ↓  synchronisation native
   Garmin Connect
        ↓  partenariat officiel, moins de 5 minutes
   Intervals.icu          ← source unique de vérité
        ↓  API HTTP, une clé
  GitHub Actions, tous les jours à 7h
        ↓
  Page statique sur GitHub Pages
```

## Les scripts

| Script | Rôle |
|---|---|
| `scripts/inventory.py` | Diagnostic : liste les champs réellement disponibles |
| `scripts/fetch_data.py` | Extraction et calculs, écrit `docs/metrics.json` |
| `scripts/build_plan.py` | Génère le plan 27 semaines, écrit `docs/plan.json` |
| `scripts/build_site.py` | Assemble le gabarit et les données dans `docs/index.html` |

## En local

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt
cp .env.example .env        # puis remplir les deux valeurs
.venv/Scripts/python scripts/fetch_data.py
.venv/Scripts/python scripts/build_site.py
```

## Confidentialité

Ce dépôt est public. Deux garde-fous :

- `.env` et `data/raw/` sont exclus par `.gitignore` : ni la clé API, ni les
  fichiers bruts ne partent sur GitHub.
- `docs/metrics.json` ne contient que des agrégats. **Aucune coordonnée GPS,
  aucune trace, aucun nom de lieu** n'est publié.
