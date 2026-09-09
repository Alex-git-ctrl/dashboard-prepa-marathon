# Apple (España) : référence de style

Document fourni par Alex le 9 septembre 2026. C'est la source du thème
`docs/themes/apple.css` (« La halle »).

Deux notes sur cette copie. Le fichier d'origine était encodé en Latin-1 et
arrivait avec des accents cassés (`Ã©`, `â€"`) : ils sont rétablis ici. Et les
tirets cadratins de l'original sont remplacés par la ponctuation prévue au
§0 de CLAUDE.md, qui interdit ce caractère dans tout le projet. Le fond n'a
pas bougé.

> Cathédrale d'espace blanc et titres murmurés. Une vaste halle pâle où de
> très gros caractères en graisse 700 flottent dans l'air, retenus seulement
> par les couleurs pastel des produits et par un unique fil bleu.

**Thème :** clair

Le langage des pages produit d'Apple est une étude de générosité
typographique : d'énormes titres en SF Pro Display posés sur un fond presque
blanc, entourés d'un espace négatif considérable qui rend chaque mot
délibéré. La palette est quasi monochrome (texte en `#1d1d1f`, fond alternant
entre `#ffffff` et `#f5f5f7`) avec un seul accent bleu, `#0071e3`, réservé aux
moments interactifs. La couleur apparaît dans l'imagerie produit elle-même,
les finitions pastel, jamais comme décoration d'interface. Les composants sont
sans bordure : cartes arrondies à 28 px, boutons en pilule qui touchent
presque le bord de la page sans conteneur visible, et zéro ombre. Le rythme
vient de l'alternance de bandes blanches et grises, pas de séparateurs ni de
bordures.

## Couleurs

| Nom | Valeur | Token | Rôle |
|---|---|---|---|
| Primary Ink | `#1d1d1f` | `--color-primary-ink` | Titres, texte courant, libellés de boutons : la teinte dominante de premier plan sur toutes les surfaces |
| Mid Gray | `#707070` | `--color-mid-gray` | Texte secondaire, navigation inactive, libellés discrets |
| Deep Gray | `#474747` | `--color-deep-gray` | Texte et iconographie de navigation, emphase moyenne |
| Hairline | `#d6d6d6` | `--color-hairline` | Filets entre sections et éléments d'interface |
| Canvas | `#f5f5f7` | `--color-canvas` | Fond alterné : la bande grise qui découpe les sections blanches |
| Paper | `#ffffff` | `--color-paper` | Surface des cartes, fond principal, texte sur aplat sombre |
| Cool Wash | `#e8e8ed` | `--color-cool-wash` | Fond de bouton discret, surface survolée, pastille de pagination |
| Faded Surface | `#fafafc` | `--color-faded-surface` | Navigation globale ouverte, panneaux en élévation |
| Quiet Dot | `#777779` | `--color-quiet-dot` | Pastilles de pagination, état interactif tertiaire |
| Electric Blue | `#0071e3` | `--color-electric-blue` | Boutons d'action pleins : le seul accent chromatique de l'interface, employé avec parcimonie |
| Link Blue | `#0066cc` | `--color-link-blue` | Liens dans le texte courant, chevrons de lien |
| Ember | `#b64400` | `--color-ember` | Accent orange pour badges, validations et étiquettes d'état courtes |
| Sky | `#c8d8e0` | `--color-sky` | Finition produit : bleu pastel |
| Citrus | `#dddc8c` | `--color-citrus` | Finition produit : jaune-vert pastel |
| Starlight | `#f0e4d3` | `--color-starlight` | Finition produit : crème chaud |
| Silver | `#e3e4e5` | `--color-silver` | Finition produit : gris froid |
| Blush | `#e8d0d0` | `--color-blush` | Finition produit : rose doux |
| Indigo | `#596680` | `--color-indigo` | Finition produit : indigo sourd |
| Midnight | `#2e3642` | `--color-midnight` | Finition produit : charbon profond |

## Typographie

### SF Pro Display, titres et affichages

