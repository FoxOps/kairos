# Changelog

All notable changes to Kairos are documented in this file, starting from
this entry onward — kept up to date between releases from now on. Format
loosely follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versions match the bare (no `v` prefix) git tags this project actually
pushes, e.g. `1.1.0`, not `v1.1.0` — see `.github/workflows/tests.yml`'s
tag trigger for why.

## [1.2.0] — 2026-11-17

Planner-only automation (legacy engine removed), a schedule-generation
fix from production, the fixes for every finding of the 1.2.0 external
audit, and dependency security bumps - see "Removed"/"Fixed"/"Changed"/
"Security" below.

Public API v1 (`/api/v1/*`) maturity pass - OpenAPI contract
correctness, server-side filtering, a new `groups` resource,
configurable rate limits, ServiceAccount scopes, and interactive
documentation. See [`Docs/api/API.md`](Docs/api/API.md#public-api-v1-service-accounts)
for the full contract.

### Added
- `GET /api/v1/groups/[/<id>]` - resolves the `group_id` values already
  present on shifts/on-calls/leaves/users to a name (previously
  unresolvable through the public API). Unpaginated, like `shift-types`.
- Server-side filtering on every public API list endpoint:
  `user_id`/`group_id` on shifts/on-call/leave/users, `start`/`end`
  date-range (overlap semantics) on shifts/on-call/leave, `shift_type_id`
  on shifts. Invalid filters (`start` after `end`, an unparseable date)
  return `422`. Previously these repository-level filters existed but
  were never wired up to the public API resources.
- ServiceAccount read scopes (`read:shifts`/`read:oncall`/`read:leave`/
  `read:users`/`read:shift_types`/`read:groups`, or `read:*`),
  admin-editable at `/admin/service-accounts`. No scope checked = full
  access, the default and unchanged behavior for every ServiceAccount
  that existed before this change. A token used outside its granted
  scopes gets `403`.
- `API_RATE_LIMIT` env var - the public API's per-ServiceAccount rate
  limit (previously a hardcoded Python constant) is now
  administrator-configurable, default unchanged
  (`60 per minute, 1000 per day`). `RATE_LIMIT_STORAGE_URI` env var -
  Flask-Limiter counter storage backend (default `memory://`,
  unchanged), can be pointed at `redis://...` for a multi-worker/
  multi-replica deployment.
- `GET /api/v1` - small discovery document (name/version/links).
- `GET /api/v1/docs` - interactive Scalar documentation, served from an
  already-CSP-whitelisted CDN origin (no CSP change). Gated by
  `PUBLIC_API_DOCS_ENABLED` (default on); the raw
  `/api/v1/openapi.json` stays reachable regardless.
- Generated OpenAPI document now includes `servers` (from
  `PUBLIC_BASE_URL`, or a safe relative `/`), a `ServiceAccountBearer`
  Bearer security scheme applied globally, stable `operationId`/
  `summary`/`description` on every operation, explicit types/formats on
  every field (duration fields are now numeric, not untyped; every
  datetime is `format: date-time`), and documented `401`/`403`/`404`/
  `422`/`429` responses per operation.

### Changed (breaking)
- `GET /api/v1/oncall/current` now **always** returns
  `{"items": [...], "count": N}`, regardless of `group_id` - previously
  the response type changed (array vs. single object vs.
  `{"active": false}`) depending on `group_id` and the number of
  matches, which was unsafe for generated clients.
- `GET /api/v1/users/` is now **paginated** (`{"items", "page", "pages",
  "per_page", "total"}`, same envelope as shifts/oncall/leave), and
  accepts a `group_id` filter - previously a bare unpaginated array.
- Every public API error response body changed shape, from
  `{"message": "..."}` to
  `{"error": {"code", "message", "details"}}` - `code` is a stable
  machine-readable value (`not_found`, `validation_error`,
  `rate_limited`, ...), `details` carries structured per-field detail
  for `422`.

### Removed
- **The legacy scheduling engine.** The planner introduced in 1.1.1 is
  now the only shift/on-call generation engine, for "Générer",
  "Recalculer les shifts" and the automatic rebalance after a leave.
  The "Moteur d'automatisation" toggle on `/admin/automation/rules`
  and `scripts/compare_automation_engines.py` are gone. An existing
  `new_automation_engine_enabled` setting row is ignored, so no
  migration is needed. **Behaviour change** for any instance that
  never turned the toggle on (it defaulted to off): real generation
  now uses the planner, which the "Aperçu (Dry Run)" preview already
  used, so the schedule you get now matches the preview. One visible
  difference: "Régénérer entièrement" follows the configured rotation
  order and no longer keeps each week's existing on-call holder. Use
  "Combler les trous" to keep existing on-calls. See
  [`report/1.2.0/BUG_HUNT_1.2.0.md`](report/1.2.0/BUG_HUNT_1.2.0.md).

### Fixed
- **Generated schedules missing a person on Mon–Thu of every other
  week** (production report). The rotation slot (07h-15h) used to go
  to both last week's and next week's on-call holder. With that slot
  capped at 1 person (`staffing_limits`), the second one got no shift
  at all. Now: last week's on-call holder gets it; if they're not in
  the group, next week's holder (on a transition Friday, the person
  whose on-call starts that evening); otherwise the rotation-order
  fallback.
