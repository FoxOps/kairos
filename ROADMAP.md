# Roadmap

**Current version: 1.0.0-rc1** — feature-complete, tested (1300+
automated tests), and used for real team scheduling. Two operational
items are still open before a production rollout should rely on them
blindly — see "Known limitations" below.

## What Kairos does today

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

**Operations**
- Multi-language (French/English) and multi-timezone, per user or
  organization-wide
- An audit trail of who changed what, browsable by admins
- Database backups (local or S3-compatible), schedulable via cron or
  triggered from the admin UI
- Prometheus metrics and Kubernetes health/readiness endpoints
- Docker image and Kubernetes manifests provided for deployment

## Known limitations

- **CI doesn't run on GitHub.** The GitLab CI config in this repo
  (`.gitlab-ci/.gitlab-ci.yml`) doesn't execute against this
  GitHub-hosted repository — there is no equivalent GitHub Actions
  workflow yet.
- **The Safety dependency scanner is inactive by default** — it
  requires a `SAFETY_API_KEY` that isn't configured out of the box.
- **ICS token expiry isn't enforced.** `ICS_TOKEN_EXPIRY_DAYS` exists
  as a setting but nothing currently checks or expires a token based
  on it — a token remains valid indefinitely once issued.
- **A pre-existing timezone edge case** in `OnCall.is_active()`
  compares a stored UTC timestamp against local server time, which can
  be off by the server's UTC offset. Known, not yet fixed.

## Contributing

Kairos was built almost entirely with AI coding tools by someone
without a professional development background — see the README for
the full story. Code review, bug reports, and contributions from
experienced developers are genuinely welcome. If you want to help,
start with an [Issue](https://github.com/FoxOps/kairos/issues) or a
[Discussion](https://github.com/FoxOps/kairos/discussions).