Graisse 700 à 80 ou 96 px, avec une chasse négative jusqu'à -1,44 px : c'est
ce qui produit la signature Apple du titre énorme flottant dans le blanc.
Substituts : Inter, `system-ui`.

- Graisses : 600, 700
- Tailles : 21, 24, 28, 32, 40, 56, 80, 96 px
- Interlignage : 1,04 à 1,07
- Chasse : -1,44 px à 96 px, -0,28 px à 56 px

### SF Pro Display, titres de section et de carte

Graisse 600 avec une chasse légèrement positive : à taille moyenne, la lecture
devient chaleureuse et accessible, en contraste avec les titres serrés
au-dessus.

- Graisse : 600
- Interlignage : 1,14 à 1,38
- Chasse : 0,007 em à 28 px, 0,011 em à 21 px

### SF Pro Text, texte courant

Graisse 400 à 17 px, c'est le cheval de trait. La chasse négative resserre le
texte pour le rendre net sur des pages denses en information.

- Graisses : 400, 500, 600
- Tailles : 8, 12, 14, 17, 20, 44 px
- Interlignage : 1,18 à 1,47
- Chasse : -0,022 em à 17 px, -0,003 em à 44 px

### Échelle typographique

| Rôle | Taille | Interligne | Chasse | Token |
|---|---|---|---|---|
| micro | 12 px | 16 | -0,12 px | `--text-micro` |
| caption | 14 px | 18 | -0,224 px | `--text-caption` |
| body-sm | 17 px | 25 | -0,374 px | `--text-body-sm` |
| body | 21 px | 29 | 0,231 px | `--text-body` |
| body-lg | 28 px | 32 | 0,196 px | `--text-body-lg` |
| subheading | 32 px | 36 | 0,128 px | `--text-subheading` |
| heading-sm | 40 px | 48 | | `--text-heading-sm` |
| heading | 56 px | 60 | -0,28 px | `--text-heading` |
| heading-lg | 80 px | 84 | -1,2 px | `--text-heading-lg` |
| display | 96 px | 100 | -1,44 px | `--text-display` |

## Espacement et formes

**Unité de base :** 4 px. **Densité :** confortable.

Échelle : 4, 8, 12, 16, 20, 24, 28, 32, 40, 44, 48, 52, 76, 80, 120, 144 px.

### Rayons

| Élément | Valeur |
|---|---|
| cartes | 28 px |
| liens | 10 px |
| badges | 36 px |
| boutons | 980 px |
| petits boutons | 999 px |
| images produit | 28 px |

### Mise en page

- Largeur maximale : 1200 px
- Écart entre sections : 100 à 120 px
- Padding de carte : 28 px
- Écart entre éléments : 8 à 10 px

## Composants

### Bouton pilule plein, action principale

Forme en pilule, rayon 980 px. Fond `#0071e3`, texte blanc, 17 px SF Pro Text
graisse 400. Padding horizontal 16 px, vertical 11 px. Une occurrence par
section au maximum.

### Bouton pilule fantôme

Fond transparent, bordure 1 px `#1d1d1f`. Rayon 999 px. Texte `#1d1d1f` à
17 px graisse 400. Padding horizontal 16 px.

### Lien texte avec flèche

Ni fond ni bordure. Couleur `#0066cc` avec un chevron final. 17 px graisse
400. Souligné uniquement au survol.

### Lien souligné d'un filet

Fond transparent, texte `#1d1d1f` ou `#474747`, bordure basse de 1 px de la
même couleur. 12 à 14 px. Employé en navigation globale et en pied de page.

### Carte de mise en avant

Rayon 28 px. Fond blanc ou `#f5f5f7`. Padding interne de 28 à 40 px. Contient
un titre de 40 à 56 px, un texte courant de 17 px, et éventuellement un appel
à l'action. Aucun contour visible.

### Pastille de finition produit

Petit carré arrondi d'environ 80 px, rayon 28 px, rempli d'une couleur de
finition. Ni bordure ni libellé à l'intérieur : la couleur EST le contenu.

### Titre de section

28 à 32 px SF Pro Display graisse 600, couleur `#1d1d1f`. Suivi d'un
paragraphe optionnel à 21 px. Aligné à gauche. La chasse légèrement positive
(+0,007 em) réchauffe les titres de taille moyenne.

