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
- A third layer sits on top of both: `Setting` (`app/models/setting.py`, generic key/value store,
  same EAV shape as `AutomationConfig`) + `app/services/settings_service.py::SettingsService`
  (typed getters/setters) for settings an admin can change at runtime from `/admin/settings`
  without redeploying — `default_timezone`, `default_language`, `public_base_url`,
  `items_per_page`/`max_per_page`, `notifications_enabled`,
  `backup_retention_days`/`backup_max_backups`, `ics_token_expiry_days` (currently unenforced, see
  "Multi-timezone support" below). Rule: a `Setting` row, if present, always wins; if absent, the
  getter falls back **live** to the matching `app.config`/env value (never a one-time seed written
  to the DB) — so an env-var-only deployment behaves identically to before this feature existed,
  until an admin actually saves a value through the new page. Don't remove the underlying env vars
  from `app/config/base.py` thinking they're superseded — they remain the permanent fallback
  layer. **`default_language` is the one exception**: there is no env var counterpart (a brand new
  concept, never configurable before the i18n feature) — its fallback
  (`SettingsService.FALLBACK_DEFAULT_LANGUAGE`) is a hardcoded `"fr"` constant, not an env read.
  See "Multi-language support" below.

### Models

`app/models/` is a package (`base.py` defines the shared `BaseModel` with `id`/`created_at`/
`updated_at` and CRUD helpers like `.save()`/`.update()`/`.to_dict()`; `user.py`, `shift.py`,
`oncall.py`, `leave.py`, `automation_config.py`, `notification_log.py`, `swap_request.py`,
`setting.py` hold the domain models, all subclassing `BaseModel`). `User.timezone` (nullable
String) is the user's personal display timezone preference — `None` means "use the org's
`default_timezone` Setting", resolved at read time via `User.effective_timezone()`, not baked
into the column (see "Multi-timezone support" below). `User.language` (nullable `String(5)`)
is the same pattern for the UI/email language — `None` means "use the org's `default_language`
Setting", resolved via `User.effective_language()` (see "Multi-language support" below).
`User.shift_notifications_enabled`/
`oncall_notifications_enabled` (both `Boolean`, default `True`) are a per-user opt-out for the
two weekly reminder emails, editable at `/profile/settings` — see "Email notifications" below for
how they interact with the org-wide `notifications_enabled` `Setting`.

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
`export/` (`ics_exporter.py` — uses stdlib `zoneinfo`, not `pytz` (removed from dependencies);
`generate_ics_standard()`/`export_to_ics()` take a `tz_name` parameter, always the org's
`default_timezone`, see "Multi-timezone support" below), `notifications/` (`email_sender.py` — smtplib/email
stdlib wrapper for the weekly reminder emails, no Flask-Mail dependency), `security/` (empty —
`token_manager.py`/`encryption.py` were removed after confirming zero real callers), `logging/` (multi-handler
setup: `app.log`/`error.log`/`debug.log`/`http_errors.log`/`audit.log` — no `sql.log`/`auth.log`/syslog
support despite an earlier version of this doc claiming otherwise; every handler is a
`RotatingFileHandler` (`LOG_MAX_BYTES`/`LOG_BACKUP_COUNT` env vars, defaults 10 MiB / 5 backups) —
see "Audit trail" below for `audit.log`'s actual writer, sensitive-data filtering),
`optimizations/` (single decorator `eager_load`, actively used by admin/dashboard routes),
`helpers/` (`common_helpers.py` — actively used; `timezone_helpers.py` — `to_viewer_timezone()`/
`to_org_timezone()`, the FullCalendar JSON API conversion, see "Multi-timezone support" below),
plus `health.py` (k8s health endpoints) and `prometheus_metrics.py` (gated by
`PROMETHEUS_ENABLED`).

Dead code found and removed (confirmed zero references anywhere before deletion):
`monitoring/`, `pagination/`, `lazy_loading.py` (785 lines, already excluded from coverage via a
stale `.coveragerc` entry pointing at paths from an earlier flat-file layout the models package
replaced), `helpers/env_helpers.py`, and `cache/` in full (`cache_helpers.py` first, then the rest
of the subpackage — `cache_manager.py`'s `init_cache()` was called at startup but nothing ever read
from the cache it built: `get_cache()`/`cache_key()`/the `cached_route` decorator were themselves
already-confirmed-dead removals from an earlier pass, leaving `init_cache()` with no real caller
either. Caching is handled externally now (reverse proxy / dedicated cache), not by the app).
`optimizations/__init__.py` was trimmed from 14 decorators to just
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

### Audit trail

`AuditLog` (`app/models/audit_log.py`) is the append-only "who did what, when, to which resource"
record consulted at `/admin/audit-log` — **not** the same thing as `NotificationLog` (email
send-dedup only) or `AppNotification` (in-app bell icon, swap-only scope, see above); don't confuse
any of these three when searching for "audit"/"notification" in this codebase. Before this feature,
`app/utils/logging/logger.py::log_audit_action()` already existed but was never called by any route
or service (confirmed by grep — only the test suite invoked it), so `logs/audit.log` carried no real
data; this feature is what actually wires it up, in addition to (not instead of) the new DB table —
an explicit dual-write decision (DB for the filterable admin UI, file as a defense-in-depth copy that
survives even if the DB is unavailable).

`AuditLog.actor_id` is a nullable FK to `User` (same `@property`-over-`db.relationship()` pattern as
`SwapRequest`, for the same SQLAlchemy 2.0 stub-typing reason — see "Models" above); `action` is a
namespaced `"<domain>.<verb>"` string, e.g. `shift.create`, `swap.approve`, `auth.login_failure`.
Domains in use: `user`, `group`, `shift` (plus `shift.bulk_delete` for the multi-row delete routes),
`oncall` (same shape as `shift`), `leave` (no `bulk_delete` — none exists in `LeaveService`),
`shift_type`, `swap` (`request`/`cancel`/`approve`/`reject`/`revert`/`purge`, mirroring every
cross-cutting effect already documented under "Shift swaps" above), `setting` (one action,
`setting.update`, for every `SettingsService` setter — `resource_type="Setting"`, `details` is a
plain `"key=value"` string since `Setting` rows have no admin-facing PK), and `auth`/`profile`
(`auth.register`, `auth.login_success`, `auth.login_failure`, `auth.logout`,
`profile.password_change`). Deliberately out of scope: no field-by-field before/after diff, just
who/what/when/which-resource plus a short human-readable `details` summary — a future enhancement,
not this one.

`AuditService.log()` (`app/services/audit_service.py`) is the single write path — resolves `actor`
from `current_user` when not passed explicitly (same `has_request_context()`-guarded pattern as
`app.get_locale()`), captures `flask.request.remote_addr`, writes the `AuditLog` row (own
`db.session.commit()`), then calls `log_audit_action()` for the file copy — wrapped in a bare
`try/except` that logs and swallows any failure, since a bug in the audit trail must never break the
business action it's recording (`tests/unit/test_audit_service.py::test_failure_writing_entry_does_not_raise`
is the regression test for this). **Call-site rule**: from the service layer, immediately after the
triggering action's own successful `db.session.commit()` — identical placement rule to
`AppNotificationService` above. The one exception is `app/routes/auth.py` (`register`/`login`/
`oidc_callback`/`logout`, plus the password-change branch of `update_profile`): there is no
dedicated `AuthService` in this app, so those call `AuditService.log()` directly from the route.
`logout()` calls it *before* `logout_user()` — `current_user` would already be anonymous afterward.
Service methods that already receive the acting user as a parameter (`SwapService`'s `requester`/
`user`/`admin`) pass `actor=` explicitly rather than relying on `current_user` resolution, since
`SwapService` never references `current_user` internally (confirmed via grep) and shouldn't start
just for this.