- A user who would exceed a slot's staffing maximum now gets the
  default slot instead of being dropped for the day. They are left
  unassigned only if the default slot is full too.
- The first week of a generation now sees the on-call already
  published right before it as "last week's on-call".
- The "Aucun shift généré automatiquement (aucun utilisateur
  disponible)" notification fired for days where users *were*
  available but a slot's staffing maximum was reached. It now fires
  only for days where every eligible user is absent, a case the
  planner used to drop silently. A reached staffing maximum is
  reported as a `[WARN]` in the generation result only.
- Three planner bugs that could delete data, found while removing the
  legacy engine. They were hidden because the planner was off by
  default:
  - With `per_group` on-calls, another group's concurrent on-call
    could be deleted (rows without a `group_id` snapshot collided).
  - The on-call ending on the window's first anchor day was deleted,
    for example when appending a second generation right after a
    first one.
  - Shifts of a group toggled out of the schedule were deleted on
    regeneration.
- **1.2.0 audit findings** (see
  [`report/1.2.0/AUDIT_REPORT_1.2.0.md`](report/1.2.0/AUDIT_REPORT_1.2.0.md)
  and the fix mapping in
  [`report/1.2.0/AUDIT_FIXES_1.2.0.md`](report/1.2.0/AUDIT_FIXES_1.2.0.md)):
  - Generation checks rest after on-call on each shift's *final* hours,
    after a staffing-max fallback (an under-rested shift could be
    saved), enforces the optional "on-call/shift overlap" block, counts
    locked shifts against staffing maxima first, and re-covers the
    rotation slot when its holder is excluded by a rule (else a new
    `[WARN]` "créneau de rotation non couvert").
  - Locked on-call weeks now constrain the spacing search ("Combler les
    trous" could give the same person two weeks 14h apart).
  - Any on-call anchor weekday now gives the right person the on-call
    shift role; the anchor day itself stays the outgoing holder's, as
    with Friday.
  - Regeneration detects and repairs shifts/on-calls whose hours were
    edited by hand.
  - A plan computed before a leave/assignment/population change is
    refused at apply time instead of being applied stale; concurrent
    applies are serialized.
  - Manual on-call creation/moves enforce the configured spacing,
    positive duration, anchor day *and* hour and weekly end; shift API
    create/move validate the actual hours saved. Every rejection says
    which rule blocked it.
  - Shift swaps validate locks, weekend and the configured
    staffing/rest/overlap rules; a same-day reciprocal swap no longer
    fails on a database constraint; the shift's group snapshot follows
    its new owner; reverting re-validates.
  - Leave rebalance refused as unsafe (e.g. locked shift on the new
    leave's day) is reported as a failure and notified, not as success.
  - Leave minimum headcount is per group in `per_group` shift mode.
  - Leave ICS export: all-day events, last day no longer dropped.
  - Fairness metrics include eligible users with zero assignments.
  - Model indexes aligned with the migrated schema.

### Changed
- Unticking "Inclure" on the rotation order form now **excludes** the
  person from on-call rotation (it used to put them back at the end).
  People joining an eligible group later are included by default.
- "Aperçu (Dry Run)" no longer saves the rotation order or resets the
  rotation phase; only "Générer" does.
- An on-call can no longer be resized in the calendar to end anywhere
  but its configured weekly end.

### Security
- **SSO-only mode bypass** (audit F01): with `OIDC_DISABLE_BASIC_AUTH`,
  `POST /login?oidc_error=1` still accepted a local password. Password
  POSTs are now always refused in SSO-only mode.
- **SSO account takeover via unverified email** (audit F02): local
  accounts are now bound to the IdP identity (issuer + `sub`, migration
  `7d2c1e9a5b30`); the first SSO login of an existing local account is
  refused when the IdP marks the email unverified, unless the new
  `OIDC_TRUST_UNVERIFIED_EMAIL=true` is set. **Upgrade note (Keycloak):**
  users created by an admin default to "Email verified: Off" - turn it on
  for accounts that already exist in Kairos, or set the flag if users
  can't choose their own email. OIDC `state` values are no longer
  logged, and the state is single-use.
- Bumped `Werkzeug` 3.1.8 → 3.1.9, `Authlib` 1.7.2 → 1.9.1 and `black`
  26.5.1 → 26.10.1. `pip-audit` reported 11 known vulnerabilities in
  these packages, and the weekly `Tests` workflow had been failing on
  that since 2026-10-12.

## [1.1.1] — 2026-09-16

### Added
- `GET /api/v1/oncall/current[?group_id=]` - returns the currently
  active on-call shift(s) (resolved server-side using the org's
  configured timezone, same comparison as `OnCall.is_active()`),
  including the on-call user's name/email inline, for monitoring/
  alerting integrations (e.g. Canopsis) that need "who's on-call right
  now" without pulling the full on-call list and re-implementing the
  timezone/active-window logic themselves. Without `group_id`, returns
  a JSON array (0+ items - more than one only possible in `per_group`
  on-call scheduling mode); with `group_id`, a single object, either
  the active shift or `{"active": false}` - unless more than one
  on-call is genuinely concurrent within that group, in which case it
  falls back to the same array shape rather than silently dropping one
  (**[Bug-hunt pass]** fixed before this endpoint's first release: it
  originally always returned just the first match).

### Changed
- `start_time`/`end_time` across `/api/v1/oncall/*` (list, detail, and
  the new `current` endpoint above) are now timezone-aware ISO 8601
  strings (e.g. `2026-09-11T21:00:00+02:00`, using the org's
  `default_timezone` `Setting`) instead of a bare, timezone-less
  string - safer for external integrations, which previously had to
  assume the org's timezone out-of-band.
- Docs corrected against actual code, found stale during this cycle's
  API doc audit: `Docs/api/openapi.yaml`/`Docs/api/API.md` were
  missing `GET /api/oncall-users`, `group_ids` on `GET /api/shifts`,
  and the `userId`/`shiftTypeId` reassignment fields on
  `PATCH /api/shifts/<id>`/`PATCH /api/oncall/<id>`; the on-call PATCH
  docs also still claimed a hardcoded Friday anchor, stale since the
  configurable `OnCallAnchorRule` per-group anchor weekday landed.
  Documentation-only, no behavior change.
- Automation rules page: "Créneaux obligatoires" section removed and
  "Effectif minimum/maximum par créneau" is now "Effectif maximum par
  créneau" - the min/mandatory-shift settings were confusing (they only
  ever meant "alert if this structurally-guaranteed slot can't be
  filled", not a real, independently-enforceable staffing minimum), so
  they were removed rather than clarified.

### Fixed
- Generating/previewing on-calls for a period far from the real
  wall-clock date (a dry-run preview or backfill for a future/past
  period, or simply this project's own CI running on a different day
  than the tests were written) could silently put the wrong person
  on-call first: `generate_full()` reset the rotation-order reference
  date ("epoch") to real `date.today()` on every call regardless of
  the actual generation window's `start_date`, so `rotation_order[0]`
  only landed on offset 0 - the configured "first" person - when the
  window happened to start near today. Now resets to the window's own
  `start_date` instead, so the configured order's first entry is
  deterministically first for whatever period is actually being
  generated, independent of when the call runs.
- Automation "Générer/rafraîchir le planning" could fail outright with
  `'>=' not supported between instances of 'int' and 'dict'` whenever a
  `staffing_limits` rule had been saved under this rule's pre-1.1.1
  shape (`{"min": .., "max": ..}` per `ShiftType`, before it became
  max-only) - `resolve()` is a raw passthrough of whatever JSON is
  already stored, with no shape check on read, so a stale row from
  before the shape change crashed the whole generation. Now coerced to
  "no limit configured" (same as an absent entry) instead of
  propagating a dict where an int is expected.
- Automation "Générer/rafraîchir le planning" could fail on every day of
  a multi-month generation run with a flood of false `rest_after_oncall`
  `hard_blocked` violations: the planner picked each user's on-call end
  time as the single latest one across the *entire* planning window
  instead of the most recent one that had actually already happened by
  the day being planned, so an on-call scheduled months later falsely
  blocked shifts earlier in the same run.
- Same "Générer/rafraîchir le planning" action still refused to apply
  even after the fix above: a routine, already-excluded
  `rest_after_oncall` case (the departing on-call holder's own
  same-day rotation slot, right when their on-call just ended) was
  tagged as a plan-breaking `hard_blocked` violation instead of a
  non-fatal `warning`, so the entire multi-month apply was refused
  the moment any single transition day hit this normal, expected
  exclusion — any org with a `rest_after_oncall` minimum configured
  could never apply a generation run at all.
- On-call rotation order ignored on a fresh/reordered rotation: the
  rotation phase stayed pinned to a fixed year-2000 reference date
  forever (no way to reset it), so the first user actually put
  on-call after saving a new order was an arbitrary position, not
  rotation order's own first entry. Saving the order now resets the
  rotation phase so the very next on-call turn starts from position 0.
- The on-call user's own mandatory coverage shift (the "oncall" role
  slot, e.g. 13h-21h on the transition day) could be excluded by
  `rest_after_oncall` — comparing it against the on-call that had
  *just* ended that same morning — leaving that mandatory slot
  permanently unfilled every single week for any org with this rule
  configured. On-call and its own coverage shift are meant to
  coexist; `rest_after_oncall` now only applies to unrelated
  ("rotation"/"default") shifts.
- Automation flash messages were never aggregated on the new planner
  engine (unlike the legacy one, which already had this fix): a
  recurring gap over a multi-month run produced one flash toast per
  occurrence, sometimes hundreds. Now grouped into one message per
  shift type/rule with a count and date range.
- Purging read notifications used the browser's native `confirm()`
  dialog instead of the app's own modal.
- Sidebar avatar letter was slightly off-center.
- Automation rules page: the scope selector and its description text
  could wrap onto separate, inconsistently-positioned lines.
- Rotation order still not respected after the fix above: the new
  engine only ever read the rotation order from its stored
  configuration, never from whatever an admin currently had
  checked/ordered on the generation form itself — clicking "Générer"
  without a separate, easy-to-miss prior "Sauvegarder l'ordre" click
  silently fell back to alphabetical order. Generating now always
  persists the submitted order first (only resetting the rotation
  phase when the order's content actually changed, to avoid
  re-shuffling an already-running rotation on a routine repeat call).
- The on-call user's own mandatory coverage shift stayed permanently
  unfilled in the "shifts shared across the whole org, on-calls
  per-group" configuration specifically: a single shared shift scope
  can have several different groups each running a concurrent
  on-call, but the lookup only ever checked one group's on-call at a
  time, silently missing every other group's holder every single
  week regardless of any other rule.
- Calendar day-click "create shift" modal let an admin freely type an
  arbitrary multi-day/multi-hour range instead of just creating a
  shift for the clicked day; the shift's hours are now always taken
  from the chosen shift type, like everywhere else in the app. The
  calendar's create/update/delete actions also only ever announced
  success/failure to screen readers (an invisible aria-live region) —
  a sighted admin got no visible confirmation of success and no
  visible error message at all on failure. These actions now also
  show a real flash message, same as every other page.
- Shift generation rotation, two compounding bugs in a group whose
  on-call turns are sparse (e.g. `oncall_scheduling_mode` shared/pooled
  across several groups while `shift_scheduling_mode` is per-group) —
  reported as "the same shift order repeats every week" on long (6+
  month) generation runs:
  - A user due on-call the *following* week is now also considered for
    the 7am-3pm rotation slot (previously only "on-call last week" was
    checked), so a group gets a second, forward-looking chance to vary
    the assignment instead of defaulting everyone to 9am-5pm.
  - When neither check matches anyone, the minimum-coverage fallback
    that force-assigns one person to 7am-3pm (guaranteeing the slot is
    never left empty) now rotates through the configured rotation
    order by week instead of always picking the same person - it was
    previously static, so a group stuck relying on this fallback for
    consecutive weeks saw the identical person on 7am-3pm indefinitely.
- Rotation order still not respected on regenerate, still present after
  the fixes above (two compounding bugs, both fixed): the new engine's
  solver kept whoever was already published for a given on-call week
  ahead of the freshly configured order's first pick, and the rotation
  phase's reference date only ever reset when the submitted order's
  *content* changed - regenerating a range that had already been
  generated once (e.g. after clearing it for testing) kept the old,
  possibly-stale pick either way. Regenerating now always follows the
  currently configured order for any non-locked week.
- Regenerating a day where several users get reassigned at once (now a
  routine outcome of the fix above) could raise `UNIQUE constraint
  failed: shift.user_id, shift.date` and abort the whole apply -
  SQLAlchemy's autoflush could batch a new assignment's INSERT ahead of
  the old one's DELETE for unrelated users on the same day.
- The mandatory on-call coverage shift (e.g. 13h-21h) was flagged
  "unfilled" whenever that week's on-call holder belonged to a
  different group than the shift schedule being generated (a
  `shift_scheduling_mode=per_group` + `oncall_scheduling_mode=shared`
  combination) - structurally impossible to fill by design, not an
  actual gap. The separate min/mandatory coverage layer that produced
  this false alert (`mandatory_shift` rule type, and the `min` half of
  `staffing_limits`) has been removed outright: coverage for the
  rotation/on-call shift types is already guaranteed by the generation
  algorithm itself, and the min/mandatory settings only added confusing,
  occasionally-misleading configuration on top of it.
- i18n was silently 100% non-functional on a plain bare-metal setup
  (`pip install` then `python run.py`, this project's own documented
  quick-start): the compiled `.mo` translation catalogs were only ever
  produced by the Docker image build or the test suite's own fixture,
  never by this path, so every locale silently fell back to French
  regardless of any language setting. `create_app()` now compiles any
  missing catalog itself on startup as a safety net.
- Shift/on-call reassignment via the calendar's click-to-edit modal
  failed completely silently on a rejected save (conflict, leave
  overlap, rule violation, etc.) - the server's error message only
  reached a screen-reader-only ARIA live region, invisible to sighted
  users, unlike every other error path in the same file. Now shown as
  a real visible flash message, same as drag & drop and delete.
- ICS calendar export was entirely invisible on `/schedule`, `/oncall`,
  and `/leave` (no button, no hint) for any user who hadn't already
  generated an ICS token from their profile - including the fresh
  bootstrap admin. A link to generate one now shows in its place.
- `/oncall/add`'s label and help text always claimed the on-call must
  start on Friday at 21h, even for a group with a different configured
  anchor day - correct submissions could look wrong and incorrect ones
  looked right, and the mismatch caused real rejected submissions.
- The auto-generated bootstrap admin password could be silently lost
  on a bare-metal start: Python's stdout is block-buffered when not
  attached to a TTY (e.g. `nohup`/`systemd`), so the one-time password
  print could sit unflushed indefinitely. Now flushed explicitly.
- `/admin/automation` and the automation "Dry Run" preview page had no
  browser tab title, unlike every sibling admin page.

## [1.1.0] — 2026-08-07

### Added
- Configurable automation rules engine, admin-editable at
  `/admin/automation/rules`: weekend definition, on-call spacing/anchor,
  shift slots, min/max staffing per shift type, mandatory slots, minimum
  rest after an on-call, shift/on-call overlap blocking. Each rule's
  default reproduces the previously hardcoded behavior exactly.
- Per-group scheduling mode (`shift_scheduling_mode`/
  `oncall_scheduling_mode`), wired into every generation entry point
  (main generation, gap-filling, period refresh, post-leave rebalance),
  and resolved per-`Group` rather than only per eligible user.
- Main calendar: color-coded dot per event's group with a legend,
  multi-group filter, and a click-to-edit modal (admins can reassign
  user/type/time) replacing the old click-to-delete-only toggle.
- `/schedule`, `/oncall`, `/leave` now share one filter bar (user, group,
  date range) and a unified delete-filtered/delete-selection action,
  replacing six separate single-purpose bulk-delete buttons.
- ICS export collapsed to one button/modal per resource type, scoped by
  group and by "me"/"everyone", reused as-is on the profile page instead
  of six static links.
- Dashboard stat cards now count days instead of rows (a multi-day
  on-call/leave no longer inflates the count), with a month-over-month
  trend.
- Admin breadcrumb trail with daisyUI icons.
- This CHANGELOG.
- A tiered (patch/minor/major) pre-release QA protocol
  (`Docs/reference/QA_PROTOCOL.md`, driven by the `release-qa` skill),
  formalizing the optimization/bug-hunt and doc-sync passes below into a
  repeatable process for every future release.

### Fixed
- `generate_full_schedule()` no longer discards mandatory-shift ALERT
  messages.
- Malformed `<form>` tag on the ICS settings card was swallowing the
  CSRF field.
- Settings-page accordion sections now closed by default.
- Repeated mandatory-shift/on-call flash messages collapse into one
  summary instead of flooding the page.
- Gender agreement on "tous/toutes les astreintes" in ICS export labels.
- Calendar: infinite/heavy re-render and low-visibility status dots.
- Calendar: hides out-of-rotation groups instead of showing everyone.
- Hardcoded strings found by a full i18n audit routed through `_()`.
- Flat typographic hierarchy and GitHub icon alignment in the footer.
- **[Optimization pass]** `/schedule` and `/oncall`'s "delete filtered
  result" 500'd whenever a group filter was active (bulk `Query.delete()`
  on a query already built with `.join()`, rejected by SQLAlchemy).
