# 📋 Report - UI/UX Overhaul: Modern, Responsive Design

**Branch**: `feature/ui-ux-refonte`
**PR**: [#103](https://github.com/FoxOps/kairos/pull/103) (draft)
**Start date**: 2026-07-12
**Status**: 🟢 Plan complete + real visual verification done (Playwright/Chromium, see Log)
**Base**: `main` (post overhaul Phases 1-6, commit `ae1c091`)

---

## 🎯 Scope (validated with the user)

- Keep Bulma 1.0.4 (already recent, no technical bug justifying a
  framework change) but go beyond simple fixes: a deep visual overhaul
  (palette, typography, layout, cards, spacing) — not just targeted
  fixes.
- Prioritize fixing the real responsive bug found during the audit:
  unusable mobile navigation menu (see below).
- Full breakpoint audit across all pages, not just the navbar.

## 🔍 Initial audit

### Real bug found: unusable mobile navbar

`app/templates/base.html` has a `<nav class="navbar ...">` with
`.navbar-menu` (7 links + user dropdown) but **no `.navbar-burger`
button** anywhere in the template, nor any JS logic to toggle
`is-active`. Yet Bulma hides `.navbar-menu` by default below 1024px
(`display: none`) until `.navbar-menu.is-active` is applied. Result:
on mobile/tablet, the navigation menu is **invisible and completely
inaccessible** - no way to reach Shifts/On-call/Leave/Admin/Profile/
Logout. Confirmed by exhaustive search
(`grep -n "burger" base.html app/static/js/`): zero results.

### State of the design system

- `app/static/css/variables.css` only maps `--bulma-*` to app-level
  names (`--color-primary`, etc.) with no customization at all -
  primary color = Bulma's default turquoise
  (`--bulma-primary-h: 171deg`), no brand palette.
- No spacing scale or consistent border radii defined beyond raw
  Bulma defaults.
- Bulma 1.0.4 already loads `Inter` as the default font
  (`--bulma-family-primary`), but no font file is vendored
  (`app/static/vendor/webfonts/` only contains Font Awesome) - `Inter`
  therefore silently falls back to system fonts (SF Pro/Segoe UI/
  Roboto depending on the OS). Not a bug (clean degradation), but
  noted: vendoring Inter would be a real visual win, out of scope for
  this pass (adding assets, license to check) - **deferred**, see the
  Deferred section below.
- CSS already well organized into layers (`base`, `components/`,
  `layout/`, `pages/`, `themes/dark.css`, `utilities.css`) - the
  structure is kept as-is, only the content is touched.
- Bulma 1.x re-themes via 3 HSL variables (`--bulma-primary-h/-s/-l`),
  all derived shades (00 to 100, invert, etc.) are computed
  automatically by Bulma - this is the right way to override, much
  more robust than redefining each shade by hand.

## 📐 Plan

1. [x] Fix the mobile burger menu (blocking bug, priority 1)
2. [x] New brand palette (HSL override of Bulma's primary - revised
   to a softer green/teal after feedback), rounder radius scale
3. [x] Refresh components: buttons, cards, forms, tables, modals
   (shadows, radii, spacing consistent with the new palette)
4. [x] Verify dark theme consistency with the new palette - Bulma
   derives dark-mode shades from the same base HSL variables, no
   additional change required
5. [x] Full responsive audit (tables on mobile, dashboard, forms,
   calendar) across the main pages (index, schedule, oncall, leave,
   admin) - led to the discovery of the 2 pages broken by the Phase 6
   CSP (see Log)
6. [x] Layout polish (header, footer, global spacing, stale color
   fallbacks in fullcalendar-overrides.css)

## ⚠️ Verification limitation

No browser rendering/screenshot tool available in this environment.
Verification was done via: a real dev server + `curl` (HTTP status,
presence of expected classes/attributes in the rendered HTML), CSS/JS
syntactic validity, variable consistency. **No pixel-by-pixel visual
verification** - to be done manually in a browser before merging.

---

## 📝 Log

### Mobile navbar menu (commit `6ffbdd5`)

`.navbar-burger` button added + `NavbarMenu` module
(`app/static/js/navbar/navbar-menu.js`) that toggles `is-active`/
`aria-expanded`, closes on link click and on Escape. Verified for
real (rendered HTML contains the burger correctly linked to the
`navbar-menu` id, JS loaded with 200 status).

### Brand palette (commit `043f9f7`, revised in `7700a10`)

First pass: indigo (243deg 75% 58%). **User feedback: too aggressive
on the eyes.** Returned to Bulma's original green/teal family
(171deg 100% 41%) but desaturated to stay soft: **168deg 70% 42%**.
Derived RGB (32, 182, 152) propagated everywhere the color was
duplicated in hard-coded form (focus ring, table hover, CSS
fallback). Softened border radii (0.375/0.5/1rem), shadows changed to
diffuse multi-layer shadows (`--shadow-sm/md/lg`).

### Components (commit `dd2f6e9`)

Buttons, cards, forms, tables, modals: radii/shadows made consistent
with `variables.css`. Bugs found along the way: input focus ring had
the old turquoise's RGB hard-coded (inconsistent with the new
palette); `.modal-card` had no responsive width below 600px nor
`overflow: hidden` (the squared-off head/foot backgrounds overflowed
the card's rounded edge).

### Dashboard + header/footer (commit `36c418d`)

**Real bug found**: `.chart-container` (the "Breakdown by shift type"
chart) had **no CSS rule at all**. `.chart-item` had `flex: 1` but
without `display: flex` on the parent that was useless - the bars
stacked vertically at full width instead of forming a side-by-side
chart, and `.chart-bar`'s inline `height: X%` couldn't resolve
anything without a reference height on the direct parent. Fixed
(fixed height + `align-items: stretch` by default + `overflow-x: auto`
if there are too many types). `.level` (Bulma) audit: the project's
override doesn't touch `flex-direction`, so Bulma's native mobile
stacking remains intact - not a bug. No dangerous fixed width found
elsewhere (systematic grep).

### Broad audit: 2 pages broken in production by the Phase 6 CSP (commit `a6fadf8`)

**Major discovery while auditing responsiveness**: the strict
`script-src 'self'` CSP (Phase 6) silently blocks (console error,
**no** HTTP error) any executable inline `<script>`. Phase 6's
regression test had only checked `index.html`. Static scan (regex
across all templates): **2 other pages still had an inline
`<script>`**, broken in production with nothing flagging it:

- `auth/ics_token.html`: every "Copy" button (token + 6 ICS export
  URLs) was a silent no-op. Externalized to
  `static/js/clipboard/copy-token.js` (7 functions deduplicated into
  a single `copyInputValue` helper), exposed via `window.Kairos`.
- `admin/automation/full.html`: on-call rotation order drag-and-drop
  entirely broken. Bonus: `saveRotationOrder()` was defined inside the
  `DOMContentLoaded` listener, so `onclick="saveRotationOrder()"` was
  **already broken even before the CSP** (incorrect function scope).
  Externalized to `static/js/automation/rotation-order.js`, fixing
  both bugs at once.

Regression test extended: a parameterized scan across 8 representative
pages (`test_page_has_no_inline_executable_script`) instead of a
single one, to prevent this type of regression from going unnoticed
again. Verified with CSP actually active (Talisman, not just
TestingConfig). 781 tests pass (8 new).

---

### Calendar audit + stale fallbacks (commit `b49d56b`)

Schedule/oncall/leave/admin audit: tables already inside
`.table-container` (overflow-x:auto), `.field.is-horizontal` already
natively handled by Bulma (stacks below 769px), `.level.is-mobile`
correct, `.column.is-one-fifth` (admin dashboard) already stacks at
full width below 769px. No additional blocking bug found - the navbar
and the dashboard chart were the app's two real structural issues.
`fullcalendar-overrides.css` had the same stale color fallbacks
(`#00D1B2`) and hard-coded 4px radii as the rest of the app before
this pass - fixed for consistency.

### Post-user-feedback fixes (commits `5aea4ef`, `3d3fc63`)

Direct visual feedback from the user, two confirmed real bugs:
1. `.empty-state i` icon offset to the left instead of centered -
   regression from my own commit `36c418d` (`display: block` prevents
   the parent's `text-align: center` from applying). Fixed with
   `inline-block`.
2. `/admin`: no gap between box rows that wrap (7 `is-one-fifth`
   cards across 2 rows). `grid.css` set `padding: 0 0.75rem` on
   `.column` (horizontal only), overriding Bulma's default vertical
   padding. Restored.

App version synced with progress (0.6.0 -> 0.7.0, both High priority
items of ROADMAP Version 0.7 - UI/UX overhaul and interactive
calendar - are now done). Side bug found along the way: two
duplicated `APP_VERSION` defaults (`health.py` and `__init__.py`),
only the first had been bumped, the footer stayed stuck on the old
value - unified into a single constant.

### Real visual verification (Playwright/Chromium, commit `6fd3de1`)

At the user's explicit request: set up an isolated Playwright +
Chromium environment (disposable venv in the scratchpad, doesn't
touch the project's dependencies), launched a real dev server, real
admin login, desktop and mobile screenshots of `/`, `/dashboard`,
`/admin`, plus browser console verification (not just the rendered
HTML).

**3rd CSP bug found** - undetectable by the textual scan used so far
(inline `<script>`) since it involves `font-src`, not `script-src`:
FullCalendar embeds its icon font (previous/next arrows) as an
`@font-face` `data:` URI in its own CSS. Without an explicit
`font-src` directive, CSP falls back to `default-src 'self'`, which
blocks `data:` - confirmed by the exact console error. The calendar
navigation buttons rendered as empty rectangles, with no chevron.
Fixed (`font-src 'self' data:` added to `CSP_POLICY`), reconfirmed
visually after the fix (0 console errors, chevrons visible).

Screenshots also visually confirm: correct soft teal/green palette,
up-to-date footer (0.7.0), centered empty-state, correct /admin
spacing, working calendar.

Playwright environment fully removed after use (not a project
dependency - `.venv/`, `requirements.txt` untouched).

---

*Last updated: 2026-07-12 — plan complete (13 commits): mobile burger,
palette (revised after feedback), components, dashboard, CSP audit (3
pages/elements broken found and fixed in total, including 1 via real
browser visual verification), full responsive audit, app version
synced. Ready for final human review before merge.*
