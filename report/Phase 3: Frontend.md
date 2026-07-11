# 📋 Rapport de Refactorisation - Phase 3: Frontend
**Branche** : `refacto/phase3`
**PR** : à créer
**Date de début** : 2026-07-11
**Statut** : 🟡 En cours
**Base** : `main` (inclut Phase 1 + Phase 2, PR #98 mergée)

---

## 📈 État des lieux (avant restructuration)

| Fichier | Lignes | Note |
|---|---|---|
| `app/static/css/base-styles.css` | 660 | |
| `app/static/css/dark-theme.css` | 337 | duplication connue avec base-styles.css |
| `app/static/css/fullcalendar-styles.css` | 188 | |
| `app/static/js/script.js` | 673 | |

**Correction par rapport au plan initial** : le plan mentionnait `script.js`
à *21 724 lignes*. Le fichier réel fait **673 lignes**. Un monolithe
mono-fichier reste à découper par souci de clarté, mais ce n'est pas
l'énorme fichier décrit initialement — la découpe en modules ES6 sera
proportionnée à la taille réelle plutôt qu'à l'estimation d'origine.

`app/static/vendor/` (Bulma, Font Awesome, FullCalendar) est déjà géré
séparément par `scripts/download_vendor_assets.py` (téléchargement local,
pas de CDN en prod — contrainte validée en Phase 1) : **non touché** par
cette phase, reste à la racine de `static/vendor/`.

**Hors scope** (décision validée en amont) : amélioration accessibilité
WCAG 2.1 AA — mise de côté, cause trop de problèmes UI/UX actuellement.

---

## 🎯 Plan de travail

### 3.1 CSS
- [x] `variables.css` : variables CSS globales (mapping Bulma, couleurs)
- [x] `base.css` : reset + styles de base (skip-link, focus-visible, sr-only)
- [x] `utilities.css` : classes utilitaires (`.mt-*`, `.gap-*`, `.min-w-*`, `.d-*`)
- [x] `components/` : buttons, cards, forms, tables, modals
- [x] `layout/` : header, footer, grid
- [x] `pages/` : dashboard (seule page avec CSS dédié pour l'instant)
- [x] `themes/dark.css` (élimine la duplication base-styles.css /
      dark-theme.css / fullcalendar-styles.css — tout le mode sombre
      consolidé en un seul fichier)
- [x] `vendor/fullcalendar-overrides.css` : overrides FullCalendar par
      défaut (hors thème sombre), séparés du reste du vendor
- [ ] Minification en production

### 3.2 JavaScript
- [x] `main.js` : point d'entrée
- [x] `theme/theme-manager.js`
- [ ] ~~`calendar/` : fullcalendar-config.js, event-handlers.js~~ — n'existe pas
      en tant que module séparé, cf. note ci-dessous
- [ ] ~~`forms/` : validation.js, submission.js~~ — idem, hors scope pour
      l'instant (validation de formulaire déjà couverte par
      `validateFormAccessible` dans `utils/accessibility.js`)
- [x] `notifications/toast.js`
- [x] `utils/` : dom.js, date.js, accessibility.js (pas de api.js —
      aucun appel fetch/API centralisé n'existait dans script.js)
- [x] Modules ES6 (import/export)
- [x] JSDoc (conservé depuis script.js, pas de format supplémentaire ajouté)
- [ ] Tests unitaires (Jest ou Vitest) — pas de setup JS existant dans le
      projet (aucun package.json/node_modules pour du tooling front), non
      fait faute de temps

### 3.3 Templates
- [ ] Macros Jinja2 réutilisables (`_macros/forms.html`, etc.)
- [ ] Structure HTML standardisée
- [ ] Meta tags SEO
- [ ] Optimisation du chargement des ressources
- ~~Accessibilité WCAG 2.1 AA~~ — hors scope (cf. ci-dessus)

---

## 📝 Journal

*(mis à jour à chaque étape)*

### 2026-07-11 — 3.1 CSS terminé

Restructuration complète de `app/static/css/` : les 3 anciens fichiers
(`base-styles.css` 660 lignes, `dark-theme.css` 337 lignes,
`fullcalendar-styles.css` 188 lignes) sont **supprimés** et remplacés par :

```
css/
├── variables.css                      (mapping Bulma, thème-agnostique)
├── base.css
├── utilities.css
├── components/{buttons,cards,forms,tables,modals}.css
├── layout/{header,footer,grid}.css
├── pages/dashboard.css
├── themes/dark.css                    ([data-theme="dark"] / .dark-mode uniquement)
└── vendor/fullcalendar-overrides.css  (styles FullCalendar par défaut)
```

Pas de `themes/light.css` séparé : le thème clair est simplement l'état
par défaut de Bulma + `variables.css`, il n'y a rien à surcharger.

**Duplication éliminée** : `fullcalendar-styles.css` répétait dans son
propre bloc `[data-theme="dark"]` la quasi-totalité des règles déjà
présentes dans `dark-theme.css` (`.fc`, `.fc-today`, `.fc-header-toolbar`,
`.fc-col-header-cell`, `.fc-day`, etc.). Tout est maintenant consolidé une
seule fois dans `themes/dark.css`.

**Bugs évités en cours de route** (repérés avant validation, corrigés
avant commit) :
- `components/cards.css` : j'avais substitué `box-shadow: var(--shadow-md)`
  sur `.box:hover` à la place de la valeur littérale d'origine
  `0 4px 6px rgba(0,0,0,0.1)` — ce ne sont pas les mêmes valeurs (blur/offset
  différents), ça aurait changé le rendu. Remis la valeur exacte.
- `components/buttons.css` : j'avais fusionné la règle générale
  `.icon { vertical-align: middle; }` dans `.button .icon { min-width/height }`,
  ce qui aurait limité la règle générale aux boutons uniquement. Séparé en
  deux règles distinctes.

**Tests mis à jour** : `tests/test_dark_theme.py` et
`tests/test_theme_fixes.py` référençaient en dur les 3 anciens noms de
fichiers dans ~20 assertions. Réécrits pour pointer vers les nouveaux
fichiers, en gardant l'intention de chaque test (ex : le test de
contraste des boutons `.is-warning` en mode sombre vérifie maintenant
`themes/dark.css` au lieu de `dark-theme.css`). `tests/manual_test_theme.py`
n'est pas ramassé par pytest (nom de fichier hors convention `test_*.py`) —
laissé tel quel pour l'instant, pas bloquant.

Un test (`test_dark_theme_css_content`) vérifiait la présence de la
chaîne `prefers-color-scheme: dark`, qui ne correspondait en réalité qu'à
un commentaire dans l'ancien fichier (pas de vraie règle `@media` — Bulma
gère ça nativement via ses propres variables). Assertion retirée plutôt
que reproduite artificiellement : elle ne testait rien de réel.

