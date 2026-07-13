# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Leviia Schedule is a Flask web app for team shift scheduling, on-call rotations, and leave
management, with ICS calendar export. Active development, French-language docs/commit history,
not production-hardened.

## Commands

```bash
# Setup
pip install -r requirements.txt
python scripts/download_vendor_assets.py   # or: make install

# Run the app (creates SQLite db + default admin on first run)
python run.py                              # http://localhost:5000

# Tests
python -m pytest tests/ -v --tb=short              # all tests (make test)
python -m pytest tests/unit/test_models.py -v      # one file
python -m pytest tests/unit/test_models.py::TestUserModel::test_user_creation -v  # one test
python -m pytest tests/ --cov=app --cov=config --cov-report=term-missing    # coverage

# Real-browser E2E tests (optional, not in requirements.txt - skipped cleanly if absent)
pip install -r requirements-e2e.txt && playwright install chromium
python -m pytest tests/e2e/test_browser_flows.py -v --tb=short

# Lint / type-check / format
ruff check . --config=.ruff.toml
mypy app/ tests/ --ignore-missing-imports --allow-untyped-decorators
black --check . --exclude=".git|__pycache__|instance|venv"
black . --exclude=".git|__pycache__|instance|venv"   # apply formatting

# Security scans
bandit -r app/ tests/
safety scan --full-report

# All of the above
make all
```

`make help` lists everything, including database backup/restore targets (`make backup-*`) and the
bug-hunt aggregate checks (`make bug-hunt*`, wraps `scripts/bug_hunt.sh`).

Default admin created on first run: `admin@leviia.local` / `admin123` (override via
`DEFAULT_ADMIN_EMAIL` / `DEFAULT_ADMIN_PASSWORD` env vars).

## Architecture

### App factory and blueprints

`app/__init__.py` exposes `create_app(config_object)` (factory) plus a module-level `app` built
from it for backward compatibility. `run.py` is the entry point: it does first-run DB setup
(`setup_database`, `create_default_data`) then calls `app.run(...)`. Four blueprints are
registered: `auth` (login/logout/OIDC), `main` (schedule/shift/oncall/leave views — the largest
route module), `admin` (user/group/shift-type/automation management), `export` (ICS).

Login view resolution is conditional: if OIDC is enabled *and* `DISABLE_BASIC_AUTH` is set,
`login_manager.login_view` points at `auth.oidc_login` instead of `auth.login` — relevant when
touching auth flows.

### Configuration: two parallel systems

- `app/config/` (`base.py`, `development.py`, `production.py`, `testing.py`) is what the running
  app actually uses — `create_app()` defaults to `"app.config.Config"`, and tests use
  `create_app('app.config.TestingConfig')`.
- Root-level `config.py` is a separate, mostly-legacy module only exercised by
  `tests/unit/test_config.py` and `scripts/validate_config.py`. Don't confuse the two when changing
  configuration — check which one a given caller actually imports (`app.config.X` vs `config`).
- `config_oidc.py` (`OIDCConfig`) and `config_performance.py` are additional standalone config
  modules loaded directly by `app/__init__.py` and `app/auth/oidc_auth.py`.

### Models

`app/models/` is a package (`base.py` defines the shared `BaseModel` with `id`/`created_at`/
`updated_at` and CRUD helpers like `.save()`/`.update()`/`.to_dict()`; `user.py`, `shift.py`,
`oncall.py`, `leave.py`, `automation_config.py`, `notification_log.py` hold the domain models, all
subclassing `BaseModel`).

Core entities: `Group` → `User` (1:N) → `Shift` / `OnCall` / `Leave` / `NotificationLog` (each 1:N
from User), `ShiftType` → `Shift` (1:N). Composite indexes exist on `Shift(user_id, date)`,
`Shift(date, start_time)`, `OnCall(user_id, start_time, end_time)`, and
`Leave(user_id, start_date, end_date)` — preserve these if you touch query patterns.
`NotificationLog` has a unique constraint on `(user_id, notification_type, period_start)` — the
anti-duplicate guard for the weekly email reminders.

### Layered architecture: repositories/ and services/

`app/repositories/` (data access — `UserRepository`, `GroupRepository`, `ShiftRepository`,
`ShiftTypeRepository`, `OnCallRepository`, `LeaveRepository`) and `app/services/` (business logic —
`UserService`, `GroupService`, `ShiftService`, `ShiftTypeService`, `OnCallService`, `LeaveService`,
`ExportService`, `ScheduleService`, `AutomationAdminService`, `NotificationService`) are implemented
and wired up. Routes in `app/routes/` (both the `main` and `admin` blueprints, split across
multiple files — e.g. `shift_routes.py`, `admin_user_routes.py` — that all register onto the same
blueprint object defined in `main.py`/`admin.py`) parse the request, call a service, and turn the
result into a flash/redirect/JSON response; services call repositories for data access and
encapsulate validation (e.g. `can_add_shift`) and cross-cutting effects (e.g. shift rebalance after
a leave change). `app/utils/automation/` (`OnCallAutomation`, `AdvancedShiftAutomation` — the
generic `ShiftAutomation`/`BusinessRules` engine was removed as dead code, PR #105, see
`report/` for details) is a pre-existing business-logic layer used directly by services rather than
being duplicated. `NotificationService` is the one service with no route calling it — it's invoked
by the standalone cron scripts `scripts/send_shift_notifications.py`/`send_oncall_notifications.py`.