### Barre de navigation globale

Hauteur 44 px. Le fond passe de transparent à `#fafafc` au défilement, avec un
flou d'arrière-plan de 20 px. Liens à 12 px graisse 400, espacés de 8 à 10 px.

### Bandeau promotionnel

Une ligne centrée à 12 ou 14 px. Texte noir sur blanc, lien éventuel en
`#0066cc`.

### Hero produit

Fond blanc. Nom du produit à 17 px centré. Titre à 96 px graisse 600, chasse
-1,44 px. Bouton d'action en dessous, puis le prix à 17 px. L'image occupe la
moitié basse.

### Vitrine de coloris

Deux cartes côte à côte, rayon 28 px, chacune avec un rendu produit sur le
fond de sa finition. Les cartes sont posées sur `#f5f5f7`. Aucun texte : le
visuel fait le travail.

### Badge « Nouveau »

Texte seul, sans fond ni forme. Couleur `#b64400`, 12 à 14 px graisse 500.
Placé au-dessus du nom du produit, comme une ponctuation chaude dans une
palette froide.

### Pastilles de pagination

Cercles d'environ 8 px. Active en `#1d1d1f`, inactives en `#777779`, espacées
de 7 px.

### Séparateur de section, implicite

Aucun trait. Les sections alternent entre `#ffffff` et `#f5f5f7`, et le
changement de fond suffit à signaler la séparation. Espacement vertical de 100
à 120 px.

### Pied de page légal

Fond `#f5f5f7`. Texte à 12 px graisse 400, couleur `#707070`. Liens en
`#0066cc`. Interlignage serré, 1,33.

## À faire

- SF Pro Display graisse 700 pour les titres à 80 ou 96 px, avec une chasse
  négative jusqu'à -1,44 px. C'est la chasse serrée sur du très gros corps qui
  donne aux titres Apple leur allure d'architecture.
- Alterner les fonds de section entre `#ffffff` et `#f5f5f7` pour créer un
  rythme sans bordure ni séparateur.
- Rayon de 28 px sur toutes les cartes et images produit : c'est l'arrondi
  signature qui adoucit tout le système.
- Réserver `#0071e3` aux boutons d'action pleins. Jamais comme couleur de
  texte, jamais en décoration. Les liens utilisent `#0066cc`.
- Boutons en pilule à 980 ou 9999 px de rayon. Un bouton carré ou peu arrondi
  casse la fluidité du système.
- Texte courant à 17 px graisse 400 avec -0,022 em de chasse : c'est la taille
  de lecture canonique de toutes les pages Apple.
- Interlignage serré sur les grands corps (1,04 à 1,07) et ouvert sur le texte
  courant (1,47). Le contraste crée la hiérarchie sans changer de taille.
- Laisser l'imagerie produit porter la couleur. L'interface reste monochrome.

## À ne pas faire

- Pas d'ombre ni d'élévation sur les cartes. Le système repose sur
  l'alternance des fonds et sur le rayon de 28 px.
- Pas d'accent au-delà de `#0071e3` et `#0066cc`. Même le badge orange
  « Nouveau » n'apparaît qu'une fois par page au plus.
- Pas de titre en dessous de 40 px. Le système dépend du très gros corps pour
  produire son effet de cathédrale.
- Pas de bordure pour séparer les sections : alterner la couleur de fond.
- Pas de rayon inférieur à 10 px sur un élément interactif.
- Pas de dégradé décoratif sur une surface d'interface. Les dégradés produit
  appartiennent aux rendus, pas aux boutons ni aux cartes.
- Pas de graisse inférieure à 400 pour le texte courant, ni à 600 pour un
  titre. Le système parle d'une voix claire et affirmée.
- Pas de fond derrière un lien texte : couleur et chevron, jamais de cadre.
- Pas de paragraphe centré. Un titre peut l'être, une description non.

## Surfaces