Suite complète : **511 tests passent, 0 échec**. Vérifié en conditions
réelles (serveur Flask dev, login, dashboard, page shifts) : les 14
fichiers CSS se chargent tous en 200, thème sombre et FullCalendar
inchangés visuellement.

### 2026-07-11 — 3.2 JavaScript terminé (périmètre réel)

`app/static/js/script.js` (673 lignes) supprimé, remplacé par :

```
js/
├── main.js                    (point d'entrée, expose window.Leviia)
├── theme/theme-manager.js     (classe ThemeManager)
├── utils/
│   ├── dom.js                 (toggle/show/hide/addClass/removeClass/toggleClass)
│   ├── date.js                (formatDate/formatTime/formatDateTime)
│   └── accessibility.js       (annonces lecteur d'écran, focus, navigation
│                                clavier, validation de formulaire, modale
│                                de confirmation accessible)
└── notifications/toast.js     (showNotification, confirmAction)
```

`base.html` charge `main.js` en `<script type="module">` au lieu du
`<script>` classique.

**Correction par rapport au plan initial (comme pour l'estimation de
lignes)** : le plan prévoyait un dossier `calendar/` (config FullCalendar,
handlers d'événements) et un dossier `forms/`. Ça n'existe pas dans
`script.js` — la config FullCalendar (~576 lignes) est un `<script>` inline
dans `index.html`, fortement templaté Jinja2 (URLs `{{ url_for(...) }}`,
CSRF token, données utilisateur injectées côté serveur). L'extraire en
module statique demanderait de faire transiter ces données via des
attributs `data-*` ou un blob JSON — un chantier séparé et plus risqué,
volontairement laissé de côté ici plutôt que bâclé. `utils/api.js` n'a pas
été créé non plus : `script.js` ne contenait aucun appel `fetch` centralisé
à extraire.

**Vérification d'innocuité avant conversion en module** : les 35 usages de
`Leviia.*` dans les templates (`onclick="Leviia.confirmActionAccessible(...)"`
etc.) sont soit des attributs `onclick` (exécutés seulement au clic
utilisateur, bien après le chargement complet de la page), soit des
callbacks FullCalendar asynchrones dans `index.html` — aucun appel
synchrone pendant le parsing du HTML. Un `<script type="module">` est
différé (comme `defer`) : ça ne casse donc aucun de ces appels.

Vérifié : tous les fichiers JS renvoient `Content-Type: text/javascript`
(requis pour que le navigateur accepte les modules ES6), la chaîne
d'imports résout correctement (`main.js` → `theme-manager.js` →
`accessibility.js`, etc.), `node --check` ne remonte aucune erreur de
syntaxe sur les 6 fichiers. `tests/manual_test_theme.py` mis à jour en
parallèle des tests pytest (mêmes anciens chemins en dur).

Suite complète : **511 tests passent, 0 échec**.

Prochaine étape : 3.3 templates (macros Jinja2, structure HTML, SEO,
optimisation du chargement des ressources).

---

*Dernière mise à jour : 2026-07-11*