### utils/ layout

`app/utils/` is organized by concern, each a subpackage: `automation/` (shift/on-call
auto-assignment and business rules — `advanced_shift_automation.py` is the biggest piece),
`cache/`, `export/` (`ics_exporter.py`), `notifications/` (`email_sender.py` — smtplib/email
stdlib wrapper for the weekly reminder emails, no Flask-Mail dependency), `security/` (empty since
Phase 4 — `token_manager.py`/`encryption.py` removed, no real callers), `logging/` (multi-handler
setup: app/error/http/audit/sql/auth log files, optional syslog, sensitive-data filtering),
`optimizations/` (single decorator `eager_load`, actively used by admin/dashboard routes),
`helpers/` (`common_helpers.py` — actively used), plus `health.py` (k8s health endpoints) and
`prometheus_metrics.py` (gated by `PROMETHEUS_ENABLED`).

Dead code found and removed in Phase 4 (confirmed zero references anywhere before deletion):
`monitoring/`, `pagination/`, `lazy_loading.py` (785 lines, already excluded from coverage via a
stale `.coveragerc` entry pointing at pre-Phase-2 flat-file paths), `helpers/env_helpers.py`, and
`cache/cache_helpers.py`. `optimizations/__init__.py` was trimmed from 14 decorators to just
`eager_load` — the other 13 (`cached_route`, `paginated_route`, `lazy_route`, `measure_time`, etc.)
were never imported outside that file; `measure_time` even imported a module
(`app.utils.performance_monitor`) that didn't exist, confirming it had never actually run.

### Auth

`app/auth/` holds `decorators.py` (route guards), `user_manager.py`, and `oidc_auth.py`
(Authlib-based SSO for Keycloak/Okta/Auth0-style providers, gated by `OIDCConfig.ENABLED` and
`is_configured()`).

### Email notifications

Weekly reminder emails (shifts + on-call) are sent by two standalone scripts —
`scripts/send_shift_notifications.py` (Sunday, 24h before Monday's shifts) and
`scripts/send_oncall_notifications.py` (Thursday, 24h before Friday 21h on-call start) — triggered
by external cron, not by the Flask app (no APScheduler; same pattern as
`scripts/backup_database.py`/`backup_config.py`). Config lives in `scripts/notification_config.py`
(dataclass, env-var driven — `NOTIFICATIONS_ENABLED`, `SMTP_HOST`, etc., see `.env.example`); both
scripts no-op silently (exit 0) if notifications aren't enabled or SMTP config is incomplete.
`app/services/notification_service.py::NotificationService` does the actual work (date math via
`next_monday()`/`next_friday()`, always strictly future even if run on the target weekday itself;
per-recipient SMTP failures are logged and don't block the rest of the batch); it calls
`app/utils/notifications/email_sender.py::send_email()` (stdlib `smtplib`/`email`, no Flask-Mail
dependency) with Jinja2 templates rendered from `app/templates/emails/`. `NotificationLog` is the
idempotency guard — re-running a script for an already-processed period is a no-op.

## Testing conventions

`tests/conftest.py` defines the fixture chain: `test_app` builds a fresh app via
`create_app('app.config.TestingConfig')` per test function (drops/recreates all tables, disables
Talisman/OIDC/rate-limiting/cache), `client` wraps its test client, and `logged_in_client` logs in
an admin user via a real POST to `/login`. Model fixtures (`test_user`, `admin_user`, `test_shift`,
`test_leave`, `test_oncall`, `test_shift_type`, etc.) build on `test_app`/`test_group`. Reuse these
fixtures rather than constructing app instances manually in new tests.

`tests/e2e/` has two layers, deliberately kept separate (see `report/E2E Playwright - Tests
navigateur réel.md`): `test_user_flows.py` uses the Flask test client (no browser, fast, good for
permissions/redirects/data) and `test_browser_flows.py` drives real Chromium via Playwright
(`tests/e2e/conftest.py`'s `live_server_url` fixture runs the app in a thread with Talisman/CSP
*actually* active — not `TestingConfig`'s Talisman-skip). The browser layer exists specifically to
catch CSP/JS/CSS regressions the test client structurally cannot see (it never executes JS or
applies CSS) — `TestNoConsoleErrors` asserts zero browser console errors across key pages, which is
how 3 real CSP bugs were found in production before this suite existed (PR #103). Requires
`requirements-e2e.txt` + `playwright install chromium`; skips cleanly via `pytest.importorskip` if
absent, so `make test`/CI never breaks for contributors without a browser installed.

OIDC/SSO has three test layers (`tests/unit/test_oidc_config.py`, `test_oidc_auth.py`,
`test_user_manager_oidc_sync.py`; `tests/integration/test_oidc_routes.py`; `tests/e2e/test_oidc_browser_flow.py`
+ `tests/e2e/oidc_mock_provider.py`, a real minimal Flask OIDC provider run in a thread, not a
Docker container and not Python-level mocks — exercises the real discovery/token/userinfo HTTP
calls). Found and fixed a real bug: with `OIDC_DISABLE_BASIC_AUTH=true`, any OIDC failure path
redirected to `/login`, which redirected straight back to `/oidc/login`, infinite-looping — see
`app/routes/auth.py`'s `oidc_error` query param workaround.

`report/TESTING_SUMMARY.md` tracks aggregate test counts/coverage/structure — update it after any
change that shifts those numbers materially (new test file, new layer, coverage swing).
