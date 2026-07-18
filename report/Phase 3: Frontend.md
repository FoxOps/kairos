# 📋 Refactoring Report - Phase 3: Frontend
**Branch**: `refacto/phase3`
**PR**: [#99](https://github.com/FoxOps/leviia-schedule/pull/99)
**Start date**: 2026-07-11
**Status**: 🟢 Complete
**Base**: `main` (includes Phase 1 + Phase 2, PR #98 merged)

---

## 📈 Current state (before restructuring)

| File | Lines | Note |
|---|---|---|
| `app/static/css/base-styles.css` | 660 | |
| `app/static/css/dark-theme.css` | 337 | known duplication with base-styles.css |
| `app/static/css/fullcalendar-styles.css` | 188 | |
| `app/static/js/script.js` | 673 | |

**Correction relative to the initial plan**: the plan mentioned `script.js`
at *21,724 lines*. The actual file is **673 lines**. A single monolithic
file still needs to be split up for clarity, but it's not the huge file
originally described — the split into ES6 modules will be proportionate
to the actual size rather than to the original estimate.

`app/static/vendor/` (Bulma, Font Awesome, FullCalendar) is already
managed separately by `scripts/download_vendor_assets.py` (local download,
no CDN in production — a constraint validated in Phase 1): **not touched**
by this phase, stays at the root of `static/vendor/`.

**Out of scope** (decision validated upstream): WCAG 2.1 AA accessibility
improvements — set aside, currently causes too many UI/UX issues.

---

## 🎯 Work plan

### 3.1 CSS
- [x] `variables.css`: global CSS variables (Bulma mapping, colors)
- [x] `base.css`: reset + base styles (skip-link, focus-visible, sr-only)
- [x] `utilities.css`: utility classes (`.mt-*`, `.gap-*`, `.min-w-*`, `.d-*`)
- [x] `components/`: buttons, cards, forms, tables, modals
- [x] `layout/`: header, footer, grid
- [x] `pages/`: dashboard (the only page with dedicated CSS for now)
- [x] `themes/dark.css` (eliminates the base-styles.css /
      dark-theme.css / fullcalendar-styles.css duplication — all dark
      mode consolidated into a single file)
- [x] `vendor/fullcalendar-overrides.css`: default FullCalendar overrides
      (outside the dark theme), separated from the rest of vendor
- [ ] Minification in production

### 3.2 JavaScript
- [x] `main.js`: entry point
- [x] `theme/theme-manager.js`
- [ ] ~~`calendar/`: fullcalendar-config.js, event-handlers.js~~ — does not
      exist as a separate module, see note below
- [ ] ~~`forms/`: validation.js, submission.js~~ — same, out of scope for
      now (form validation already covered by `validateFormAccessible`
      in `utils/accessibility.js`)
- [x] `notifications/toast.js`
- [x] `utils/`: dom.js, date.js, accessibility.js (no api.js —
      no centralized fetch/API call existed in script.js)
- [x] ES6 modules (import/export)
- [x] JSDoc (kept from script.js, no additional format added)
- [ ] Unit tests (Jest or Vitest) — no existing JS setup in the
      project (no package.json/node_modules for front-end tooling), not
      done for lack of time

### 3.3 Templates
- [x] Reusable Jinja2 macros (`macros/errors.html` — 9 error pages
      400/401/403/404/405/500/502/503/504 deduplicated)
- [x] Standardized HTML structure (405.html aligned on the same
      `<main role="main">` skeleton + aria attributes as the other 8 error pages)
- [x] SEO meta tags (description + robots noindex, internal app not
      meant to be indexed)
- [x] Resource-loading optimization (see note below —
      limited scope, honestly documented)
- ~~WCAG 2.1 AA accessibility~~ — out of scope (see above)

---

## 📝 Log

*(updated at each step)*

### 2026-07-11 — 3.1 CSS complete

Complete restructuring of `app/static/css/`: the 3 old files
(`base-styles.css` 660 lines, `dark-theme.css` 337 lines,
`fullcalendar-styles.css` 188 lines) are **deleted** and replaced by:

```
css/
├── variables.css                      (Bulma mapping, theme-agnostic)
├── base.css
├── utilities.css
├── components/{buttons,cards,forms,tables,modals}.css
├── layout/{header,footer,grid}.css
├── pages/dashboard.css
├── themes/dark.css                    ([data-theme="dark"] / .dark-mode only)
└── vendor/fullcalendar-overrides.css  (default FullCalendar styles)
```

No separate `themes/light.css`: the light theme is simply Bulma's
default state + `variables.css`, there is nothing to override.

**Duplication eliminated**: `fullcalendar-styles.css` repeated in its
own `[data-theme="dark"]` block almost all the rules already present
in `dark-theme.css` (`.fc`, `.fc-today`, `.fc-header-toolbar`,
`.fc-col-header-cell`, `.fc-day`, etc.). Everything is now consolidated
once in `themes/dark.css`.

**Bugs avoided along the way** (spotted before validation, fixed
before commit):
- `components/cards.css`: I had substituted `box-shadow: var(--shadow-md)`
  on `.box:hover` in place of the original literal value
  `0 4px 6px rgba(0,0,0,0.1)` — these are not the same values (different
  blur/offset), it would have changed the rendering. Restored the exact value.
- `components/buttons.css`: I had merged the general rule
  `.icon { vertical-align: middle; }` into `.button .icon { min-width/height }`,
  which would have restricted the general rule to buttons only. Split back
  into two separate rules.

**Tests updated**: `tests/test_dark_theme.py` and
`tests/test_theme_fixes.py` hard-coded the 3 old file names in
~20 assertions. Rewritten to point to the new files, keeping the
intent of each test (e.g. the `.is-warning` button contrast test
in dark mode now checks `themes/dark.css` instead of `dark-theme.css`).
`tests/manual_test_theme.py` is not picked up by pytest (file name
outside the `test_*.py` convention) — left as-is for now, not blocking.

One test (`test_dark_theme_css_content`) checked for the presence of the
string `prefers-color-scheme: dark`, which in reality only matched a
comment in the old file (no real `@media` rule — Bulma handles that
natively via its own variables). Assertion removed rather than
artificially reproduced: it wasn't testing anything real.

Full suite: **511 tests pass, 0 failures**. Verified under real
conditions (Flask dev server, login, dashboard, shifts page): all
14 CSS files load with 200, dark theme and FullCalendar visually
unchanged.

### 2026-07-11 — 3.2 JavaScript complete (actual scope)

`app/static/js/script.js` (673 lines) removed, replaced by:

```
js/
├── main.js                    (entry point, exposes window.Kairos)
├── theme/theme-manager.js     (ThemeManager class)
├── utils/
│   ├── dom.js                 (toggle/show/hide/addClass/removeClass/toggleClass)
│   ├── date.js                (formatDate/formatTime/formatDateTime)
│   └── accessibility.js       (screen reader announcements, focus, keyboard
│                                navigation, form validation, accessible
│                                confirmation modal)
└── notifications/toast.js     (showNotification, confirmAction)
```

`base.html` loads `main.js` as `<script type="module">` instead of the
classic `<script>`.

**Correction relative to the initial plan (same as for the line-count
estimate)**: the plan called for a `calendar/` folder (FullCalendar
config, event handlers) and a `forms/` folder. This doesn't exist in
`script.js` — the FullCalendar config (~576 lines) is an inline
`<script>` in `index.html`, heavily templated with Jinja2 (`{{ url_for(...) }}`
URLs, CSRF token, server-injected user data). Extracting it into a
static module would require passing that data through `data-*`
attributes or a JSON blob — a separate and riskier undertaking,
deliberately left aside here rather than rushed. `utils/api.js` was
also not created: `script.js` contained no centralized `fetch` call
to extract.

**Safety check before converting to a module**: the 35 uses of
`Kairos.*` in templates (`onclick="Kairos.confirmActionAccessible(...)"`
etc.) are either `onclick` attributes (executed only on user click,
well after the page has fully loaded) or asynchronous FullCalendar
callbacks in `index.html` — no synchronous call during HTML parsing.
A `<script type="module">` is deferred (like `defer`): so it doesn't
break any of these calls.

Verified: all JS files return `Content-Type: text/javascript`
(required for the browser to accept ES6 modules), the import chain
resolves correctly (`main.js` → `theme-manager.js` →
`accessibility.js`, etc.), `node --check` reports no syntax error on
the 6 files. `tests/manual_test_theme.py` updated alongside the pytest
tests (same old hard-coded paths).

Full suite: **511 tests pass, 0 failures**.

### 2026-07-11 — 3.3 Templates complete (without WCAG, as requested)

**Jinja2 macros**: the 9 error pages (`400.html` through `504.html`)
were nearly identical (same `<main>`/`box`/title/subtitle/buttons
skeleton, ~50-70 lines each, ~450 cumulative lines of actual
duplication). Extracted into `app/templates/macros/errors.html` — a
parameterized `error_page` macro (code, title, subtitle, color, primary
button, optional secondary buttons, login toggle) with a `{% call %}`
block for content specific to each page. Each page goes from ~50-70
lines to ~10-20 lines.

**Standardized HTML structure**: `405.html` was the only error page
not following the same skeleton (a bare `<div>` instead of
`<main role="main">`, no `aria-labelledby`/`aria-describedby`
attributes, buttons without `aria-label`). By routing it through the
common macro, it now has the same structure as the other 8 — not a
WCAG audit, just the cross-page consistency requested by this ticket.

**Real bug caught by the tests before commit**: macros imported via
`{% from "macros/errors.html" import error_page %}` do NOT have access
to the calling template's context by default in Jinja2 (standard
behavior, not a Flask bug) — `current_user` was `undefined` inside the
macro even though it's injected by Flask-Login into the render context.
Fixed with `{% from "macros/errors.html" import error_page with context %}`
on all 9 pages. Without `tests/test_error_handlers.py` (which renders
each template directly), this bug would have gone unnoticed until a
real error page was served in production.

**SEO meta tags**: `base.html` had a minimal `<head>` (charset,
viewport, title, favicon) with no `<meta name="description">` tag and
no robots directive. Added an overridable `meta_description` block
(generic default value) and `<meta name="robots" content="noindex,
nofollow">` — this is a team-internal scheduling app, not meant to
appear in a search engine.

**Resource-loading optimization — honest scope**: no build pipeline
(webpack/vite) in this project, so no bundling/minification possible
without adding one (already flagged as not done in the Minification
item of 3.1). The real optimization achievable without additional
tooling — vendor assets already served locally (achieved in Phase 1),
scripts already placed at the end of `<body>`, `main.js` already loaded
as a deferred module — was already in place before this step. The
CSS/JS splitting in steps 3.1/3.2 mechanically increased the number of
requests (12 CSS + 6 JS instead of 3 CSS + 1 JS); HTTP/2 (already used
in production per the existing Talisman config) multiplexes these
requests over a single connection, so the real impact is likely
negligible, but not measured here for lack of a profiling tool in
place. Documented rather than left unmentioned.

Full suite: **511 tests pass, 0 failures**. Verified under real
conditions (Flask dev server): actual 404 page rendered correctly with
the macro.

Phase 3 complete: 3.1 CSS, 3.2 JavaScript, 3.3 Templates — all done,
WCAG 2.1 AA excluded as validated upstream.

---

*Last updated: 2026-07-11*
