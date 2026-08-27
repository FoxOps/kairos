# Changelog

All notable changes to Kairos are documented in this file, starting from
this entry onward — kept up to date between releases from now on. Format
loosely follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versions match the bare (no `v` prefix) git tags this project actually
pushes, e.g. `1.1.0`, not `v1.1.0` — see `.github/workflows/tests.yml`'s
tag trigger for why.

## [1.1.1] — 2026-08-27

### Fixed
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
