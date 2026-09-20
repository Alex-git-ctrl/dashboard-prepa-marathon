# Sub-4 à Barcelone : contexte pour Claude Code

Tableau de bord de préparation au marathon. Alex Gourdou court son premier
marathon, le Zurich Marató de Barcelona, dimanche 14 mars 2027, objectif
sous 4h00 (5:41/km). Page publique :
https://alex-git-ctrl.github.io/dashboard-prepa-marathon/

Ce fichier documente ce qui ne se déduit pas du code seul : les décisions,
les dates, les conventions, et le "pourquoi" derrière les choix de conception.
La documentation "pourquoi" vit déjà largement dans les docstrings des
scripts (`scripts/*.py`) — les lire avant de modifier un module, elles sont
denses et à jour.

## §0. Règle absolue : pas de tiret cadratin ni demi-cadratin

Interdit partout dans ce projet : code, contenu généré, commits, ce fichier.
Utiliser un point, deux points, une virgule ou une parenthèse à la place.
Cette règle est appliquée explicitement dans le prompt système envoyé à
Claude pour les résumés de séance (`scripts/resume_ia.py`) et documentée
dans `design/apple-style-reference.md`.

## Le plan

- **10 km** de calibration : samedi 26/09/2026 (semaine 3)
- **Semi-marathon**, Bois de Vincennes (Paris) : samedi 05/12/2026
  (semaine 13) — jalon de décision, c'est lui qui fixe l'allure marathon
  retenue. Initialement prévu le 25/10/2026 (semaine 7), déplacé au
  05/12/2026 le 20/09/2026 : tout le bloc base/construction entre le 10 km
  et le semi a été réétalé en conséquence (voir plus bas).
- **Marathon de Barcelone** : dimanche 14/03/2027 (semaine 27), départ 8h30
  Plaça de Catalunya, parcours plat

27 semaines, 5 blocs (voir `scripts/build_plan.py` pour le détail semaine
par semaine) :
1. S1-13 : Base aérobie, 10 km et semi (base prolongée, travail semi-pace
   introduit en S9-11, taper S12, course S13)
2. S14-16 : Récupération et fondation marathon (1 semaine de récup puis
   reprise du volume avec les zones recalibrées sur le semi)
3. S17-20 : Construction spécifique (allure marathon, seuil, décharge avant
   le bloc suivant)
4. S21-24 : Pic de volume et test 30K (semaine 23 = test clé à allure
   marathon) — inchangé
5. S25-27 : Affûtage — inchangé

Les blocs 4 et 5 (S21-27) n'ont pas bougé : seul l'étalement des blocs 1 à 3
a changé pour absorber le report du semi. La phase de construction
spécifique passe de 8 à 4 semaines (S17-20 au lieu de S13-20) : plus courte
qu'avant, mais elle s'enchaîne directement sur le bloc de pic (S21-24), pour
un total de 8 semaines de travail spécifique + pic avant l'affûtage, ce qui
reste dans la norme d'une préparation marathon.

Contraintes réelles : 3 séances de course/semaine + 2 séances de musculation,
créneaux de semaine en pause déjeuner (40-45 min max), sortie longue le
samedi. Départ : 12 km/sem, 82 kg, référence 10 km en 48 min (estimée, jamais
courue avant le plan).

Le plan écrit à la main (`build_plan.py`) reste la référence d'ambition et
n'est jamais réécrit par l'adaptation automatique (`adaptation.py`) : celle-ci
ajuste au-dessus, sans effacer l'original.

## Calibration et allures : modèle Jack Daniels (`scripts/calibration.py`)

