# Roadmap

**Current version: 1.2.0** — feature-complete, tested (2000+
automated tests), and used for real team scheduling.

## ✅ Done

**Core scheduling**
- Shift scheduling with day/week/month calendar views, drag & drop
- On-call rotations, generated automatically with a legal minimum
  rest period enforced between two on-call weeks
- Leave management, integrated into the same calendar
- Shift swaps between users, with a three-party approval flow
  (requester → target confirms → admin approves)
- User and group management, with per-group participation in
  scheduling/on-call
- Main calendar shows a color-coded dot per event's group (with a
  legend) and a multi-group filter, on top of the existing per-type
  colors (shift/on-call/leave); clicking an event opens a view/edit
  modal (admins can reassign the user, type, or time) instead of the
  old click-to-delete-only toggle
- `/schedule`, `/oncall`, and `/leave` share one filter bar (user,
  group, date range) plus a unified "delete filtered result"/"delete
  selection" action, replacing what used to be six separate
  single-purpose bulk-delete buttons
- Dashboard stat cards count days, not rows (a multi-day on-call or
  leave used to inflate the count), with a month-over-month trend
- ICS export collapsed to one button/modal per resource type, scoped
  by group and by "me"/"everyone" inside the modal, reused as-is on
  the profile page instead of six static links

**Automation**
- Rule-based automatic shift generation (on-call coverage, rotation,
  weekend handling, maximum staffing)
- Automatic rebalancing of shifts and on-calls when a leave is added
- If a rule can't be satisfied (e.g. no one eligible for on-call
  duty), the affected slot is left unfilled and admins are notified
  instead of silently breaking the rule
- Configurable automation rules, admin-editable at
  `/admin/automation/rules`: weekend definition, on-call spacing/week
  anchor, shift slots (which `ShiftType` covers on-call/rotation/
  default), maximum staffing per shift type, minimum rest after an
  on-call, and shift/on-call overlap blocking. Each rule's default
  matches the previously hardcoded behavior exactly. Org-wide for now —
  see "Future ideas" for per-group rules. (Minimum staffing and a
  separate "mandatory slots" rule existed briefly but were removed —
  coverage for the rotation/on-call shift types is already guaranteed
  by the generation algorithm itself, so the extra min/mandatory layer
  only produced confusing, occasionally-false "unfilled" alerts.)
- Per-group scoping (`shift_scheduling_mode`/`oncall_scheduling_mode`)
  covers every generation entry point, including the narrower ones
  (filling on-call gaps, refreshing a period, rebalancing after a
  leave) — not just the main "Générer" action
- A rewritten, pure generation planner (`app/utils/automation/planner/`):
  computes a plan (a `GenerationRun`) as data first, then applies it
  atomically, instead of the legacy engine's read-modify-write-as-you-go
  approach. Dry-run preview always uses it; real generation/refresh/
  leave-rebalance stay on the legacy engine until an admin opts in via
  the **Moteur d'automatisation** toggle on `/admin/automation/rules`
  (off by default — a diagnostic legacy-vs-new comparison mode confirmed
  parity, and the toggle lets a production rollback happen without a
  code revert if an issue surfaces post-cutover)

**Access & integration**
- Session login and SSO/OIDC (Keycloak, Okta, Auth0-compatible
  providers)
- ICS calendar export (Google Calendar, Outlook, etc.), by token or
  session
- A read-only public REST API (`/api/v1/*`) with its own
  service-account tokens, for third-party integrations, including
  `GET /api/v1/oncall/current` for monitoring/alerting integrations
  that need "who's on-call right now"; on-call datetimes are
  timezone-aware ISO 8601 strings
- Outbound notifications to Slack/Discord/Telegram/webhooks (via
  Apprise), plus in-app and email reminders
- ICS export tokens expire automatically (admin-configurable duration)

**Security**
- Static code analysis (Bandit) and dependency vulnerability scanning
  (pip-audit, no API key required), run automatically on GitHub Actions
  before every release, once a week, or on demand

