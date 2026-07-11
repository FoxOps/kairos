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
- [ ] `main.js` : point d'entrée
- [ ] `theme/theme-manager.js`
- [ ] `calendar/` : fullcalendar-config.js, event-handlers.js
- [ ] `forms/` : validation.js, submission.js
- [ ] `notifications/toast.js`
- [ ] `utils/` : dom.js, date.js, api.js
- [ ] Modules ES6 (import/export)
- [ ] JSDoc
- [ ] Tests unitaires (Jest ou Vitest) — à évaluer selon temps disponible

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

Prochaine étape : 3.2 découpe de `script.js` (673 lignes) en modules ES6.

---

*Dernière mise à jour : 2026-07-11*