`/admin/audit-log` (`app/routes/admin_audit_routes.py`) lists entries with filters (actor, action
domain, date range) and a purge action. Purge deletes entries older than
`SettingsService.get_audit_log_retention_days()` (admin-editable at `/admin/settings`, same
`Setting`-wins/fallback pattern as the rest of `SettingsService`) — **unlike** every other
`SettingsService` retention-style setting, there is no numeric fallback: `None` means "keep every
entry, purge nothing" until an admin explicitly opts in, since defaulting an audit trail to silently
deleting its own history would be a surprising, not a safe, default.

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
scripts no-op silently (exit 0) if notifications aren't enabled or SMTP config is incomplete. Both
scripts also check `SettingsService.get_notifications_enabled()` (DB-stored `Setting` override,
admin-editable at `/admin/settings`, falls back to the `NOTIFICATIONS_ENABLED` env var) inside
their existing `app.app_context()`, in addition to (not instead of) the SMTP-completeness check —
SMTP host/credentials stay env-only (secrets, not migrated to `Setting`).
`app/services/notification_service.py::NotificationService` does the actual work (date math via
`next_monday()`/`next_friday()`, always strictly future even if run on the target weekday itself;
per-recipient SMTP failures are logged and don't block the rest of the batch); it calls
`app/utils/notifications/email_sender.py::send_email()` (stdlib `smtplib`/`email`, no Flask-Mail
dependency) with Jinja2 templates rendered from `app/templates/emails/`. `NotificationLog` is the
idempotency guard — re-running a script for an already-processed period is a no-op.

Two independent gates, checked in order — don't conflate them: the org-wide
`SettingsService.get_notifications_enabled()` above short-circuits the entire script (no user gets
anything); `User.shift_notifications_enabled`/`oncall_notifications_enabled` (both default `True`)
are then checked per-recipient inside `send_weekly_shift_notifications()`/
`send_weekly_oncall_notification()` — a user who opted out is skipped (tracked in
`NotificationBatchResult.skipped_disabled_by_user`, distinct from `skipped_already_sent`) *without*
writing a `NotificationLog` row, so re-enabling mid-week and rerunning the script still catches
them up. Editable at `/profile/settings` (`app/routes/auth.py::profile_settings`) — a page separate
from `/profile/update` (name/email/password only) since the notification section there is
conditionally shown/hidden based on the org-wide toggle, which doesn't belong mixed into an
identity-focused form. Submitting the notification checkboxes while the org-wide toggle is off is
deliberately ignored server-side (not just hidden client-side), so a stale form can't silently flip
a preference the user never actually saw.

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
available regardless. `BackupService.get_config()` layers any DB-stored `Setting` override
(`backup_retention_days`/`backup_max_backups`, admin-editable at `/admin/settings`) on top of
`BackupConfig.from_env()` — but this only affects admin-UI-triggered actions (`create_now`/
`cleanup_now`/`list_all_backups`); the standalone cron-invoked `scripts/backup_database.py` stays
100% env-var-driven by design, so its isolation guarantee (above) is untouched — an admin who wants
both paths in sync must keep the env var and the DB setting equal manually. `get_config()` silently
skips the DB lookup (falls back to env only) when called outside a Flask app context, since some
callers (tests) invoke it without one. Docker: `docker/entrypoint.sh` starts `crond` if `NOTIFICATIONS_ENABLED` and/or
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

### Multi-timezone support

Display-only, not a storage refactor: `Shift`/`OnCall` still store naive wall-clock `datetime`s
(no tzinfo), now meaning explicitly "local time in the organization's `default_timezone`
`Setting`" instead of a tacit "Europe/Paris" assumption. **Don't** interpret the naive-datetime
call sites in `app/services/shift_service.py`/`oncall_service.py`/`app/utils/automation/` as a bug
to fix — a shift's stored digits are already correct once the org timezone is known; a per-user
timezone preference never redefines when a shift happens, only how it's displayed for that user. A
full UTC-aware storage refactor was considered and rejected as disproportionate for this
requirement — it would touch every naive-datetime call site above for no correctness gain beyond
what the two mechanisms below already provide.

`User.effective_timezone()` resolves the *display* timezone for a given user: their own
`timezone` column if set, else `SettingsService.get_default_timezone()`. Two independent
mechanisms consume it, with different rules — don't conflate them:

- **ICS export** (`app/utils/export/ics_exporter.py`) always uses the org's `default_timezone`,
  **never** a viewer's personal preference — `ExportService` passes
  `tz_name=SettingsService.get_default_timezone()` explicitly. Attaching a viewer's own tz here
  would *relabel* the stored digits without translating them (a real bug caught during this
  feature's own design review), producing a wrong instant in the exported file. The exporter
  attaches real `zoneinfo` tzinfo to `dtstart`/`dtend` and calls `Calendar.add_missing_timezones()`
  to generate a matching `VTIMEZONE` component — this is what fixes the previous "floating time"
  bug (no tzinfo at all, so every calendar client guessed its own local timezone). Translation to
  the *viewer's* device timezone is the receiving calendar client's job, standard RFC 5545
  behavior — not this app's.
- **FullCalendar JSON API** (`app/services/schedule_service.py::build_calendar_events`,
  `app/routes/shift_routes.py`'s `api_create_shift`/`api_update_shift`,
  `app/routes/oncall_routes.py`'s `api_update_oncall`) *does* translate into the viewer's own
  `effective_timezone()`, both directions, via `app/utils/helpers/timezone_helpers.py`
  (`to_viewer_timezone()` for reads, `to_org_timezone()` for writes back to storage — drag & drop
  and the shift-creation modal both go through the write side). This is what makes the
  `/profile/settings` timezone preference visibly change the calendar, not just the ICS feed.
  `app/static/js/calendar/fullcalendar-config.js` sets `timeZone: 'UTC'` on the `Calendar`
  instance specifically so it never reinterprets the already-translated digits against the
  browser's own system clock — all the real `zoneinfo` conversion happens server-side, avoiding a
  `moment-timezone`/`luxon` plugin (this app is CDN-only, see "Frontend" above). Every Date
  getter/constructor in that file must stay consistent with this contract (UTC getters, never
  `new Date(str)` on a timezone-less string) — see `formatDateForInput`'s and the create-shift
  modal's comments if you touch this file. `Leave` dates have no time component and need no
  conversion in either mechanism.

Known, deliberately unaddressed by this feature: `OnCall.is_active()` (`app/models/oncall.py`)
compares the naive-UTC value written by `BaseModel`'s `created_at`/`updated_at` pattern against a
naive-*local* `datetime.now()` — a pre-existing bug unrelated to per-user timezones, left alone
here to avoid folding an unrelated behavior change into this feature. `ICS_TOKEN_EXPIRY_DAYS`
(migrated to `Setting` for scope consistency with the other backup/notification settings) has no
enforcement point anywhere in `app/` — it's a documented no-op, not wired to any actual token
expiry check.

### Multi-language support (i18n)

French/English, same architecture as multi-timezone support above (org default + personal
override), built with **Flask-Babel 4.0.0** — `Babel(app, locale_selector=fn)`, not the
deprecated `@babel.localeselector` decorator. Flask-Babel reintroduces `pytz` as a transitive
dependency (this app dropped it in favor of `zoneinfo`) — harmless, Flask-Babel only uses it
internally for its own formatting helpers, never called here; don't "fix" this by removing it.

`User.language` (nullable `String(5)`, room for a future regional variant like `"en-US"` without
a new migration) mirrors `User.timezone`: `None` means "use the org default".
`User.effective_language()` resolves it the same way as `effective_timezone()` — own value if
set, else `SettingsService.get_default_language()`. `SettingsService.DEFAULT_LANGUAGE_KEY`/
`FALLBACK_DEFAULT_LANGUAGE` follow the same `Setting`-wins/env-falls-back pattern as the rest of
`SettingsService` — **except** there is no env var counterpart for language (a brand new concept,
never configurable before this feature): `FALLBACK_DEFAULT_LANGUAGE = "fr"` is a hardcoded
constant, not an env read. This fallback is also structurally load-bearing for the test suite
(see below).

**`app/__init__.py::get_locale()`** is the Flask-Babel `locale_selector` callback: authenticated
user's `effective_language()` if a real request context exists, else
`SettingsService.get_default_language()`. Deliberately **no `Accept-Language` sniffing** — org/user
settings stay the single source of truth, consistent with `effective_timezone()`, and it keeps
anonymous pages (login, error pages) deterministic across visitors. `get_locale` is registered
twice: once as Flask-Babel's `locale_selector`, and separately as a Jinja global
(`app.jinja_env.globals["get_locale"]`) for `base.html`'s `<html lang="{{ get_locale() }}">` —
Flask-Babel's `init_app()` auto-injects `gettext`/`ngettext`/`_` and the `jinja2.ext.i18n`
extension into Jinja, but **not** `get_locale` itself (confirmed via `inspect.getsource()` on the
installed package), so it needs this explicit registration or every template render throws
`UndefinedError`.

**Don't call `app`'s `get_locale()` directly from application code** (e.g. `format_date_fr()` in
`app/utils/helpers/common_helpers.py`) — it's the raw locale-selector callback and ignores an
active `force_locale()` override. Use `flask_babel.get_locale()` instead (the *resolved* current
locale), which respects `force_locale()`. This distinction matters specifically for the email
path below, where each recipient is rendered inside its own `force_locale()` block.

**Two independent translation-consuming mechanisms**, each with its own resolution point — don't
conflate them:

- **HTTP requests** (templates via `{{ _(...) }}`/`{% trans %}`, `flash()` messages, service-layer
  error strings) resolve through `get_locale()` above, once per request, transparently.
- **Weekly reminder emails** (`app/services/notification_service.py`) have no real request
  context (cron-triggered, `app.app_context()` only) and batch multiple recipients who may have
  different language preferences — each recipient's `html_body`/`text_body`/subject render inside
  `with force_locale(user.effective_language()):`, never a single upfront translation for the
  whole batch. `force_locale()` only needs Flask's `g` (confirmed via source inspection:
  `_get_current_context()` checks `if not g: return None`), so it works from an `app_context()`
  alone, no real request needed. The same per-recipient pattern is used by
  `AppNotificationService` (in-app bell notifications, see "In-app notifications" above) for the
  same reason — a notification persisted now may be read later by a user with a different
  language than whoever triggered the event.

**JS strings**: this app is CDN-only with no build step (see "Frontend" above), so there's no
i18next-style client pipeline. Instead, `app/utils/helpers/js_translations.py::get_js_translations()`
(each value passed through `_()`) is injected via `base.html` as a `<script type="application/json"
id="i18n-strings">` tag — same JSON-injection pattern already used for `#calendar-events-data` —
and read at runtime by `app/static/js/utils/i18n.js::getString(key)` (caches the parsed JSON on
first call). Call sites: `fullcalendar-config.js` and `accessibility.js`. `getString()` has no
placeholder-interpolation support (unlike Python's `%(name)s` gettext placeholders) — the one
call site that needs a dynamic value (`accessibility.js`'s form-validation error) does a plain
`.replace('%(field)s', fieldName)` on the returned string instead. Most JS-adjacent user-facing
text (`onclick="return confirm('...')"` attributes) actually lives directly in Jinja templates,
not JS files, and is translated there via the normal `{{ _(...) }}` mechanism — only text
hardcoded inside `.js` files itself needs `getString()`.

**Translation catalog workflow**: `babel.cfg` scopes extraction to `app/**.py` and
`app/templates/**.html`/`**.txt` only (not `scripts/`, `tests/`, `migrations/` — no user-facing
text there). `make babel-extract`/`babel-update`/`babel-compile` wrap `pybabel extract`/`update`/
`compile`; catalogs live at `app/translations/<locale>/LC_MESSAGES/messages.po`. **`fr.po` is
committed with every `msgstr` left empty** — gettext falls back to the `msgid` (the original
French source string) when `msgstr` is empty, so this is intentionally a no-op catalog, not an
oversight: French rendering is identical whether or not `fr.po` exists at all. `en.po` carries the
real translation work — every `msgid` has a real English `msgstr`. `.mo` files are compiled
build artifacts, gitignored (`*.mo`/`*.pot`) — `docker/Dockerfile` runs `pybabel compile` during
the image build, and `tests/conftest.py`'s session-scoped autouse `_compile_babel_catalogs`
fixture does the same before the test suite runs. Without one of these, a fresh checkout has no
`en.mo`, and Flask-Babel silently falls back to the French `msgid` even when `default_language`
is set to `"en"` — the exact bug class `TestEnCatalogTranslation` in
`tests/integration/test_i18n.py` exists to catch (that test, plus the general **"fr.po is
committed empty" invariant**, are why the 1000+ pre-existing tests stay green through this
feature with zero changes: `BABEL_DEFAULT_LOCALE = "fr"` + `FALLBACK_DEFAULT_LANGUAGE = "fr"` mean
`get_locale()` resolves to `"fr"` in every fixture-built test app, where gettext's empty-`msgstr`
fallback makes every `_()` call render exactly the original French text).

### Date/time display format

Same architecture again: org default (`SettingsService.default_date_format`/`default_time_format`)
+ personal override (`User.date_format`/`User.time_format`), resolved via
`User.effective_date_format()`/`effective_time_format()`. Values are **strftime patterns
themselves** (`"%d/%m/%Y"`, `"%m/%d/%Y"`, `"%Y-%m-%d"` for dates; `"%H:%M"`, `"%I:%M %p"` for
time), not an indirection code — `SettingsService.SUPPORTED_DATE_FORMATS`/`SUPPORTED_TIME_FORMATS`
enumerate the only valid values, `get_date_format_choices()`/`get_time_format_choices()`
(`app/utils/helpers/common_helpers.py`) pair each pattern with a *computed* sample render (e.g.
`datetime(2026, 12, 31).strftime(pattern)`), never a hand-typed label, so the `<select>` option
text can never drift from what the pattern actually produces.

`app/__init__.py::get_date_format()`/`get_time_format()` mirror `get_locale()`'s resolution order
and request-context guard, with one addition: **both cache their result on `flask.g` for the
lifetime of the request**. `get_locale()` doesn't need this because `flask_babel.get_locale()`
already caches internally once Babel resolves it — but there is no equivalent library-level cache
here, and templates like `schedule.html` call the `format_date`/`format_time` Jinja filters once
per table row. Without the `flask.g` cache, that's a real N+1 (`Setting.get()` hits the DB on every
filter call) — caught once already by
`test_performance.py::test_schedule_query_count_stable_across_dataset_size` during this feature's
own development; keep that test green if you touch either resolver.

Three Jinja filters (`app/utils/helpers/common_helpers.py`, registered in `app/__init__.py`
alongside `date_fr`): `format_date`, `format_time`, `format_datetime` (the latter is just
`format_date() + " " + format_time()`). These replace essentially every display-facing
`.strftime('%d/%m/%Y')`/`.strftime('%H:%M')` call across the templates — but **not** every
`strftime()` call: `<input type="date">`/`<input type="datetime-local">` `value` attributes and
`date_str=...` URL route parameters (e.g. `schedule.html`'s `delete_all_shifts_for_week`) must
stay `strftime('%Y-%m-%d')`, since those are consumed by the browser's native date input or parsed
back by a route with `datetime.strptime(..., "%Y-%m-%d")` — never display, and never
format-preference-aware. Don't "fix" these by pointing them at `format_date` too. The weekly
reminder emails (`app/templates/emails/*.html`/`*.txt`) also went through this filter
retrofit — as a side effect, the weekday name there now goes through the `date_fr` filter (already
locale-aware, see above) instead of a raw `strftime('%A')`, which fixed a latent bug: `%A` depends
on the OS locale (`locale.setlocale`), never reliably French in a WSGI process, so emails were
likely showing English weekday names even in French - see `format_date_fr()`'s own docstring for
why this codebase avoids `%A`/`%a` directly anywhere.

Emails are a **display-format exception**, same boundary as timezone (see above): `NotificationService`
renders inside `force_locale(user.effective_language())` per recipient for *text*, but
`get_date_format()`/`get_time_format()` have no request context during a cron-triggered send
(`app.app_context()` only, `has_request_context()` is `False`), so they always fall through to the
**org default**, never the recipient's personal format preference. This mirrors the existing
timezone behavior in emails (org-canonical time, not per-recipient) — not a bug to fix by threading
the recipient through these resolvers.

Beyond Jinja: `base.html` exposes the resolved patterns as `<body data-date-format
data-time-format>`, the one non-Jinja-filter consumption point every other piece of
format-aware JS reads from. `app/static/js/calendar/fullcalendar-config.js` derives a boolean
`hour12` from `data-time-format` (`.includes('%I')`) to drive FullCalendar's own
`eventTimeFormat`/`slotLabelFormat` — the calendar grid's own hour display, independent of any
Jinja-rendered text. `app/static/js/utils/date.js` (`formatDate`/`formatTime`/`formatDateTime`,
used by `swap-form.js`'s dynamically-fetched target-shift dropdown) reads the same two data
attributes and switches on the pattern directly, rather than attempting a general strftime-in-JS
engine — safe specifically because `SUPPORTED_DATE_FORMATS`/`SUPPORTED_TIME_FORMATS` above are a
closed, small enumeration, not arbitrary user input. Both files use UTC getters
(`getUTCDate()`/`getUTCHours()`/...), never local ones — same rule as documented at the top of
`fullcalendar-config.js`: a date-only ISO string (`"2026-07-16"`, no time/offset) parses as UTC
midnight, and a local getter would reinterpret it against the browser's own timezone and silently
shift the day.

## Testing conventions

`tests/conftest.py` defines the fixture chain: `test_app` builds a fresh app via
`create_app('app.config.TestingConfig')` per test function (drops/recreates all tables, disables
Talisman/OIDC/rate-limiting), `client` wraps its test client, and `logged_in_client` logs in
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
