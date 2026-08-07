# Changelog

All notable changes to Kairos are documented in this file, starting from
this entry onward — kept up to date between releases from now on. Format
loosely follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versions match the bare (no `v` prefix) git tags this project actually
pushes, e.g. `1.1.0`, not `v1.1.0` — see `.github/workflows/tests.yml`'s
tag trigger for why.

## [Unreleased] — 1.1.0

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
completed — see `report/SECURITY_AUDIT_v1.0.md`, `report/BUG_HUNT_v1.0.md`,
`report/LOAD_TEST_v1.0.md`. Full feature set at this point: shift/on-call/
leave scheduling with drag & drop, rule-based automatic generation with
legal rest constraints, shift swaps (three-party approval), SSO/OIDC, ICS
export, a read-only public REST API (`/api/v1/*`), outbound notifications
(Apprise/email/in-app), multi-language and multi-timezone support, audit
trail, database backups, Prometheus metrics, Docker/Kubernetes deployment.
