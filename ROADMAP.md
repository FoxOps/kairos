# Roadmap

**Current version: 1.0.0-rc3** — feature-complete, tested (1390+
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

**Automation**
- Rule-based automatic shift generation (on-call coverage, rotation,
  weekend handling, minimum staffing)
- Automatic rebalancing of shifts and on-calls when a leave is added
- If a rule can't be satisfied (e.g. no one eligible for on-call
  duty), the affected slot is left unfilled and admins are notified
  instead of silently breaking the rule

**Access & integration**
- Session login and SSO/OIDC (Keycloak, Okta, Auth0-compatible
  providers)
- ICS calendar export (Google Calendar, Outlook, etc.), by token or
  session
- A read-only public REST API (`/api/v1/*`) with its own
  service-account tokens, for third-party integrations
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

## 🔧 In progress

**1.0.0-rc3** — addressing feedback reported against `1.0.0-rc2`
(tagged, see the `1.0.0-RC2` tag/release). Landed so far (PR #167-181):
a guaranteed minimum 7am-3pm shift presence (previously a real gap
could open on 7-9am/5-9pm with certain leave/availability combinations);
minimal-perturbation on-call rebalancing (a leave no longer reshuffles
weeks it doesn't actually touch); a fixed admin notification gap for
automation failures; three related on-call boundary bugs where a
rebalance/regeneration deleted the astreinte straddling its start date
without ever recreating it (silently, with no admin notification since
the week was never even attempted); the home calendar switched from a
static ±180-day snapshot to a dynamic FullCalendar events source
(`/api/shifts?start&end`, capped at 730 days to prevent a resource-
exhaustion request) — a schedule generated a year out is now actually
reachable; automatic daily cleanup of shift/on-call history past a
configurable retention (365 days by default, 0 disables it); a Jinja/
HTML linter (djlint) added to the test suite; a WCAG AA contrast fix
for muted text in the light theme; and a couple of AI-slop-adjacent
CSS cleanups (a decorative side-border, a dead layout-property
transition) caught by a design audit pass.

The `1.0.0-rc1` production-readiness audit is done: dependency updates,
dead-code removal, N+1/SQL query optimization, i18n completeness (French
*and* English), documentation accuracy, a full security audit plus a
live penetration test (2 real findings fixed — see
`report/SECURITY_AUDIT_v1.1.md` and `report/PENTEST_v1.md`), load
testing, and a dedicated bug hunt — landed as a series of themed,
individually reviewed pull requests.

`1.0.0-rc2` (tagged, merged to `main`) landed from real user feedback
(PR #159-166): per-day SAVEPOINT isolation so one bad day in a leave
rebalance no longer blanks the whole ±30-day window; a backtracking
on-call scheduler that maximizes filled weeks instead of a first-fit
greedy pick, plus a fixed spacing-check bug that broke on partial-window
regeneration; a merged automation dashboard with a proactive on-call gap
alert; an ANSSI-PG-078 password policy (local auth only, forced change
on first login); a fixed 405 on user/group deletion; and a full i18n
audit (10 hardcoded-string sites fixed, `fr.po` now fully populated
instead of relying on gettext's empty-string fallback). Re-validated
with a fresh full test run (1394 tests), lint/type/format checks, a
bandit + pip-audit security pass, and a load-test re-run
(`report/LOAD_TEST_v1.2.md`) — no regression found.

## 🔭 Future ideas

Larger features, not yet started, not committed to a timeline.

- **Configurable automation rules.** Rules used to generate shifts and
  on-call rotations (weekend handling, minimum staffing, rest periods)
  are currently hardcoded in Python — a config file or an admin UI
  would let each team adapt them without touching code.
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