- **[Optimization pass]** Dashboard on-call stats: `this_month` could
  exceed `total` (whole-calendar-day counting vs. fractional-duration
  totaling gave inconsistent units).
- **[Optimization pass]** `/admin/automation/rules`' weekday labels were
  frozen to whichever locale was active at process startup instead of
  the viewer's own language.
- **[Optimization pass]** 12 "Admin" breadcrumb labels across the admin
  section were never routed through `_()`.
- **[Optimization pass]** The `/schedule`/`/oncall`/`/leave` date-range
  filter discarded an already-valid `date_from`/`date_to` whenever the
  *other* field was malformed.
- **[Optimization pass]** Per-group "regenerate" could permanently lose
  on-calls/shifts belonging to a group that had been toggled out of
  rotation eligibility after they were created — the delete was
  unscoped even under "per_group" mode, while the regeneration loop
  right after only recreates data for currently-eligible groups. The
  delete is now scoped to exactly the groups about to be regenerated.
- **[Optimization pass]** `/dashboard`'s shift stats returned
  `decimal.Decimal` instead of `int` for `this_month`/`last_month` on
  MySQL/MariaDB (its `SUM()` of an exact-numeric expression returns
  `DECIMAL`, unlike SQLite/PostgreSQL) — an inconsistent shape versus
  the on-call/leave stats, invisible under this repo's SQLite-only test
  suite. Found while dogfooding the new release QA protocol on this
  same release.
