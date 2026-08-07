# Security audit v1.0

> Conducted as part of the v1.0 stabilization effort (see the plan across 6
> themed PRs). Scope: HTTP/session configuration, authentication, secrets
> management, SQL injection, static analysis (Bandit), dependency scanning
> (Safety), CI/CD. Does not replace a pentest or a third-party audit — this
> is a code + configuration review, with direct verification (actually
> running the scanners, not just reading the code).

## Summary

No critical or high vulnerability found in the application code (`app/`).
Two real weaknesses fixed during this audit (see "Fixes applied"). The rest
of this document is mostly a **confirmation** of protections already in
place (CSRF, CSP, password hashing, etc.), backed by evidence rather than
assumption.

## Fixes applied during this audit

### 1. Bandit B105/B107/B104 — false positives not annotated on the Bandit side

`ruff` (rule `S105`/`S107`, flake8-bandit) and `bandit` detect similar
patterns but use **different** suppression mechanisms (`# noqa: S105` for
ruff, `# nosec BXXX` for bandit) — an existing `# noqa: S105` does not
suppress the equivalent bandit warning. Three false positives already
reviewed on the ruff side had therefore never been explicitly marked as
accepted on the bandit side:

- `app/services/settings_service.py:38` — `ICS_TOKEN_EXPIRY_DAYS_KEY`, a
  `Setting` key name, not a secret (B105).
- `app/services/user_service.py:50,71` — `password: str = ""` parameter
  (empty default value, not a hard-coded password) on
  `UserService.create()`/`update()` (B107 x2).

Added explicit `# nosec BXXX` with a justification comment. `bandit -r
app/`: **0 findings** after the fix (3 before).

### 2. Bandit B104 — 0.0.0.0 bind

`app/config/base.py:HOST` — binds on all interfaces, flagged by Bandit as
a potential risk. **Documented false positive**: the app always runs in a
container or behind a reverse proxy in production —
`127.0.0.1` would silently break any exposure. Annotated `# nosec
B104` with justification (network exposure controlled by the deployment,
not by the app).

### 3. Bandit B324 — MD5 in `scripts/find_duplicates.py`

Non-cryptographic usage (code-similarity fingerprint, not a security
need). Fixed with `usedforsecurity=False` (the fix suggested by Bandit
itself) rather than an unnecessary algorithm change.

### 4. Real bug found while digging into B104: `PROMETHEUS_ENABLED` never wired up

Not strictly a security vulnerability, but documented here since it was
found during this pass and fixed in the same PR: `app/__init__.py` checks
`app.config.get("PROMETHEUS_ENABLED", False)`, but this key was **never
read from the environment** in `app/config/base.py::Config` — the
`/metrics` feature was therefore structurally unreachable in a real
deployment, regardless of the env var set, masked by a test that forced
`app.config["PROMETHEUS_ENABLED"] = True` directly instead of going
through the real `create_app()` path. See `report/BUG_HUNT_v1.0.md`
for the full detail and the fix (wiring added + removal of the
duplicated and buggy `/health`/`/ready` routes in that same module,
already correctly served by `app/utils/health.py`).

## What was checked and confirmed sound

### CSRF

`Flask-WTF CSRFProtect` active across the whole application
(`app/__init__.py`). The only exemption: the `app/api/resources/*`
blueprints (public API `/api/v1/*`), exempted via `csrf.exempt(blp)` —
justified: this API never accepts cookie-based authentication (bearer
token only, `ServiceAccount`), so the risk CSRF protects against
(cross-site request with a valid session cookie) doesn't apply here.

### HTTP security headers (Talisman + CSP)

`Flask-Talisman` active everywhere except in `TESTING`.
`TALISMAN_FORCE_HTTPS`/`TALISMAN_STRICT_TRANSPORT_SECURITY`
configurable via env, enabled by default. CSP (`CSP_POLICY`,
`app/__init__.py`): `default-src 'self'`, `object-src 'none'`, no
`'unsafe-inline'` on `script-src` (only on `script-src-attr`, for the
`onclick=""` attributes in developer-written static HTML — never user
data — and on `style-src`, for a single dynamic dashboard bar-width
style). External whitelisted domains (`cdnjs.cloudflare.com`,
`cdn.jsdelivr.net`) documented and justified one by one in the code (CDN
for Tailwind/daisyUI/Font Awesome/FullCalendar — the app has no JS/CSS
build pipeline, see CLAUDE.md "Frontend").

### Session cookies

`SESSION_COOKIE_HTTPONLY=True` by default, `SESSION_COOKIE_SAMESITE=Lax`,
`SESSION_PROTECTION="strong"` (Flask-Login re-invalidates the session if
the IP/user-agent changes). `SESSION_COOKIE_SECURE` is `False` by default
in `Config` (needed for a first local run without TLS) but
`True` by default in `docker/.env.example`
(`TALISMAN_FORCE_HTTPS`/deployment behind a TLS proxy) — consistent with
the documented architecture.

### `ProxyFix`

`ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)` — trusts exactly
**one** proxy hop. Correct for the documented topology (a single reverse
proxy in front of the app); a longer proxy chain without adjusting these
values would let a client spoof its IP in audit logs, but that is not the
documented deployment topology.

### Passwords

