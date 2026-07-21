# TESTING_SUMMARY.md - Kairos Testing Strategy

## 📊 Global Overview

- **Last updated**: July 21, 2026 (1.0.0-RC2 full validation pass)
- **Total number of tests**: 1394 (720 unit + 642 integration + 32 e2e)
- **Tests passing**: 1394 ✅
- **Tests failing**: 0
- **Code coverage**: **94%** (`--cov=app`)
- **Lint (ruff)**: clean - **0 errors**
- **Types (mypy)**: clean - **0 errors**
- **Formatting (black)**: compliant
- **Security (bandit)**: 0 findings in `app/` (all flagged items are test-only fixture literals - mock passwords/tokens)
- **Dependencies (pip-audit)**: 0 known vulnerabilities
- **Duplicate code (`find_duplicates.py`)**: none detected

---

## 🎯 Testing Strategy

### Philosophy: four layers, not three

1. **Unit tests** (`tests/unit/`): isolated components (models, config,
   automation, helpers, decorators) - no HTTP client.
2. **Integration tests** (`tests/integration/`): Flask routes via the
   test client (`client`, `logged_in_client`), CSRF/CSP/permissions,
   no real browser.
3. **E2E tests - test client** (`tests/e2e/test_user_flows.py`):
   full user journeys (login → action → verification →
   logout), always via the Flask test client.
