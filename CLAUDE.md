# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Language

Respond to the user in French. Code, identifiers, and commit messages follow the conventions
described below (commit history is French-language; code/comments in English unless stated
otherwise).

## Project

Leviia Schedule is a Flask web app for team shift scheduling, on-call rotations, and leave
management, with ICS calendar export. Active development, French-language docs/commit history,
not production-hardened.

## Commands

```bash
# Setup
pip install -r requirements.txt
# (no more local vendor download - see Frontend section below)

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
- `config_oidc.py` (`OIDCConfig`) is an additional standalone config module loaded directly by
  `app/__init__.py` and `app/auth/oidc_auth.py`. A `config_performance.py` used to exist alongside
  it but was orphaned (loaded nowhere) and removed — don't reintroduce it under that name without
  actually wiring it into `create_app()`.

### Models

`app/models/` is a package (`base.py` defines the shared `BaseModel` with `id`/`created_at`/
`updated_at` and CRUD helpers like `.save()`/`.update()`/`.to_dict()`; `user.py`, `shift.py`,
`oncall.py`, `leave.py`, `automation_config.py`, `notification_log.py`, `swap_request.py` hold the
domain models, all subclassing `BaseModel`).

Core entities: `Group` → `User` (1:N) → `Shift` / `OnCall` / `Leave` / `NotificationLog` (each 1:N
from User), `ShiftType` → `Shift` (1:N). Composite indexes exist on `Shift(user_id, date)`,
`Shift(date, start_time)`, `OnCall(user_id, start_time, end_time)`, and
`Leave(user_id, start_date, end_date)` — preserve these if you touch query patterns.
`NotificationLog` has a unique constraint on `(user_id, notification_type, period_start)` — the
anti-duplicate guard for the weekly email reminders. `SwapRequest` has 3 FKs to `User`
(requester/target_user/reviewer) + 2 to `Shift` (shift/target_shift) — the first model in this repo
with more than one FK to the same table. It deliberately has **no** `db.relationship()` declarations:
SQLAlchemy 2.0's own stubs type a bare `relationship()` call as `RelationshipProperty[Any]` on both
declaration and instance access without the (unconfigured, see `mypy.ini`/Makefile) SQLAlchemy mypy
plugin, so `requester`/`target_user`/`reviewer`/`shift`/`target_shift` are plain `@property` lookups
via `db.session.get(...)` instead — same pattern as `User.next_shift`/`User.current_oncall`
(`app/models/user.py`). Consequence: `SwapRequestRepository` cannot `joinedload()` these (one extra
query per access) — acceptable at this app's scale.

### Layered architecture: repositories/ and services/

`app/repositories/` (data access — `UserRepository`, `GroupRepository`, `ShiftRepository`,
`ShiftTypeRepository`, `OnCallRepository`, `LeaveRepository`, `SwapRequestRepository`) and
`app/services/` (business logic — `UserService`, `GroupService`, `ShiftService`, `ShiftTypeService`,
`OnCallService`, `LeaveService`, `SwapService`, `ExportService`, `ScheduleService`,
`AutomationAdminService`, `NotificationService`, `BackupService`) are implemented and wired up.
Routes in `app/routes/` (both the `main` and `admin` blueprints, split across multiple files — e.g.
`shift_routes.py`, `admin_user_routes.py` — that all register onto the same blueprint object defined
in `main.py`/`admin.py`) parse the request, call a service, and turn the result into a
flash/redirect/JSON response; services call repositories for data access and encapsulate validation
(e.g. `can_add_shift`) and cross-cutting effects (e.g. shift rebalance after a leave change).
`app/utils/automation/` (`OnCallAutomation`, `AdvancedShiftAutomation` — a previous generic
`ShiftAutomation`/`BusinessRules` engine was removed as dead code after confirming zero real
callers; see `report/` for the investigation) is a pre-existing business-logic layer used directly
by services rather than being duplicated. `NotificationService` is the one service with no route calling it — it's invoked
by the standalone cron scripts `scripts/send_shift_notifications.py`/`send_oncall_notifications.py`.
`BackupService` (`app/services/backup_service.py`) is the exception in the other direction — it's
`app/` code that imports from `scripts/` (`scripts/backup_config.py`/`backup_database.py`), safe
because that dependency only ever goes one way (`scripts/` never imports `app/`, see "Database
backups" below).

### utils/ layout

The absolute ICS subscription links shown on `/profile/ics-token` and the shift/oncall/leave
export buttons (`_ics_export_buttons.html`) prefer `app.config["PUBLIC_BASE_URL"]` (optional env
var, injected as `public_base_url` by `inject_public_base_url` in `app/__init__.py`) over
`request.host_url` — needed behind reverse-proxy topologies where `ProxyFix`'s trusted
`X-Forwarded-Host` isn't set correctly, which would otherwise leak the backend's internal
IP/hostname into links users paste into calendar apps.

`app/utils/` is organized by concern, each a subpackage: `automation/` (shift/on-call
auto-assignment and business rules — `advanced_shift_automation.py` is the biggest piece),
`cache/`, `export/` (`ics_exporter.py`), `notifications/` (`email_sender.py` — smtplib/email
stdlib wrapper for the weekly reminder emails, no Flask-Mail dependency), `security/` (empty —
`token_manager.py`/`encryption.py` were removed after confirming zero real callers), `logging/` (multi-handler
setup: app/error/http/audit/sql/auth log files, optional syslog, sensitive-data filtering),
`optimizations/` (single decorator `eager_load`, actively used by admin/dashboard routes),
`helpers/` (`common_helpers.py` — actively used), plus `health.py` (k8s health endpoints) and
`prometheus_metrics.py` (gated by `PROMETHEUS_ENABLED`).

Dead code found and removed (confirmed zero references anywhere before deletion):
`monitoring/`, `pagination/`, `lazy_loading.py` (785 lines, already excluded from coverage via a
stale `.coveragerc` entry pointing at paths from an earlier flat-file layout the models package
replaced), `helpers/env_helpers.py`, and `cache/cache_helpers.py`. `optimizations/__init__.py` was trimmed from 14 decorators to just
`eager_load` — the other 13 (`cached_route`, `paginated_route`, `lazy_route`, `measure_time`, etc.)
were never imported outside that file; `measure_time` even imported a module
(`app.utils.performance_monitor`) that didn't exist, confirming it had never actually run.

### Auth

`app/auth/` holds `decorators.py` (route guards), `user_manager.py`, and `oidc_auth.py`
(Authlib-based SSO for Keycloak/Okta/Auth0-style providers, gated by `OIDCConfig.ENABLED` and
`is_configured()`).

### Shift swaps

Users request to give up one of their shifts to another user (`app/routes/swap_routes.py`:
`/swaps`, `/swaps/add`, `/swaps/<id>/cancel`), optionally in exchange for one of the target's shifts
(reciprocal swap) — leave `target_shift_id` unset for a one-way give-away. An admin must approve
before anything changes (`app/routes/admin_swap_routes.py`: `/admin/swaps`,
`/admin/swaps/<id>/approve`, `/admin/swaps/<id>/reject`, `/admin/swaps/<id>/revert`) — this is the
**only** approval workflow in the app; `Leave` (congés) has none by design (see "Models" above) and
stays that way, don't add one there by analogy. `SwapService` (`app/services/swap_service.py`)
re-validates the same business rules at both request time and approval time (`_validation_error`:
shift still owned by requester, target not on leave / doesn't already have another shift that day,
no duplicate pending request per shift) since state can drift between the two — approval doesn't
blindly trust the original request. `approve_swap` reassigns `Shift.user_id` directly (swap, not
delete+recreate) then commits; reject/cancel only touch `SwapRequest.status`, shifts stay untouched.
`/admin/swaps` lists both pending and already-approved requests — an admin can `revert_swap` an
approved exchange after the fact, which reassigns `Shift.user_id` back to the original owners and
sets status to `REVERTED` (distinct from `CANCELLED`, which is only for the requester backing out
*before* approval). `revert_swap` deliberately skips `_validation_error` (the swap back to the prior
owners was valid by definition) but does check each shift is still owned by whoever the approval put
it with — if either shift was reassigned again since (another swap, manual edit), it refuses rather
than silently overwriting an unrelated change. `/api/swaps/target-shifts` is a small JSON endpoint
backing `app/static/js/swaps/swap-form.js`, which populates the optional "shift requested back"
dropdown once a target user is chosen on `add_swap.html`. `SwapService.purge_resolved_for_user`/
`purge_all_resolved` hard-delete non-`PENDING` requests (`/swaps/purge` for a user's own history —
matched as requester *or* target, so a purge can remove a row the other party can still see, since
it's one shared historical record, not a per-user view; `/admin/swaps/purge` for everyone's) — no
age threshold, "old" here means "no longer actionable", not time-based.

### In-app notifications

`AppNotification` (`app/models/app_notification.py`) is the bell-icon notification shown in the
sidebar (unread count badge via `inject_unread_notifications_count` context processor in
`app/__init__.py`) — **not** the same thing as `NotificationLog`
(`app/models/notification_log.py`), which is purely an idempotency guard for the weekly *email*
reminders and is never rendered anywhere; don't confuse the two when searching for "notification" in
this codebase. `AppNotificationService` (`app/services/app_notification_service.py`) is created
synchronously by other services on domain events, not by a cron script — currently the only caller is
`SwapService`: a new request notifies every admin (`UserRepository.list_admins()`) with a link to
`/admin/swaps`; an approve/reject/revert decision notifies the requester (and also the target user
for approve/revert, since those two actually change their shifts — reject changes nothing, so only
the requester is told). Routes live in `app/routes/notification_routes.py` (`/notifications`,
`/notifications/<id>/read`, `/notifications/read-all`), all on `main_bp`. If you add a notification
trigger to another service, follow the same pattern: call `AppNotificationService` after the
triggering action's own `db.session.commit()`, not before — a notification that fires ahead of a
failed/rolled-back action would be wrong.

### Frontend

Tailwind CSS 4 + daisyUI 5, both loaded via `cdnjs.cloudflare.com` — no build step: Tailwind runs
as `tailwindcss-browser` (the official JIT-in-browser compiler), scanning class names at runtime
instead of being precompiled. There is no `package.json`/npm anywhere in this project; keep it that
way — the CDN-JIT approach was chosen specifically to avoid introducing a Node toolchain. Bulma
(the previous CSS framework) was fully removed; no vendor directory, no `download_vendor_assets.py`
— Font Awesome
(7.2.0, SVG+JS mode, see below) and daisyUI/Tailwind are 100% CDN. `app/static/css/variables.css`
bridges daisyUI's own `--color-*` custom properties to app-level names (`--app-color-primary`,
`--bg-primary`, etc.) consumed by the handful of remaining custom CSS files
(`pages/dashboard.css`, `pages/rotation-order.css`, `vendor/fullcalendar-overrides.css`,
`themes/dark.css`) — don't reintroduce a `--bulma-*`-style remap; daisyUI already handles
light/dark itself via `[data-theme]`, `themes/dark.css` only needs to cover things daisyUI can't
know about (FullCalendar's own DOM) plus a couple of framework-agnostic accessibility rules
(focus-visible, reduced-motion).

**Palette: Dracula (dark theme) / Alucard (light theme)** — `app/static/css/theme-colors.css`
overrides every daisyUI semantic `--color-*` (not just `--color-primary`) per `[data-theme="dark"|"light"]`,
sourced 1:1 from the official spec at draculatheme.com/spec (no invented or computed hues; the three
background levels `--color-base-100/200/300` come straight from the spec's Background/Current Line
(opaque)/Selection colors). This is still the only way to theme daisyUI under `tailwindcss-browser` —
in a real-browser check it raised "does not support plugins or config files" for both `@plugin
"daisyui/theme"` and `@theme`, so a full custom daisyUI theme via daisyUI's own theming system is
not possible here; CSS-variable overrides on `[data-theme=...]` remain the only route. Same file also
sets shape/depth tokens (`--radius-box`, `--radius-field`, `--radius-selector`, `--depth`, `--noise`) —
a computed-style diff in a real browser confirmed the cdnjs-pulled daisyUI build honors
`--depth`/`--noise`, so they were kept rather than assumed unsupported and dropped.

Font Awesome is loaded in **SVG+JS mode** (`js/all.min.js`, not the CSS+webfont mode) —
deliberately: cdnjs's `.woff2` files for 7.2.0 are each truncated by exactly one byte (confirmed
against the previously-vendored copies), which Chromium's font sanitizer rejects outright
("OTS parsing error"), leaving every icon invisible. SVG+JS sidesteps the corrupt fonts by
rendering icons as inline `<svg>` at runtime — but it also means any JS that touches an icon's
DOM node must not assume it stays an `<i>` (Font Awesome replaces it with `<svg>` after load,
preserving the original classes). The theme toggle button no longer swaps `fa-moon`/`fa-sun`
classes directly (that pattern is gone) — it's a daisyUI `swap swap-rotate` component now, and
`theme-manager.js` just toggles the `swap-active` class on the button itself; daisyUI's own CSS
handles which icon shows, so the FA SVG-replacement quirk no longer needs to be worked around here
specifically (it still applies to any *other* code touching icon DOM nodes — don't assume `<i>`).

Mobile navigation is a real daisyUI `drawer` (checkbox-driven, `#mobile-drawer`) — `navbar-menu.js`
only syncs the checkbox's checked state with the burger `<button>` (kept as a real button, not a
`<label for>`, so `aria-expanded`/`aria-controls` stay correct) and closes on Escape; the daisyUI
overlay's own `<label for="mobile-drawer">` handles click-outside-to-close natively, no JS needed
for that part. The shift-creation modal (built dynamically in `fullcalendar-config.js`, not a
template) is a native `<dialog>` + `showModal()`/`close()` — focus trap and Escape-to-close are
handled by the browser, not hand-rolled; listen on the dialog's `cancel` event (not `close`) if you
need to distinguish "user dismissed it" from a programmatic `.close()` after a successful save,
since `close` fires for both. User-supplied strings (names, emails, labels) interpolated into that
modal's generated HTML go through an `escapeHtml()` helper first — the innerHTML-template-literal
pattern doesn't escape by default.

