# Roadmap

**Current version: 1.1.0** — feature-complete, tested (1390+
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
- Configurable automation rules, admin-editable at
  `/admin/automation/rules`: weekend definition, on-call spacing/week
  anchor, shift slots (which `ShiftType` covers on-call/rotation/
  default), minimum/maximum staffing per shift type, mandatory slots
  (unfilled raises an elevated alert, never a hard block), minimum
  rest after an on-call, and shift/on-call overlap blocking. Each
  rule's default matches the previously hardcoded behavior exactly.
  Org-wide for now — see "Future ideas" for per-group rules

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

**1.1.0** — next development cycle, just started, nothing landed yet.

## 🔭 Future ideas

Larger features, not yet started, not committed to a timeline.

- **Per-group calendar display.** The configurable automation rules
  engine (see "Done") supports per-`Group` overrides end to end —
  both the eligible-user pool *and* rule values (weekend/slots/
  spacing/anchor/mandatory/staffing/rest/overlap) resolve per Group,
  editable on `/admin/automation/rules` via its group selector — and
  `shift_scheduling_mode`/`oncall_scheduling_mode` (each independently
  shared/per_group) are wired all the way into generation:
  `AutomationAdminService.generate_full()` runs one independent pass
  per eligible `Group` when a mode is `per_group`. What's still
  missing is the calendar itself: no per-group color/legend/filter, so
  a `per_group` deployment can't visually distinguish which rotation
  an event belongs to. `fill_oncall_gaps()`/`rebalance_after_leave()`/
  `refresh_shifts()` (narrower advanced workflows) also still pool
  regardless of the setting. Deliberately left for a dedicated
  follow-up rather than bundled into the rules-engine work.
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