4. **E2E tests - real browser** (`tests/e2e/test_browser_flows.py`,
   `test_oidc_browser_flow.py`): Playwright + Chromium, **optional**
   (see dedicated section below). Exists precisely because the
   three previous layers never execute JS nor apply
   CSS/CSP - an entire category of bugs (3 real CSP bugs found in
   PR #103) is structurally invisible to them.

### Tools used

- **Framework**: `pytest` (+ `pytest-flask`, `pytest-cov`)
- **Fixtures**: `tests/conftest.py` (`test_app`/`client`/
  `logged_in_client` chain) + `tests/fixtures/` (models: user, group, shift,
  leave, oncall, swap)
- **Real browser (optional)**: `pytest-playwright` + Chromium, see
  `requirements-e2e.txt`
- **Tests workflow**: GitHub Actions (`.github/workflows/tests.yml`, 4
  jobs: test, e2e, lint, security) — deliberately **not** run on every push/PR
  while the repo is private (GitHub Actions minutes are metered on a
  private repo, unlike a public one). Triggers: a version tag push
  (`v*`, just before a release), weekly (`schedule`, catches
  dependencies turning vulnerable with no code change), or on demand
  (`workflow_dispatch`). The former GitLab CI config
  (`.gitlab-ci/.gitlab-ci.yml`) was removed — GitLab never actually
  executed against this GitHub-hosted repo. Docker build/push is a
  separate, manual-only workflow
  (`.github/workflows/docker-release.yml`), not part of this one.

---

## 📁 Test structure

```
tests/
├── conftest.py                      # Fixture chain: test_app, client, logged_in_client
├── fixtures/                        # test_user, test_group, test_shift, test_leave, test_oncall...
│
├── unit/                            # 682 tests - isolated components, no HTTP
│   ├── test_service_account_model.py     # ServiceAccount: SHA-256 token/hash, is_valid()
│   ├── test_service_account_repository.py
│   ├── test_service_account_service.py   # create/revoke/regenerate + audit trail
│   ├── test_models.py               # User, Group, Shift, OnCall, Leave, ShiftType, NotificationLog
│   ├── test_repositories.py         # Data access layer
│   ├── test_services.py             # Business logic layer
│   ├── test_automation*.py          # Shift/on-call business rules (3 files)
│   ├── test_advanced_shift_automation.py
│   ├── test_shift_rotation_fix.py
│   ├── test_decorators_unit.py
│   ├── test_helpers.py
│   ├── test_ics_export.py
│   ├── test_config.py               # DATABASE_URL, normalize_database_uri() (MySQL/PostgreSQL
│   │                                 #   driver rewrite), SQLALCHEMY_ENGINE_OPTIONS
│   ├── test_run_functions.py        # setup_database/create_default_data
│   ├── test_oidc_config.py          # OIDCConfig (25 tests)
│   ├── test_oidc_auth.py            # OIDCAuthLib, mocked network (31 tests)
│   ├── test_user_manager_oidc_sync.py  # OIDC user sync (12 tests)
│   ├── test_notification_config.py  # NotificationConfig (SMTP via env vars)
│   ├── test_email_sender.py         # Low-level SMTP sending, mocked
│   ├── test_notification_service.py # Weekly shift/on-call reminders, idempotency
│   ├── test_backup_config.py        # BackupConfig (SMTP/S3 via env vars)
│   ├── test_backup_database.py      # scripts/backup_database.py (independent of app/)
│   ├── test_backup_service.py       # BackupService (/admin/backups support layer)
│   └── test_settings_service.py     # SettingsService (timezone, language, date/time formats...)
│
├── integration/                     # 629 tests - Flask routes, test client
│   ├── test_routes.py, test_*_priority.py, test_*_coverage.py
│   ├── test_admin_*.py              # Admin routes (users/groups/shift-types/automation/backups,
│   │                                 #   service accounts)
│   ├── test_service_account_auth.py # resolve_service_account(): missing/invalid/expired/revoked header
│   ├── test_api_v1_routes.py        # /api/v1/* endpoints (shifts/oncall/leave/users/shift-types)
│   ├── test_api_csrf_exemption.py   # app/api/ blueprints exempted from CSRFProtect
│   └── test_openapi_spec.py         # /api/v1/openapi.json generated, no Swagger UI served
│   ├── test_security.py             # CSP, CSRF, Talisman, access control
│   ├── test_oidc_routes.py          # /login, /oidc/login, /oidc/callback, /logout (13 tests)
│   ├── test_performance.py          # Response time, N+1, compression
│   ├── test_i18n.py                 # get_locale(), <html lang>, en.po catalog (round-trip)
│   ├── test_prometheus_metrics.py, test_health.py
│   ├── test_dark_theme.py, test_theme_fixes.py
│   └── test_error_handlers.py
│
└── e2e/                             # 32 tests
    ├── test_user_flows.py           # 6 tests, Flask test client
    ├── conftest.py                  # live_server_url, oidc_live_servers (Playwright)
    ├── test_browser_flows.py        # 20 tests, real Chromium (optional) - including the creation
    │                                 #   of a service account (token shown once)
    ├── oidc_mock_provider.py        # Real fake OIDC provider (Flask, not Docker)
    └── test_oidc_browser_flow.py    # 6 tests, full SSO flow in a real browser (optional)
```

---

## 🧪 Real browser E2E tests (Playwright) - optional

**NOT installed by default** (`requirements.txt` alone is enough to
run the whole app and the rest of the suite). To enable them:

```bash
pip install -r requirements-e2e.txt
playwright install chromium
```

Without this, `pytest tests/` cleanly skips the two modules involved
(`pytest.importorskip("playwright")` at the top of the file) - shown as
`skipped` in the summary, never as a failure or a collection error.
Explicitly verified: without playwright installed, the E2E suite becomes
6 passing + 2 skipped (instead of 24 passing).

What this layer verifies that no other layer can:
- **Zero console errors** on 8 key pages (`TestNoConsoleErrors`) -
  generalizes into a permanent safeguard the manual audit that found 3 real
  CSP bugs during the UI/UX overhaul (inline script blocked on 2 pages,
  FullCalendar icon font blocked by a missing `font-src`)
- Mobile burger menu (`is-active`/`aria-expanded` toggle, pure JS)
- Dark theme (`localStorage` persistence, nonexistent server-side)
- Copy-to-clipboard button (real visual feedback)
- **Full SSO flow** against a real fake OIDC provider
  (`oidc_mock_provider.py`, a real Flask app on a separate port,
  not a Python mock): browser redirect, real IdP login page
  with an actual click, real server-to-server exchanges (discovery, token,
  userinfo), session actually established and invalidated. Allowed
  finding and fixing a real blocking bug (infinite redirect loop
  `/login` ↔ `/oidc/login` on any forced SSO failure).

Full detail: `report/E2E Playwright - Tests navigateur réel.md`.

---

## 🔐 OIDC/SSO Tests

Zero tests existed before July 13, 2026 despite ~450 lines of logic
(`config_oidc.py`, `app/auth/oidc_auth.py`, `app/auth/user_manager.py`).
Three levels, deliberately complementary (see
`report/E2E Playwright - Tests navigateur réel.md` for the rationale):

1. **Unit** (68 tests): each method isolated, network calls
   (`requests.get/post`) mocked, unsigned test JWT (the code never
   verifies a signature, only expiration).
2. **Integration** (13 tests): route wiring, `oidc_auth` mocked at
   the routes module boundary. **Found a real blocking bug**:
   infinite redirect loop on any OIDC failure when SSO is
   forced (`OIDC_DISABLE_BASIC_AUTH=true`) - fixed.
3. **Real browser E2E** (5 tests): see previous section.

---

## 🔧 Test commands

```bash
# Everything (test -> lint -> format -> security)
make all

# Tests only
python -m pytest tests/ -v --tb=short         # everything (make test)
python -m pytest tests/unit/ -v               # one layer
python -m pytest tests/test_models.py -v      # one file
python -m pytest tests/unit/test_models.py::TestUserModel::test_user_creation -v  # one test

# Coverage
python -m pytest tests/ --cov=app --cov=config --cov-report=term-missing
python -m pytest tests/ --cov=app --cov=config --cov-report=html

# Real browser E2E (optional, see dedicated section)
pip install -r requirements-e2e.txt && playwright install chromium
python -m pytest tests/e2e/test_browser_flows.py tests/e2e/test_oidc_browser_flow.py -v

# Code quality
ruff check . --config=.ruff.toml
mypy app/ tests/ --ignore-missing-imports --allow-untyped-decorators
black --check . --exclude=".git|__pycache__|instance|venv"

# Security (blocking, part of `make security` and the CI `security` job)
bandit -r app/ tests/
pip-audit -r requirements.txt   # no API key required (replaced `safety scan`)
```

---

## 📝 Best practices established in this project

1. **Reuse existing fixtures** (`test_app`, `client`,
   `logged_in_client`, `test_user`, `test_group`, etc.) rather than
   building app instances by hand - except for an explicit need
   for a different config (Talisman/CSRF re-enabled, OIDC configured),
   in which case build a dedicated fixture that `monkeypatch`es on top
   of `test_app` rather than duplicating `create_app()`.
2. **Clear naming**: `test_login_route_redirects_to_dashboard()`, not
   `test_login()`.
3. **Isolation**: `test_app` recreates all tables for every test
   (function-scoped). Global state (`OIDCConfig`, `oidc_auth`
   singletons) explicitly saved/restored whenever a test modifies it (see
   `tests/unit/test_oidc_config.py::clean_oidc_env`,
   `tests/integration/test_oidc_routes.py::oidc_mode`).
4. **Verify, don't assume**: a test that has never been seen to fail
   is not a safeguard. Before trusting a new regression test,
   deliberately break the code it's supposed to protect and
   confirm it fails with the right message (pattern applied to
   `TestNoConsoleErrors`: `font-src` temporarily removed from
   `CSP_POLICY`, red test confirmed, then restored).
5. **Mock at the right boundary**: mock network calls
   (`requests.get/post`) in unit tests, mock the calling module's
   methods (`app.routes.auth.oidc_auth.X`) in integration
   tests, mock nothing in browser E2E (real server, real
   fake OIDC provider).
6. **Only one authenticated HTTP client per test**: combining
   `logged_in_client` and `non_admin_client` (or simply two
   `test_app.test_client()`) in the same test ends up sharing
   their cookiejar - a client that never logged in silently inherits
   the session of whichever login happened first in the test (an artifact
   of the test harness, not an application bug). To test a permission
   after an admin action, set up the desired state directly via the
   service (e.g. `SwapService.approve_swap(...)` inside `app_context()`)
   rather than via a second, differently-authenticated HTTP request.
7. **Never nest `with test_app.app_context():` when a test
   mutates then re-verifies a fixture object via a fresh query**:
   `test_app` already has an active context for the entire duration of the test (see
   `tests/conftest.py`). Pushing a second one makes `db.session` resolve
   to a **different** SQLAlchemy session than the one used by the
   fixtures - confirmed by SQLAlchemy's own error: `"Object ...
   is already attached to session 'N' (this is 'M')"`. An object created by
   a fixture (attached to session N) mutates normally in memory inside
   the nested block (session M), but `db.session.commit()` in that block
   commits NOTHING for that object - it stays invisible even against raw
   SQL afterwards. Harmless as long as a test only checks the in-memory
   Python attribute (`object.field == value`, the vast majority of the
   tests in this file); silently wrong as soon as it checks
   actually-persisted state (`Model.query.count()` after a bulk
   `.delete()`, for example - see `TestPurgeSwaps` in
   `test_swap_service.py`, where this caused a test to fail
   100% reproducibly despite correct application code). An object
   **created** inside the nested block (not from a fixture) is not
   affected, since it's added directly to session M. The real
   app is never affected: an HTTP request has a single context, never
   nested.

---

## 📈 History

- **June 26, 2026**: 522 tests (515 passing, 2 failing, 7 skipped),
  ~66% coverage, flat structure (`tests/test_*.py`), no CI.
- **July 13, 2026**: 881 tests (0 failing), ~88% coverage, 4-layer
  structure (`unit/`/`integration/`/`e2e/` + optional real browser),
  GitLab CI, complete OIDC suite, `make all` (test + lint
  ruff/mypy + black formatting) fully clean.
- **July 13, 2026 (continued)**: 891 tests (0 failing). Improvement of
  the shift/on-call automation engine (PR #105: removal of the dead
  generic engine, fixed dry-run, atomic rebalancing, new minimum-staffing
  rule, fixes to delete confirmations/duplicate on-calls/
  calendar reload) followed by rollout of weekly email
  notifications (shift/on-call reminders, `NotificationLog`
  anti-duplicate guard, SMTP via environment variables,
  standalone cron scripts).
- **July 13, 2026 (continued)**: 944 tests (0 failing). Backup system
  overhaul (PR #107): removal of dead scaffolding
  (`encrypt`/`encryption_key`/`frequency`), opt-in `BACKUP_ENABLED`
  (`false` by default), success/failure email alerts reusing the
  notifications system, `BackupService` + admin interface
  (`/admin/backups`: list, create, cleanup, download with
  path-traversal protection), Docker integration (conditional crond
  shared with notifications).
- **July 13, 2026 (continued)**: 931 tests (0 failing). Full UI/UX
  overhaul, Bulma → Tailwind CSS 4 + daisyUI 5 via cdnjs CDN (PR #108):
  removal of local vendoring (`app/static/vendor/`,
  `scripts/download_vendor_assets.py`,
  `tests/unit/test_vendor_assets.py`), Font Awesome in SVG+JS mode (the
  cdnjs 7.2.0 `.woff2` files are corrupted, rejected by Chromium's
  font sanitizer), FullCalendar kept at 6.1.21 via jsDelivr (7.0.0
  raises a real runtime error in its own compiled Preact code,
  confirmed via three different CDN strategies - an upstream bug, not
  a hosting issue). Net drop in test count compared to the
  previous entry: removal of `test_vendor_assets.py` and tests
  specific to now-obsolete Bulma variables/classes, partially
  offset by new theme tests (`test_dark_theme.py`
  rewritten). Full suite (unit + integration + real browser e2e) green,
  including a real JS bug found in manual testing (not by the
  automated suite): the theme toggle broke after the Font
  Awesome SVG+JS conversion (`querySelector('i')` no longer matched),
  fixed by targeting by class (`.fa-moon, .fa-sun`) instead of by tag.
- **July 14, 2026**: 933 tests (0 failing). Dracula (dark theme) /
  Alucard (light theme) visual overhaul on top of the Tailwind/daisyUI
  base from PR #108 (PR #110): palette sourced 100% from the official
  draculatheme.com/spec spec, mobile menu converted to a native daisyUI
  `drawer` (replacing the homemade `hidden` toggle), shift creation
  modal rewritten as a native `<dialog>` (`showModal()`/`close()`) with
  HTML escaping added for interpolated data, native daisyUI
  components adopted wherever the CSS was hand-rolled (`stats`,
  `list`, `avatar`, `breadcrumbs`, `tooltip`, `collapse`, `hero`,
  `swap`). Real browser E2E suite updated for the new mobile menu
  mechanism (checkbox instead of `hidden` class) and enriched with a
  keyboard-toggle test; real bug found in manual testing (daisyUI's
  `avatar-placeholder` component targeting its centering styles at a
  child `<div>`, not a `<span>` - fixed).
- **July 14, 2026**: 975 tests (0 failing, +42). Shift swaps between
  users (`SwapRequest`: request, one-way give-away or reciprocal,
  admin approval/rejection) - new model/repository/service/
  routes layer (user + admin) with no prior approval-workflow
  precedent in this repo (leave requests have none, and stay that way).
  New tests: model
  (`TestSwapRequestModel`), service (`TestRequestSwap`/`TestCancelSwap`/
  `TestApproveSwap`/`TestRejectSwap` - notably covering business-rule
  re-validation at approval time, not just at creation), user and
  admin routes (`tests/integration/test_swap_routes.py`, including
  admin vs non-admin permissions). Completed the same day with
  `revert_swap` (undoing a swap *after* admin approval, a distinct
  `REVERTED` status separate from `CANCELLED`, which stays reserved
  for the requester self-cancelling before validation) -
  `/admin/swaps` now also shows already-approved swaps, not just
  pending ones (`TestRevertSwap`, associated route tests). Test
  pitfall discovered along the way: combining `logged_in_client` and
  `non_admin_client` (or two `test_app.test_client()`) in the same
  test ends up sharing their cookiejar - an artifact of the test
  harness, not an application bug; always isolate a single
  authenticated HTTP client per test (set up the "already approved"
  state directly via the service if needed, not via a second
  admin-authenticated HTTP request).
- **July 14, 2026**: 994 tests (0 failing, +19). In-app
  notifications (sidebar bell icon, unread badge): `AppNotification` -
  distinct from `NotificationLog`, which stays reserved for weekly
  email reminders and is never displayed. `AppNotificationService`
  triggered synchronously by `SwapService` (new request -> all
  admins; approval/cancellation -> requester + recipient; rejection ->
  requester only). Real bug found and fixed *before* it broke
  production: the new `context_processor` (unread badge) accessed
  `current_user.is_authenticated` without checking
  `has_request_context()` - `NotificationService` (weekly emails)
  renders its templates via a plain `app_context()` (cron scripts,
  never an HTTP request), where `current_user` resolves to `None`
  rather than raising an exception; result:
  `'NoneType' object has no attribute 'is_authenticated'` on
  **every** reminder email, silently swallowed into
  `NotificationBatchResult.failed`. Caught by the existing suite
  (`tests/unit/test_notification_service.py`, 5 red tests) when
  rerunning the full suite after the feature landed - not by a test
  written specifically for this bug. A reminder that a
  `context_processor` runs for *every* template render in the app,
  including outside an HTTP request.
- **July 14, 2026**: 1006 tests (0 failing, +12). User feedback
  fixes on shift swaps + notifications: `REVERTED` status badge
  simplified to "Cancelled" (instead of "Cancelled after
  approval") on the user-facing page; the "Swap rejected." flash
  changed from `success` (green) to `warning` (orange), a rejection
  not being a success from the requester's point of view. Purging
  added on both sides: read notifications
  (`AppNotificationService.purge_read`, keeps unread ones) and
  completed/non-pending swap requests
  (`SwapService.purge_resolved_for_user` on the user side - matched
  as requester *or* recipient, so it can make a row disappear that's
  still visible to the other party, a single shared historical
  record; `purge_all_resolved` on the admin side, for every user).
  Major discovery along the way, documented in detail under "Best
  practices" above (item 7): nesting
  `with test_app.app_context():` inside a test whose `test_app`
  already has an active context makes `db.session` resolve to a
  different SQLAlchemy session than the fixtures' - a commit inside
  the nested block then silently persists nothing for a fixture
  object, unless the state is checked via a fresh query. This made
  a new purge test fail 100% reproducibly in isolation despite
  correct application code (confirmed via the equivalent HTTP route
  tests, which were unaffected) - probably latent and invisible in
  the rest of the suite until now, since almost all existing tests
  only check the in-memory Python attribute after an action, never
  freshly-queried state.
- **July 16, 2026**: 1099 tests (0 failing, +93). Two features shipped
  (PR #115 then #116, same Setting/User architecture reused for
  each):
  - **French/English i18n** (Flask-Babel): `User.language` +
    `SettingsService.default_language`, full retrofit of all
    user-facing text (55 templates, every `flash()`, service
    errors, hardcoded JS via a server→JS JSON mechanism since there's
    no build step, 4 email templates rendered in each recipient's
    language via `force_locale()`), fully translated `en.po` catalog
    (806 strings), `fr.po` deliberately left with empty `msgstr`
    (standard fallback to French, unchanged behavior for the existing
    suite). New `tests/integration/test_i18n.py`, including a dedicated
    round-trip test (`TestEnCatalogTranslation`) that renders a page
    with `default_language="en"` and verifies that English actually
    appears - catching both "string never translated" and "catalog
    never compiled". New session-scoped autouse pytest fixture
    (`tests/conftest.py::_compile_babel_catalogs`): without it a
    fresh checkout has no `.mo` files (gitignored, build artifacts) and
    gettext silently falls back to French even in English.
  - **Configurable date/time formats**: same pattern
    (`User.date_format`/`time_format` +
    `SettingsService.default_date_format`/`default_time_format`), 3
    date formats / 2 time formats, retrofit of display-facing
    `strftime()` calls into 3 new Jinja filters
    (`format_date`/`format_time`/`format_datetime`). Real bug found
    and fixed along the way: N+1 regression
    (`test_schedule_query_count_stable_across_dataset_size`, already
    present in the suite before this session) - the new format
    resolvers didn't have the per-request cache that `get_locale()`
    benefits from internally via `flask_babel`, so every date/time
    cell in a table triggered its own `Setting.get()` query; fixed by
    caching on `flask.g`.
  - Afterwards, when rerunning the full suite: 2 tests found broken
    since the `/profile/update` → `/profile/settings` split (earlier
    session, timezone migration) - `TestApiCreateShiftTimezoneConversion`
    and `TestApiUpdateOncall::test_update_converts_viewer_tz_to_org_tz_for_storage`
    were still posting `timezone` to `/profile/update`, a route that
    only reads name/email/password; the POST was silently ignored and
    no timezone conversion took place. Long misdiagnosed during the
    session as a "pre-existing DST bug" before a careful read of both
    routes' code - fixed by pointing at `/profile/settings`.
- **July 16, 2026**: 1133 tests (0 failing, +34). Audit trail (PR #117):
  `AuditLog` model (append-only) + `AuditLogRepository` +
  `AuditService.log()` as the single write point, dual write to DB +
  `logs/audit.log`. Before this PR, `log_audit_action()` had existed
  in the code for a long time but was never called outside the tests -
  confirmed by grepping `app/routes/`/`app/services/`, zero results.
  Retrofit of all business CRUD (users, groups, shifts, on-calls,
  leave, shift types, the entire swap lifecycle, admin settings) and
  authentication events (successful/failed login,
  logout, registration, password change). Representative tests
  per domain (not systematic per-method duplication, the call
  pattern is identical everywhere) plus a dedicated suite for
  `AuditLogRepository`/`AuditService` (explicit actor resolution
  vs `current_user` vs none, no exception propagation if the write
  fails - `test_failure_writing_entry_does_not_raise`) and for the
  admin route `/admin/audit-log` (filters, pagination, admin-only
  permission, purge with/without configured retention). A test broke
  along the way (`test_resolves_actor_from_current_user_in_request_context`):
  it was counting *all* `AuditLog` rows in the table, but the real
  login performed by the `logged_in_client` fixture now itself writes
  an `auth.login_success` entry - fixed by filtering on the tested
  action instead of counting the whole table.
- **July 16, 2026**: 1176 tests (0 failing, +43). External notifications
  via Apprise (Slack/Discord/Telegram/generic webhooks): new
  `NotificationTarget` model (JSON-encoded categories, `subscribes_to()`
  with the "empty list = all categories" rule) + `AppriseNotificationService`,
  two entry points tested separately - `notify()` (fire-and-forget,
  never propagates an exception even if the repository fails, one
  target failing doesn't prevent the others from being notified) and
  `send_test()` (returns the real success/failure for the admin's
  "Test" button). `apprise.Apprise` talks over the network, so fully
  mocked (`unittest.mock.patch` at the service's import point) - no
  real network call in the suite. Representative tests for each
  retrofitted call site (`SwapService.request_swap()` does trigger
  `notify("swap", ...)`, mocked) rather than per-method duplication.
  Full suite for `/admin/notification-targets`: CRUD, admin-only
  permission, global toggle, test action with mocked success/failure.
- **July 16, 2026**: 1183 tests (0 failing, +7). Added two dedicated
  Apprise categories (`shift_weekly`/`oncall_weekly`) that relay every
  successful weekly send (not just failures like the `system`
  category), with a per-user opt-out independent of the email one
  (`User.apprise_shift_notifications_enabled`/
  `apprise_oncall_notifications_enabled`, new migration), visible
  and editable in `/profile/settings` in its own section (same
  "only apply the checked boxes if the section was actually visible"
  guard as the email section). Tests: relay triggered on success,
  relay absent if the user toggle is disabled (`NotificationService`),
  section hidden/shown depending on the global toggle,
  persistence/ignoring of the checkboxes depending on the global
  toggle (`/profile/settings`).
- **July 16, 2026**: 1193 tests (0 failing, +10). User feedback:
  the simple boolean `apprise_shift_notifications_enabled`/
  `apprise_oncall_notifications_enabled` replaced with actual
  target selection (`User.apprise_shift_target_ids`/
  `apprise_oncall_target_ids`, JSON-encoded list of `NotificationTarget`
  ids, same migration modified in place since not yet merged). New
  `AppriseNotificationService.notify_to_targets(target_ids, ...)`
  method (fire-and-forget, resolves each id at send time and
  silently skips a target deleted/disabled since it was selected).
  `/profile/settings` only displays and accepts targets that are
  enabled AND subscribed to the matching category
  (`NotificationTargetRepository.list_enabled_for_category`)
  - an id submitted outside this eligible set is silently
  ignored (explicitly tested). Apprise documentation link pointed
  to appriseit.com/services.
- **July 16, 2026**: 1224 tests (0 failing, +31). Three independent
  workstreams on the same branch:
  - **Security**: the `nav_links` loop in `base.html` (Home/
    Dashboard/Shifts/On-call/Leave/Swaps) was the only sidebar
    section without a `current_user.is_authenticated` guard - fixes
    `/login` and every 400-504 error page in one go (same shared
    layout). Information leak (internal app structure), not a
    functional bypass (all targeted routes remain `@login_required`).
  - **Two-step shift swap workflow**: new `AWAITING_ADMIN` state
    between the request (`PENDING`) and admin validation - the
    recipient now chooses their own swap shift (or none) at
    confirmation time, or declines directly, before an admin even
    sees the request. No migration needed (`status` stays a free
    `String(20)`, `target_shift_id` already nullable). Full retrofit
    of existing tests (new `confirmed_swap_request` fixture for
    admin approval/rejection/cancellation tests, which no longer
    start directly from `PENDING`) + new `TestConfirmSwap`/
    `TestTargetRejectSwap` tests. `/api/swaps/target-shifts` and
    `swap-form.js` became dead code (the requester no longer chooses
    the return shift) - removed, along with
    `app/static/js/utils/date.js` (no real caller left once
    `swap-form.js` was removed).
  - **Makefile**: 39 targets reduced to 15 (removal of the
    `bug-hunt`/`scripts/bug_hunt.sh` block, confirmed never actually
    run in this repo - `reports/` didn't exist - and already
    diverged from the real `ruff`/`.ruff.toml` config; merging of
    redundant `test-*`/`backup-*` variants into documented direct
    invocations). `find-duplicates` kept as the only genuinely
    useful piece of the old bug-hunt block.
- **July 17, 2026**: 1314 tests (0 failing). v1.0 stabilization (PR
  #122-#127, 6 themed PRs): Docker/dependency hygiene, dead code
  removal (`config.py`/`ProductionConfig`/`DevelopmentConfig`/
  `get_database_type()`), SQL optimization (Apprise N+1, bulk delete,
  missing `joinedload`), full security audit + targeted bug hunt +
  blocking CI, i18n (JS strings + placeholders + 206 backlogged
  `en.po` strings caught up), load test. Two regression tests added
  for two real bugs found *during the load test*: `run.py` was
  forcing `debug=True` on the Flask development server regardless of
  `FLASK_DEBUG` (RCE risk via the Werkzeug debugger), and Flask-Talisman
  forces `SESSION_COOKIE_SECURE=True` independently of
  `TALISMAN_FORCE_HTTPS` (broke login on any plain-HTTP deployment,
  the documented default mode) - both were coupled and fixed
  together. See `report/SECURITY_AUDIT_v1.0.md`,
  `report/BUG_HUNT_v1.0.md`, `report/LOAD_TEST_v1.0.md` for the full
  detail.
- **July 19, 2026**: 1343 tests (0 failing, +29), coverage ~92% → 94%.
  Production-readiness audit, batch 1 (PR #145): translated the
  automation engine's hardcoded French messages
  (`advanced_shift_automation.py`/`oncall_automation.py`) through
  `gettext`, completed `en.po` (12 new msgids + 4 pre-existing
  untranslated/wrongly-fuzzy entries); cached
  `SettingsService.get_default_timezone()` on `flask.g` (was a real
  N+1, one `Setting.get()` per shift/on-call rendered on the
  calendar); bulk-preloaded `AuditLog.actor` in
  `AuditLogRepository.list_paginated()` (same N+1 shape, up to
  `per_page` extra queries on `/admin/audit-log`); removed 3
  confirmed-dead functions (`ShiftRepository.list_in_date_range()`,
  `Config.validate()`, `get_str_from_env()`) and the entire
  `app/utils/optimizations/` module (its one decorator, `@eager_load`,
  was a no-op on its last remaining call site); fixed
  `test_log_http_error` and 4 related assertions in
  `tests/integration/test_error_handlers.py`, all of which were using
  the module-level `app` singleton instead of the `test_app` fixture -
  a source of test-order-dependent flakiness. Also switched CI from
  GitLab (never actually run against this GitHub-hosted repo) to
  GitHub Actions.
- **July 21, 2026**: 1394 tests (0 failing, +51), coverage steady at
  94%. 1.0.0-RC2 batch (PR #159-165, see `ROADMAP.md`): per-day/
  per-section SAVEPOINT isolation for `rebalance_after_leave` (a
  failure on one day no longer wipes the whole ±30-day window);
  `BackupConfig` no longer eagerly `os.makedirs()`s on every
  instantiation (fixed a crash on `/admin/settings` in a read-only
  container); on-call generation replaced with a backtracking search
  maximizing filled weeks, plus a bidirectional interval-based
  spacing check (`AvailabilityIndex`) replacing a scalar "last on-call
  end time" that broke on partial-window regeneration; merged the
  automation dashboard/refresh pages into one, with a proactive gap-
  detection banner; ANSSI-PG-078 password policy (12+ characters, 3-
  of-4 character classes, weak-password rejection) plus forced
  password change on first login, local auth only - never applied to
  OIDC accounts; fixed a real 405 on user/group deletion (`<a href>`
  GET link against a POST-only route); full i18n audit of templates/
  routes/services/JS (10 hardcoded-string sites fixed); `fr.po` policy
  reversed to explicit `msgstr` (was empty + gettext fallback), now
  automated via `scripts/fill_fr_catalog.py`. See `report/
  LOAD_TEST_v1.2.md` for this batch's load-test re-run (zero
  regression, zero errors).