**Operations**
- Multi-language (French/English) and multi-timezone, per user or
  organization-wide, including on-call status computed in the
  organization's own timezone rather than the server's
- An audit trail of who changed what, browsable by admins
- Database backups (local or S3-compatible), schedulable via cron or
  triggered from the admin UI
- Prometheus metrics and Kubernetes health/readiness endpoints
- Docker image and Kubernetes manifests provided for deployment

**Optimization & release prep**
- A dedicated optimization/bug-hunt pass over the code that landed this
  cycle (the automation rules engine, per-group scoping, dashboard,
  calendar JS) — this code hadn't had one yet, unlike the pre-1.1.0
  codebase's dedicated 1.0.0 security audit/bug hunt/load test. Fixed:
  a crash (500) on `/schedule`/`/oncall`'s "delete filtered result" when
  a group filter was active (`Query.delete()` on a query with `.join()`
  already applied — SQLAlchemy rejects that combination), a dashboard
  stat inconsistency (on-call `this_month` could exceed `total`), two
  real i18n bugs (a weekday-label list frozen to whichever locale was
  active at process startup instead of resolving per-request; 12
  "Admin" breadcrumb labels never routed through `_()`), a filter-bar
  bug (one malformed date field discarded the other, already-valid
  one), a data-loss edge case where a per-group "regenerate" deleted a
  group's on-calls/shifts without recreating them if that group had
  since been toggled out of rotation eligibility (delete is now scoped
  to exactly the groups about to be regenerated), and an N+1 in the
  scheduling-mode setting lookups plus the whole configurable
  automation rules engine's resolution path (both now cached on
  `flask.g`, same pattern as the timezone/date-format resolvers — a
  multi-week schedule generation run went from one `AutomationRule`
  query per rule *per day* to one per rule for the whole run). Also
  converted `/dashboard`'s shift stats from an unbounded full-history
  Python fetch to a single SQL aggregate query (`Shift` specifically —
  the dominant volume driver; `OnCall`/`Leave` stay Python-side, see
  `Docs/reference/PERFORMANCE_OPTIMIZATION.md` for why). Added a
  composite DB index on `AutomationRule(rule_type, group_id)`. Test
  suite parallelized via pytest-xdist (`make test`), ~3.3x faster (548s
  → 166s on 4 cores).
- `CHANGELOG.md` introduced — kept up to date between releases from now
  on, alongside this file.
- 1.1.1 cycle: a real-browser QA sweep and a round of production bug
  reports drove a long tail of on-call/rotation-generation fixes (wrong
  rotation-order epoch on non-"today" generation windows, a
  `staffing_limits` shape crash, false `rest_after_oncall` blocks, and
  several rotation-order/coverage bugs specific to mixed
  shared/per-group scheduling) plus smaller UI/i18n/accessibility fixes
  — see `CHANGELOG.md`'s `[1.1.1]` entry for the full list.

## 🔧 In progress

Nothing currently in flight — everything for this cycle is already
listed under "Done". 1.1.1 has completed its release-QA pass and is
being tagged/published.

## 🔭 Future ideas

Larger features, not yet started, not committed to a timeline.

- **On-call intervention reports.** A way to log what happened during
  an on-call shift (time spent, actions taken) — useful both for
  payroll and as an audit trail of interventions.
- **New access-control roles**, beyond today's admin/user split (e.g.
  HR, auditor) — for people who need to see scheduling data without
  being able to change it.
- **Write support on the public API v1.** `/api/v1/*` is deliberately
  read-only today (listing shifts/on-call/leave/users) — adding
  create/update/delete would mean re-validating the same
  conflict/weekend/leave rules already enforced by the internal
  session-based routes, without duplicating that logic. A real
  candidate for a v2, not started yet.

## Contributing

Kairos was built almost entirely with AI coding tools by someone
without a professional development background — see the README for
the full story. Code review, bug reports, and contributions from
experienced developers are genuinely welcome, on either list above or
anything else you find. Start with an
[Issue](https://github.com/FoxOps/kairos/issues) or a
[Discussion](https://github.com/FoxOps/kairos/discussions).
