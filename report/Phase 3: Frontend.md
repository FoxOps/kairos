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
- [ ] `variables.css` : variables CSS globales (couleurs, espacements)
- [ ] `base.css` : reset + styles de base
- [ ] `utilities.css` : classes utilitaires
- [ ] `components/` : buttons, cards, forms, tables, modals
- [ ] `layout/` : header, sidebar, footer, grid
- [ ] `pages/` : schedule, oncall, leave, dashboard
- [ ] `themes/` : light.css, dark.css (élimine la duplication
      base-styles.css / dark-theme.css)
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

---

*Dernière mise à jour : 2026-07-11*