- **[Optimization pass]** The new `AutomationRuleType.resolve()`
  per-request cache had no invalidation path: a same-request
  `AutomationRule.set()` followed by another `resolve()` call would have
  silently returned the stale pre-save value. Not reachable by any
  current caller (the admin route always redirects after saving), but
  now enforced rather than left to that caller discipline. Also found
  while dogfooding the release QA protocol.

### Changed
- Automation status messages use plain-text severity tags instead of
  emoji markers.
- `/admin/settings` and `/admin/automation/rules` redesigned with
  grouped, collapsible sections.
- **[Optimization pass]** Scheduling-mode setting lookups
  (`get_shift_scheduling_mode`/`get_oncall_scheduling_mode`) and the
  whole configurable automation rules engine's resolution path
  (`AutomationRuleType.resolve()`) now cached per-request, fixing an
  N+1 in shift/on-call generation and rule validation — a multi-week
  generation run went from one `AutomationRule` query per rule *per
  day* to one per rule for the whole run.
- **[Optimization pass]** `/dashboard`'s shift stats (total/this-month/
  last-month) now computed with a single SQL aggregate query instead of
  fetching a user's entire shift history into Python on every load.
  On-call/leave stats stay Python-side (see
  `Docs/reference/PERFORMANCE_OPTIMIZATION.md` for why).
- **[Optimization pass]** Test suite parallelized with pytest-xdist
  (`make test`) — ~3.3x faster locally (548s → 166s on 4 cores).

## [1.0.0] — first stable release

First stable release. Security audit, targeted bug hunt, and load test
completed — see `report/1.0.0/SECURITY_AUDIT_v1.0.md`, `report/1.0.0/BUG_HUNT_v1.0.md`,
`report/1.0.0/LOAD_TEST_v1.0.md`. Full feature set at this point: shift/on-call/
leave scheduling with drag & drop, rule-based automatic generation with
legal rest constraints, shift swaps (three-party approval), SSO/OIDC, ICS
export, a read-only public REST API (`/api/v1/*`), outbound notifications
(Apprise/email/in-app), multi-language and multi-timezone support, audit
trail, database backups, Prometheus metrics, Docker/Kubernetes deployment.