| Niveau | Nom | Valeur | Usage |
|---|---|---|---|
| 0 | Canvas White | `#ffffff` | Fond principal et surface de carte |
| 1 | Canvas Gray | `#f5f5f7` | Bandes alternées, pied de page, fond de badge |
| 2 | Hover Wash | `#e8e8ed` | Survol des boutons clairs et des pastilles |
| 3 | Nav Elevated | `#fafafc` | Fond de navigation après défilement |

## Imagerie

Le langage visuel d'Apple est d'abord photographique et centré produit : des
rendus matériels recadrés serré sur blanc pur ou sur la couleur de la
finition, sans contexte de vie ni mise en scène. Le hero montre des mains
tenant un MacBook vert pastel : l'élément humain est incident, il donne
l'échelle et la texture plutôt qu'une émotion. Les sections de coloris
présentent deux appareils côte à côte sur leurs finitions respectives, chaque
carte étant un aplat de couleur avec le produit au centre. Les plans de détail
sont des gros plans extrêmes sur fond neutre. Aucune illustration, aucun
graphisme abstrait, aucune image décorative : le produit EST le visuel.
L'iconographie est monochrome, en trait de 1,5 à 2 px, dans l'esprit des SF
Symbols. Le traitement photographique est toujours en haute clé : une lumière
égale et sans ombre qui aplatit le produit en forme graphique plutôt qu'en
objet dimensionnel.

## Mise en page

Des sections pleine largeur, bord à bord, avec un padding interne généreux de
40 à 80 px sur les côtés. La largeur utile est de 1200 px centrés dans chaque
bande. Le hero est une pile centrée : sur-titre, titre surdimensionné, bouton
unique, ligne de prix, puis l'image produit qui occupe les 60 % inférieurs de
la fenêtre. Les sections suivent ensuite un motif répété : un titre aligné à
gauche dans une bande, puis une mise en page à deux colonnes (texte à gauche,
image à droite, ou l'inverse), une grille de trois cartes, ou une vitrine
centrée. Le rythme est entièrement porté par l'alternance des fonds et par des
écarts verticaux de 100 à 120 px : ni séparateur, ni carte enveloppante. La
navigation globale est une barre unique de 44 px. Les sections de
caractéristiques utilisent des bandes pleine largeur où le texte tient dans
des colonnes étroites d'environ 560 px, centrées face à une zone visuelle plus
large.

## Marques voisines

- Pages iPhone d'Apple : mêmes titres surdimensionnés sur bandes alternées,
  mêmes rayons de 28 px, mêmes boutons pilule bleus.
- Pages Vision Pro : même générosité typographique, même interface monochrome
  à accent unique.
- Pages AirPods Max : langage de composants identique.
- Nothing.tech : même hiérarchie portée par la typographie, même interface
  quasi monochrome.
- Teenage Engineering : même retenue délibérée, l'interface si silencieuse que
  le produit devient le seul intérêt visuel.

## Ce que le thème du dashboard en a retenu

Le thème `docs/themes/apple.css` applique ce langage, avec trois écarts
assumés et documentés dans l'en-tête du fichier.

1. **L'échelle est celle d'un outil, pas d'une page de vente.** Les pas
   typographiques sont ceux du guide, tronqués en haut : le titre plafonne à
   56 px et non 96, et les sections sont séparées de 56 px et non 120.
   Un tableau de bord dense se lit sur un téléphone un mardi midi.
2. **La couleur vit dans les tracés.** Le guide dit que c'est la photo produit
   qui porte la couleur. Ici il n'y a pas de produit : ce sont les graphiques.
   L'interface reste monochrome plus un bleu, et les cinq zones de fréquence
   cardiaque gardent les teintes de la Forerunner.
3. **Les couleurs d'état ont été assombries.** Le vert `#248a3d` du guide
   n'atteint que 4,04 de contraste sur le fond gris, sous le minimum de 4,5
   pour du petit texte. Il devient `#1d7a34`.

Un détail technique du guide n'a délibérément pas été suivi : il recommande
`font-feature-settings: "numr"` sur les contenus numériques. Cette
fonctionnalité produit des numérateurs en exposant, pas des chiffres
tabulaires. Le thème utilise `font-variant-numeric: tabular-nums`.