VDOT recalculé à chaque nouvelle course officielle (la plus récente fait foi,
pas la meilleure : c'est la forme actuelle qui compte). Les zones d'allure
(endurance fondamentale, marathon, seuil, 10 km, fractionné court) sont des
fractions de la vitesse à VO2max, pas des valeurs fixes : tout se recalcule
après chaque course. La cible marathon (5:41/km) est une **décision**, pas
une déduction physiologique : elle reste volontairement séparée des zones
calculées (`cible_marathon` vs `zones` dans la sortie de `calcule()`).

## Architecture / pipeline

```
Forerunner 265 + HRM-Pro Plus
        │  synchronisation native
   Garmin Connect
        │  partenariat officiel
   Intervals.icu          ← source unique de vérité
        │  API HTTP (INTERVALS_API_KEY)
  GitHub Actions, ~7h13 et ~21h17 Paris (update.yml)
        │
  docs/metrics.json, docs/plan.json, docs/bilans.json, docs/resumes.json
        │
  scripts/build_site.py → docs/index.html (page complète) + docs/artifact.html (contenu seul)
        │
  GitHub Pages
```

Un second workflow, `export-garmin.yml`, va dans l'autre sens : il pousse les
séances planifiées vers le calendrier Intervals.icu (qui les synchronise vers
Garmin Connect). Il n'est **jamais programmé**, seulement déclenchable à la
main (bouton du dashboard, onglet Actions, ou `gh workflow run`) : écrire sur
le calendrier de quelqu'un doit rester un geste volontaire.

## Carte des scripts (`scripts/`)

| Script | Rôle |
|---|---|
| `inventory.py` | Diagnostic : liste les champs réellement dispo via l'API Intervals.icu, sans rien publier |
| `fetch_data.py` | Extraction Intervals.icu → `docs/metrics.json`, agrégats uniquement, jamais de GPS |
| `calibration.py` | VDOT et zones d'allure, modèle Jack Daniels |
| `build_plan.py` | Génère le plan 27 semaines → `docs/plan.json` |
| `adaptation.py` | Ajuste le plan selon observance + coût, sans écraser l'original ; n'ajuste jamais si les mesures manquent |
| `alerts.py` | Règles d'alerte : charge qui monte trop vite, dérive cardiaque qui stagne, VFC/FC repos qui se dégradent. Renvoie `None` tant que les données sont insuffisantes |
| `bilan.py` | Bilan hebdomadaire général ("où j'en suis, puis-je viser plus haut"). Contexte volontairement borné (27 semaines max, 10 dernières séances, 12 derniers points d'efficacité aérobie) pour que le coût n'explose pas avec l'historique |
| `resume.py` / `resume_ia.py` | Résumé par séance : via Claude (`ANTHROPIC_API_KEY`, modèle `claude-opus-5`) si dispo, sinon repli par règles, toujours étiqueté comme tel sur la page. Résumés cachés sur disque (`docs/resumes.json`), clés sur un hash du contenu de la séance |
| `seance_detail.py` | Détail d'une séance : splits au km, dérive, dynamique de course |
| `seances_type.py` | Décompose une semaine du plan en séances pas-à-pas avec allure cible, exportables vers Garmin |
| `sante.py` | Pas, sommeil, indice de fatigue (calculé comme déviation à la moyenne glissante de VFC/FC repos, pas en valeur absolue) |
| `journal.py` | Écrit le ressenti (RPE, douleur, fatigue) dans Intervals.icu, jamais en local |
| `build_site.py` | Assemble `docs/_template.html` + JSON + thème → `docs/index.html` et `docs/artifact.html` |
| `maj_locale.py` | Même enchaînement qu'Actions mais en local, pour que les résumés soient rédigés par Claude Code (abonnement) plutôt que par une clé API facturée au token |
| `export_garmin.py` | Pousse les séances planifiées vers Garmin via Intervals.icu ; ne supprime que ce qu'il a lui-même posé (suivi dans `docs/export_garmin.json`) |
| `set_secrets.py` | Envoie `.env` vers les secrets GitHub via `gh` |

## Fichiers de données (`docs/`)

- `metrics.json` : seul fichier "brut" publié, agrégats et séries temporelles, **jamais de GPS ni de nom de lieu**
- `plan.json` : sortie de `build_plan.py`
- `bilans.json` : historique des bilans hebdomadaires (append-only)
- `resumes.json` : cache des résumés de séance, clé = hash du contenu
- `export_garmin.json` : IDs des événements posés sur le calendrier Garmin, pour pouvoir les remplacer sans dupliquer
- `_template.html` : le gabarit source, avec placeholders `__THEME__`, `__PLAN__`, `__METRICS__` — **c'est ce fichier qu'on édite**, pas `index.html` ni `artifact.html` qui sont générés
- `index.html` : page complète générée par `build_site.py`
- `artifact.html` : même contenu, sans `<html>`/`<head>`/`<body>`, pensé pour être publié comme Claude Artifact
- `themes/<nom>.css` + `<nom>.json` : un thème = une palette/typo, jamais une réécriture de structure. Thèmes existants : `apple` (actif), `releve`, `sante`. Le thème actif est mémorisé dans `themes/actif.txt`

## Conventions et pièges connus

- **Encodage** : sur console Windows (cp1252), `build_plan.py` fait un
  `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` sinon le
  récapitulatif final plante sur les accents après avoir quand même écrit le
  JSON — l'erreur donne l'impression à tort que la génération a échoué.
- **Français correct dans le contenu généré** : virgule décimale, pas de
  point (`resume_ia.py:_fr`). Toujours des accents complets, jamais de
  translittération.
- **Honnêteté avant tout** dans `adaptation.py` et `alerts.py` : quand les
  données manquent, on ne décide pas et on ne signale pas — on suit le plan
  d'origine et on le dit, plutôt que d'extrapoler.
- **Contexte borné** dans `bilan.py` : ne jamais envoyer un historique qui
  grossit sans limite vers un modèle ou un calcul, plafonner explicitement.
- **Confidentialité** : `.env` et `data/raw/` sont dans `.gitignore` (le
  dépôt est public). Ne jamais faire fuiter de coordonnée GPS ou de trace
  dans un fichier publié sous `docs/`.
- **`export-garmin.yml`** compare le flag `simulation` en bash sur chaîne
  brute, jamais dans une expression GitHub `${{ }}` : selon le typage
  (booléen vs chaîne), la comparaison peut être fausse dans les deux sens, ce
  qui produirait une "panne muette" (le job passe au vert, rien ne part sur
  la montre). Ne pas revenir en arrière là-dessus.
- **Cron GitHub Actions décalé** : les horaires `7h13`/`21h17` (au lieu de
  7h/21h) sont volontaires, pour limiter (pas supprimer) le retard que
  GitHub applique aux crons programmés sur les petits dépôts peu actifs.

## En local

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt
cp .env.example .env        # remplir INTERVALS_API_KEY et INTERVALS_ATHLETE_ID
.venv/Scripts/python scripts/fetch_data.py
.venv/Scripts/python scripts/build_site.py
```

Changer de thème : `python scripts/build_site.py --theme releve` (mémorise
le choix) ou `--liste` pour voir ce qui existe.

Envoyer le plan sur la montre : `python scripts/export_garmin.py` (simulation
par défaut) puis `--envoyer` pour écrire réellement, après avoir vérifié dans
Intervals.icu (section Garmin) que "Upload planned workouts to Garmin
Connect" est coché.

## Écarts résolus le 20/09/2026

Deux écarts entre le dépôt et un résumé fourni par Alex depuis l'app Claude
(hors Claude Code) ont été tranchés par Alex :

- Poids de départ : **82 kg** confirmé (c'était déjà la valeur dans le dépôt).
- Semi-marathon : confirmé à **Bois de Vincennes, Paris**, mais déplacé au
  **05/12/2026** (au lieu du 25/10/2026 initialement dans le dépôt). Le plan
  a été réétalé en conséquence, voir la section "Le plan" ci-dessus.

Le résumé de l'app mentionnait aussi un profil hors périmètre de ce dépôt
(musculation/calisthenics, basket, foot en loisir, douleur en supination) :
rien de tout ça n'est suivi ici, ce dépôt ne couvre que la course à pied.
