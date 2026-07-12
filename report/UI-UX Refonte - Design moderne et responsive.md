# 📋 Rapport - Refonte UI/UX : Design moderne et responsive

**Branche** : `feature/ui-ux-refonte`
**PR** : [#103](https://github.com/FoxOps/leviia-schedule/pull/103) (draft)
**Date de début** : 2026-07-12
**Statut** : 🟢 Plan terminé - vérification visuelle manuelle requise avant merge (voir Limite de vérification)
**Base** : `main` (post refonte Phases 1-6, commit `ae1c091`)

---

## 🎯 Portée (validée avec l'utilisateur)

- Garder Bulma 1.0.4 (déjà récent, pas de bug technique justifiant un
  changement de framework) mais aller au-delà des simples corrections :
  refonte visuelle profonde (palette, typographie, layout, cards,
  espacements) — pas juste des fixes ciblés.
- Corriger en priorité le vrai bug responsive trouvé à l'audit : menu de
  navigation mobile inutilisable (voir ci-dessous).
- Audit complet des breakpoints sur toutes les pages, pas seulement la
  navbar.

## 🔍 Audit initial

### Bug réel trouvé : navbar mobile inutilisable

`app/templates/base.html` a un `<nav class="navbar ...">` avec
`.navbar-menu` (7 liens + dropdown utilisateur) mais **aucun bouton
`.navbar-burger`** nulle part dans le template, ni logique JS pour
toggle `is-active`. Or Bulma masque `.navbar-menu` par défaut sous
1024px (`display: none`) tant que `.navbar-menu.is-active` n'est pas
appliqué. Résultat : sur mobile/tablette, le menu de navigation est
**invisible et totalement inaccessible** - aucun moyen d'atteindre
Shifts/Astreintes/Congés/Admin/Profil/Déconnexion. Confirmé par
recherche exhaustive (`grep -n "burger" base.html app/static/js/`) :
zéro résultat.

### État du design system

- `app/static/css/variables.css` ne fait que mapper les `--bulma-*`
  vers des noms d'app (`--color-primary`, etc.) sans aucune
  personnalisation - couleur primaire = turquoise par défaut de Bulma
  (`--bulma-primary-h: 171deg`), pas de palette de marque.
- Pas d'échelle d'espacement (spacing scale) ni de rayons de bordure
  cohérents définis en dehors des défauts Bulma bruts.
- Bulma 1.0.4 charge déjà `Inter` comme police par défaut
  (`--bulma-family-primary`), mais aucun fichier de police n'est
  vendorisé (`app/static/vendor/webfonts/` ne contient que Font
  Awesome) - `Inter` retombe donc silencieusement sur les polices
  système (SF Pro/Segoe UI/Roboto selon l'OS). Pas un bug (dégradation
  propre), mais noté : vendoriser Inter serait un vrai gain visuel,
  hors périmètre de cette passe (ajout d'assets, licence à vérifier) -
  **reporté**, voir section Reporté plus bas.
- CSS déjà bien organisée en couches (`base`, `components/`, `layout/`,
  `pages/`, `themes/dark.css`, `utilities.css`) - la structure est
  gardée telle quelle, seul le contenu est retouché.
- Bulma 1.x re-thème via 3 variables HSL (`--bulma-primary-h/-s/-l`),
  toutes les nuances dérivées (00 à 100, invert, etc.) sont calculées
  automatiquement par Bulma - c'est la bonne façon d'overrider,
  beaucoup plus robuste que de redéfinir chaque nuance à la main.

## 📐 Plan

1. [x] Corriger le burger menu mobile (bug bloquant, priorité 1)
2. [x] Nouvelle palette de marque (HSL override du primary Bulma -
   révisée en vert/teal doux après feedback), échelle de rayons plus
   arrondie
3. [x] Rafraîchir les composants : boutons, cards, formulaires, tables,
   modales (ombres, rayons, espacements cohérents avec la nouvelle
   palette)
4. [x] Vérifier la cohérence du thème sombre avec la nouvelle palette -
   Bulma dérive les nuances dark-mode depuis les mêmes variables HSL de
   base, aucun changement supplémentaire requis
5. [x] Audit responsive complet (tables sur mobile, dashboard,
   formulaires, calendrier) sur les pages principales (index, schedule,
   oncall, leave, admin) - a débouché sur la découverte des 2 pages
   cassées par la CSP Phase 6 (voir Journal)
6. [x] Polish layout (header, footer, spacing global, fallbacks de
   couleur obsolètes dans fullcalendar-overrides.css)

## ⚠️ Limite de vérification

Aucun outil de rendu/capture d'écran de navigateur disponible dans cet
environnement. Vérification faite par : serveur de développement réel +
`curl` (statut HTTP, présence des classes/attributs attendus dans le
HTML rendu), validité syntaxique CSS/JS, cohérence des variables. **Pas
de vérification visuelle pixel par pixel** - à faire manuellement dans
un navigateur avant merge.

---

## 📝 Journal

### Menu mobile navbar (commit `6ffbdd5`)

Bouton `.navbar-burger` ajouté + module `NavbarMenu`
(`app/static/js/navbar/navbar-menu.js`) qui toggle `is-active`/
`aria-expanded`, ferme au clic sur un lien et à Escape. Vérifié en réel
(HTML rendu contient burger + id `navbar-menu` reliés, JS chargé 200).

### Palette de marque (commit `043f9f7`, révisée en `7700a10`)

Première passe : indigo (243deg 75% 58%). **Feedback utilisateur : trop
agressif aux yeux.** Retour dans la famille verte/teal de l'original
Bulma (171deg 100% 41%) mais désaturé pour rester doux : **168deg 70%
42%**. RGB dérivé (32, 182, 152) répercuté partout où la couleur était
dupliquée en dur (focus-ring, survol de tableau, fallback CSS).
Rayons de bordure adoucis (0.375/0.5/1rem), ombres passées à des ombres
diffuses en plusieurs couches (`--shadow-sm/md/lg`).

### Composants (commit `dd2f6e9`)

Boutons, cards, formulaires, tables, modales : rayons/ombres cohérents
avec `variables.css`. Bugs trouvés en cours de route : focus-ring des
inputs avait le RGB de l'ancien turquoise en dur (incohérent avec la
nouvelle palette) ; `.modal-card` sans largeur responsive sous 600px ni
`overflow: hidden` (les fonds carrés de head/foot dépassaient du bord
arrondi de la card).

### Dashboard + header/footer (commit `36c418d`)

**Bug réel trouvé** : `.chart-container` (graphique "Répartition par
type de shift") n'avait **aucune règle CSS**. `.chart-item` avait
`flex: 1` mais sans `display: flex` sur le parent ça ne servait à
rien - les barres s'empilaient verticalement en pleine largeur au lieu
de former un graphique côte à côte, et le `height: X%` inline de
`.chart-bar` ne pouvait rien résoudre sans hauteur de référence sur le
parent direct. Corrigé (hauteur fixe + `align-items: stretch` par
défaut + `overflow-x: auto` si trop de types). Audit `.level` (Bulma) :
l'override du projet ne touche pas `flex-direction`, le stacking mobile
natif de Bulma reste donc intact - pas de bug. Aucune largeur fixe
dangereuse trouvée ailleurs (grep systématique).

### Audit large : 2 pages cassées en prod par la CSP Phase 6 (commit `a6fadf8`)

**Découverte majeure en auditant le responsive** : la CSP `script-src
'self'` stricte (Phase 6) bloque silencieusement (erreur console,
**pas** d'erreur HTTP) tout `<script>` inline exécutable. Le test de
régression de Phase 6 n'avait vérifié qu'`index.html`. Balayage statique
(regex sur tous les templates) : **2 autres pages avaient encore un
`<script>` inline**, cassées en production sans que rien ne le
signale :

- `auth/ics_token.html` : tous les boutons "Copier" (token + 6 URLs
  d'export ICS) étaient no-op silencieux. Externalisé vers
  `static/js/clipboard/copy-token.js` (7 fonctions dédupliquées en un
  helper `copyInputValue`), exposé via `window.Leviia`.
- `admin/automation/full.html` : glisser-déposer de l'ordre de rotation
  d'astreinte entièrement cassé. Bonus : `saveRotationOrder()` était
  définie à l'intérieur du listener `DOMContentLoaded`, donc
  `onclick="saveRotationOrder()"` était **déjà cassé avant même la
  CSP** (portée de fonction incorrecte). Externalisé vers
  `static/js/automation/rotation-order.js`, corrige les deux bugs d'un
  coup.

Test de régression étendu : balayage paramétré sur 8 pages
représentatives (`test_page_has_no_inline_executable_script`) au lieu
d'une seule, pour empêcher ce type de régression de repasser inaperçu.
Vérifié avec CSP réellement active (Talisman, pas juste TestingConfig).
781 tests passent (8 nouveaux).

---

### Audit calendrier + fallbacks obsolètes (commit `b49d56b`)

Audit schedule/oncall/leave/admin : tables déjà dans `.table-container`
(overflow-x:auto), `.field.is-horizontal` déjà géré nativement par
Bulma (stack mobile sous 769px), `.level.is-mobile` correct,
`.column.is-one-fifth` (dashboard admin) stack déjà en pleine largeur
sous 769px. Aucun bug bloquant supplémentaire trouvé - la navbar et le
graphique dashboard étaient les deux vrais problèmes structurels de
l'app. `fullcalendar-overrides.css` avait les mêmes fallbacks de
couleur obsolètes (`#00D1B2`) et rayons 4px en dur que le reste de
l'app avant cette passe - corrigés pour cohérence.

---

*Dernière mise à jour : 2026-07-12 — plan terminé (9 commits) : burger
mobile, palette (révisée après feedback), composants, dashboard, audit
CSP (2 pages cassées trouvées et fixées), audit responsive complet.
Reste : vérification visuelle manuelle dans un navigateur avant merge
(voir Limite de vérification en haut du rapport - aucun outil de rendu
visuel disponible dans cet environnement).*
