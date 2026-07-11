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
python -m pytest tests/test_models.py -v           # one file
python -m pytest tests/test_models.py::TestUserModel::test_user_creation -v  # one test
python -m pytest tests/ --cov=app --cov=config --cov-report=term-missing    # coverage

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
  `tests/test_config.py` and `scripts/validate_config.py`. Don't confuse the two when changing
  configuration — check which one a given caller actually imports (`app.config.X` vs `config`).
- `config_oidc.py` (`OIDCConfig`) and `config_performance.py` are additional standalone config
  modules loaded directly by `app/__init__.py` and `app/auth/oidc_auth.py`.

### Models: package shadows a legacy file

`app/models/` is a package (`base.py` defines the shared `BaseModel` with `id`/`created_at`/
`updated_at` and CRUD helpers like `.save()`/`.update()`/`.to_dict()`; `user.py`, `shift.py`,
`oncall.py`, `leave.py`, `automation_config.py` hold the domain models, all subclassing
`BaseModel`). There is also a flat `app/models.py` with duplicate class definitions —
it is **shadowed** by the `app/models/` package on every `from app.models import ...` and is dead
code. Don't edit `app/models.py` expecting it to take effect; edit the file under `app/models/`.

Core entities: `Group` → `User` (1:N) → `Shift` / `OnCall` / `Leave` (each 1:N from User),
`ShiftType` → `Shift` (1:N). Composite indexes exist on `Shift(user_id, date)`,
`Shift(date, start_time)`, `OnCall(user_id, start_time, end_time)`, and
`Leave(user_id, start_date, end_date)` — preserve these if you touch query patterns.

### Scaffolded but unused: repositories/ and services/

`app/repositories/__init__.py` and `app/services/__init__.py` import from submodules
(`user_repository`, `shift_service`, etc.) that **do not exist yet** — these are placeholders for
an in-progress layered-architecture refactor (current branch: `vibe/refactor-backend-*`). Routes
currently talk to models/utils directly, not through these layers. Importing `app.repositories`
or `app.services` as-is will raise `ImportError`; either implement the missing submodules or treat
these packages as not-yet-wired-up.

### utils/ layout

`app/utils/` is organized by concern, each a subpackage: `automation/` (shift/on-call
auto-assignment and business rules — `advanced_shift_automation.py` is the biggest piece),
`cache/`, `export/` (`ics_exporter.py`), `security/` (`token_manager.py` — ICS export tokens),
`logging/` (multi-handler setup: app/error/http/audit/sql/auth log files, optional syslog,
sensitive-data filtering), plus flatter single-purpose modules (`encryption.py`,
`health.py` — k8s health endpoints, `prometheus_metrics.py`, `pagination.py`).

### Auth

`app/auth/` holds `decorators.py` (route guards), `user_manager.py`, and `oidc_auth.py`
(Authlib-based SSO for Keycloak/Okta/Auth0-style providers, gated by `OIDCConfig.ENABLED` and
`is_configured()`).

## Testing conventions

`tests/conftest.py` defines the fixture chain: `test_app` builds a fresh app via
`create_app('app.config.TestingConfig')` per test function (drops/recreates all tables, disables
Talisman/OIDC/rate-limiting/cache), `client` wraps its test client, and `logged_in_client` logs in
an admin user via a real POST to `/login`. Model fixtures (`test_user`, `admin_user`, `test_shift`,
`test_leave`, `test_oncall`, `test_shift_type`, etc.) build on `test_app`/`test_group`. Reuse these
fixtures rather than constructing app instances manually in new tests.