`werkzeug.security.generate_password_hash()` (scrypt by default).
`User.password_hash` is `String(255)` (widened this session, see
CLAUDE.md — real bug found and fixed while building
MySQL support: the default 128-character length silently truncated a
~162-character scrypt hash under SQLite, and rejected it outright
under MySQL/PostgreSQL).

### API tokens (`ServiceAccount`)

`token_hash` in SHA-256 (no slow hash like PBKDF2/bcrypt) —
deliberate and documented: the token has 256 bits of entropy
(`secrets.token_urlsafe(32)`), unlike a low-entropy human password, so a
slow hash would only add latency with no real security benefit. The full
token is **never persisted** (shown only once, at creation/regeneration —
same UX as a GitHub PAT).

### SQL injection

No raw SQL query built by string concatenation found in
`app/`. The only two `.execute()` calls with textual SQL use
`sqlalchemy.text()` correctly (`app/utils/health.py`) — the only
counter-example (`app/utils/prometheus_metrics.py`, raw string without
`text()`) was unreachable dead code, removed (see "Real bug
found" above) rather than merely fixed, since it already duplicated an
existing, correct route.

### Default secrets

`SECRET_KEY`/`SECURITY_PASSWORD_SALT`: if not set via env,
randomly generated via `secrets.token_urlsafe()` at startup — no
hard-coded static value that would end up in a public repo. Side effect
documented elsewhere (not a security bug): without an explicitly fixed
`SECRET_KEY`, every restart invalidates active sessions —
which is why `docker/.env.example`/`.env.example` explicitly document
generating and fixing a real value.

### Apprise webhooks

`NotificationTarget.apprise_url` treated as a secret: never in
`AuditService` `details`, never in the list view (`/admin/notification-targets`,
only pre-filled in the edit form), never interpolated into
a log message (see CLAUDE.md "External notifications (Apprise)" for
the detail — including the documented limitation of the log
sensitive-data filter on this specific point, mitigated by discipline at
the call sites rather than by a regex that cannot cover every Apprise
URL shape).

### Path traversal (backups)

`BackupService` (local backup download): prefix guard
+ containment check on the resolved path before any file access
(`app/services/backup_service.py`, see CLAUDE.md "Database
backups").

### Audit trail

`AuditService.log()` captures actor/IP/action/resource for the
sensitive domains (`auth.*`, `user.*`, `setting.*`, etc.) — DB
+ file write, fails silently and gets logged (never blocking for the
business action it records), with a dedicated regression test
(`test_failure_writing_entry_does_not_raise`).

## Bandit — final status

```
bandit -r app/     -> 0 finding (3 before the fix)
bandit -r scripts/ -> 0 blocking finding (remaining Low findings: B101
                       assert in a script, B110 try/except/pass already
                       deliberate in find_duplicates.py - script
                       hygiene, not an attack surface)
```

## Safety (dependency scan) — not run in CI, gap documented

`safety check` (the old command, used until now by
`.gitlab-ci/.gitlab-ci.yml`) has been **unsupported since May 2024** — CI
was calling it with syntax already invalid for the installed version
(`safety==3.8.1`). Its replacement, `safety scan`, requires either
`safety auth login` (interactive) or a `SAFETY_API_KEY` key — confirmed
by direct testing: without a key, `safety scan` hangs indefinitely
waiting for a login prompt, which **would block the entire CI pipeline**
indefinitely instead of failing cleanly. CI (see
"CI/CD" below) now only runs `safety scan` if
`SAFETY_API_KEY` is configured (CI/CD > Variables), and explicitly skips
it otherwise (a clear message, not a `|| true` silently masking the
absence of a scan).

**Recommended action, not done here** (requires a
platform.safetycli.com account, a decision outside code scope): configure
`SAFETY_API_KEY` to actually enable dependency scanning in CI.

## CI/CD — blocking jobs

`.gitlab-ci/.gitlab-ci.yml`: `run_linting` and `run_security` were
both non-blocking (`|| true` on every command), so a
lint/type-check/format/security regression never failed the pipeline.
Fixed: `run_linting` (ruff/mypy/black) is now strictly aligned with
`make lint`/`make format-check` (the exact same commands) and blocking;
`run_security` (`bandit`) is blocking, `safety`
remains conditional for the reasons above.

**Important point not resolved by this PR**: this repository is hosted on
GitHub (`FoxOps/kairos`), but `.gitlab-ci/.gitlab-ci.yml` is a
**GitLab CI** configuration — there is **no GitHub
Actions workflow at all** (`.github/workflows/` does not exist). Making
this file blocking improves its intrinsic quality but, as it stands, has
**no real effect on this repo's GitHub pull requests**
since no CI actually runs against them (confirmed: `gh pr checks` reports
no checks at all on this series' PRs). Decision for the team to make:
either this file serves an existing GitLab mirroring setup outside what
this Git repo alone can confirm, or a real, equivalent GitHub Actions
workflow needs to be added for a quality gate to actually apply to this
repo's PRs.

## Verdict

No critical/high application vulnerability found. The structural
protections (CSRF, CSP, password hashing, API tokens,
session protection, audit trail) are in place and consistent with their
documentation. The two real gaps identified are operational, not
application-level: (1) the dependency scan (Safety) is not active for
lack of an API key — a team decision, not a code fix — and (2) no
CI actually runs against this GitHub repo. Neither one
indicates a flaw in the application code itself.