FullCalendar stayed on **6.1.21** (not upgraded to 7.0.0 as originally planned) — loaded from
`cdn.jsdelivr.net`, the one deliberate exception to "everything via cdnjs" (cdnjs doesn't host
this package's locale files for any version tested). 7.0.0 was attempted three ways (cdnjs, plain
jsDelivr ESM imports, esm.sh's auto-bundled imports) and hit a real runtime bug in FullCalendar's
own compiled Preact rendering code every time ("Class constructor ... cannot be invoked without
'new'") — not a hosting or import-resolution issue, so not something fixable from this side.
Revisit if a later 7.x patch lands.

CSP (`app/__init__.py`'s `CSP_POLICY`) allows `cdnjs.cloudflare.com` (script/style/font) and
`cdn.jsdelivr.net` (script, FullCalendar only) plus `data:` for `img-src` (daisyUI's noise-texture
SVG background on some components).

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

### Database backups

`scripts/backup_database.py` (local + S3/S3-compatible, compression, integrity verification,
retention/cleanup) is deliberately independent of `app/` — no import of anything under `app.*`,
verified by a regression test that greps the file's source — so it keeps working even if the Flask
app can't boot (the disaster-recovery scenario it exists for). Config lives in
`scripts/backup_config.py::BackupConfig` (same dataclass-from-env pattern as
`notification_config.py`), gated by `BACKUP_ENABLED` (opt-in, `false` by default). Success/failure
alerts (`send_backup_notification()`) reuse the notifications SMTP config
(`scripts/notification_config.py`) via a small self-contained SMTP call rather than importing
`app.utils.notifications.email_sender` — the same isolation constraint applies in reverse (`app/`
doesn't import from `scripts/`, except `BackupService`, see above) — so also gated by
`NOTIFICATIONS_ENABLED`. `app/services/backup_service.py::BackupService` wraps the script's pure
functions (`create_backup`, `list_backups`, `cleanup_local_backups`/`cleanup_s3_backups`) for
`app/routes/admin_backup_routes.py` (`/admin/backups`) — local file downloads are path-traversal
guarded (prefix + resolved-path containment check); S3 downloads go through a server-side temp file
(`send_file` + `call_on_close` cleanup), not a presigned URL. `BackupService.create_now()` re-checks
`BACKUP_ENABLED` itself (the script's own `main()` guard doesn't cover this path) so manual creation
from the admin UI honors the same switch as the cron job; listing/downloading existing backups stays
available regardless. Docker: `docker/entrypoint.sh` starts `crond` if `NOTIFICATIONS_ENABLED` and/or
`BACKUP_ENABLED` is true (one shared crond, `docker/crontabs/appuser` always has both scripts'
entries — each script no-ops internally if its own flag is off).

Schema migrations are handled by Alembic (`migrations/`, via Flask-Migrate). `run.py::setup_database()`
calls `flask_migrate.upgrade()` unconditionally on every start (both the plain `python run.py` path
and `docker/entrypoint.sh` → `docker/init_database.py`, which now delegates to `setup_database()`
instead of calling `db.create_all()` directly) — safe to run every time: on a fully up-to-date
database it's a no-op. On a database predating Alembic's adoption (tables already created by the old
`db.create_all()`-only path, no `alembic_version` table yet), `setup_database()` first runs
`db.create_all()` once more to backfill anything still missing (idempotent), then stamps the
baseline revision (`run.py::BASELINE_REVISION`, matching `migrations/versions/da2c4dfc1024_*.py`)
so `upgrade()` only applies what comes after it — no manual `alembic stamp`/`upgrade` step required
on deploy, on a fresh install or an existing one. `check_database_integrity()` in `run.py` remains a
separate, simpler table-existence check (used by tests), no longer part of the startup path.
`TestingConfig` bypasses migrations entirely — `tests/conftest.py`'s `test_app` fixture calls
`db.drop_all()`/`db.create_all()` directly for speed, since tests don't need to exercise the upgrade
path itself.

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
applies CSS) — `TestNoConsoleErrors` asserts zero browser console errors across key pages; this
suite is how 3 real CSP bugs (resources silently blocked by the policy, invisible to the test
client) were caught before shipping. Requires
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
