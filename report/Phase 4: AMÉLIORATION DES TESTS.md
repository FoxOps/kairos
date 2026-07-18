# 📋 Refactoring Report - Phase 4: Test Improvements
**Branch**: `refacto/phase4`
**PR**: [#100](https://github.com/FoxOps/leviia-schedule/pull/100)
**Start date**: 2026-07-11
**Status**: 🟢 Done
**Base**: `main` (includes Phases 1 + 2 + 3, PR #99 merged)

---

## 📈 State of play (before restructuring)

- 29 test files, ~8085 lines, all flat under `tests/`, 511 tests, 511
  passing.
- `pytest-cov` **wasn't installed** even though `CLAUDE.md` already
  documented `pytest tests/ --cov=app --cov=config --cov-report=term-missing`
  as an existing command - the command crashed
  (`unrecognized arguments: --cov=app`). Now installed.
- **Real measured coverage (baseline)**: **56%** (`app/` + `config.py`).
- No dedicated tests for the `app/services/` or `app/repositories/`
  layer (created in Phase 2) - only `ScheduleService` had a few indirect
  tests in `test_main_coverage.py`/`test_main_priority.py`. Everything
  else (`UserService`, `GroupService`, `ShiftService`, `ShiftTypeService`,
  `OnCallService`, `LeaveService`, `ExportService`,
  `AutomationAdminService`) and every repository was only covered
  indirectly through HTTP route tests.
- **No Selenium/Playwright, no chromedriver/geckodriver, no sudo** in
  this environment: impossible to install a headless browser. Decision
  validated with the user: the "E2E" tests will be multi-request flows
  through the existing Flask test client (login -> action -> verify ->
  logout), not real browser automation. Documented honestly rather than
  checking the box with no real basis.

### Coverage distortion from dead code

A significant chunk of the uncovered lines comes from modules already
flagged as unused in `CLAUDE.md`, plus two newly spotted this phase:

| Module | Lines | Coverage | Status |
|---|---|---|---|
| `app/utils/monitoring/__init__.py` | 344 | 0% | dead (already noted in CLAUDE.md) |
| `app/utils/pagination/__init__.py` | 248 | 0% | dead - only reachable via decorators that are themselves never applied (see below) |
| `app/utils/prometheus_metrics.py` | 86 | 0% | conditional (`PROMETHEUS_ENABLED`), not dead but never exercised in tests |
| `app/utils/helpers/env_helpers.py` | 47 | 0% | dead (already noted in CLAUDE.md) |
| `app/utils/cache/cache_helpers.py` | 40 | 0% | dead, zero references anywhere else in `app/` |
| `app/utils/optimizations/__init__.py` (partial) | ~230/292 uncovered | 11% | only `eager_load` is actually imported by routes (`admin_shift_type_routes.py`, `dashboard_routes.py`, `admin_user_routes.py`, `admin_group_routes.py`); `paginated_route`, `paginated_api`, `cached_route`, `cache_result`, `lazy_route`, `lazy_property_cache`, `batch_load`, `bulk_operation`, `retry_on_failure`, `measure_time` are applied on **no** route at all - dead code |

**Decision**: don't write artificial tests for dead code just to inflate
the percentage - that wouldn't test anything real and would mask the
actual problem (code that's never called, which should be deleted, not
tested). An 80% target on the current scope includes ~765 lines of
confirmed dead code; a realistic, honest target covers code that's
actually used. A recommendation to remove the dead code is documented
here, the removal itself left to a separate user decision (out of this
phase's "tests" scope, and `app/utils/monitoring/`/`env_helpers.py` are
already flagged as such in `CLAUDE.md` with no removal requested so
far).

---

## 🎯 Work plan

### 4.1 Test restructuring
- [x] `tests/unit/`: 12 files moved (no HTTP client - models, automation,
      config, helpers...)
- [x] `tests/integration/`: 14 files moved (go through the Flask test
      client - routes, auth, export...)
- [x] `tests/e2e/`: created, filled in the next step (multi-request
      flows, see decision above)
- [x] `tests/fixtures/`: `user_fixtures.py`, `shift_fixtures.py`,
      `leave_fixtures.py`, `oncall_fixtures.py` - extracted from
      `conftest.py` (which keeps only `test_app`/`client`), registered
      via `pytest_plugins`
- [x] `Makefile`: paths updated (`test-main`, `test-dark-theme`) + new
      `test-unit`/`test-integration`/`test-e2e` targets

### 4.2 Improvements
- [x] `unit/test_services.py` + `unit/test_repositories.py`: real tests
      for the business layer created in Phase 2, until now barely tested
      directly (107 tests, repositories 100%, services 90%+)
- [x] Coverage at 80%+: **81%** reached (71% -> 81% via additional dead
      code removal + targeted services/repositories/routes tests, see
      Log). OIDC (`oidc_auth.py`/`user_manager.py`) left out of scope by
      explicit choice.
- [x] Performance tests (response time + N+1 detection on `/schedule`)
- [x] Security tests - **led to two real fixes, not just tests** (see
      Log):
      1. `User.to_dict()` exposed `password_hash` and `ics_token`
         (latent, nothing called it yet, but it was a ticking time bomb)
      2. **CSRF protection completely absent from the application** (not
         just disabled in tests) - `Flask-WTF` is a dependency,
         `WTF_CSRF_ENABLED` exists in the config, but `CSRFProtect` was
         instantiated nowhere and no template had a `csrf_token` field.
         Fixed: see Log for the full detail.
- [x] Accessibility tests - already partially covered by
      `test_dark_theme.py`/`test_theme_fixes.py` (Phase 3), no full WCAG
      2.1 AA (confirmed out of scope in Phase 3)
- [x] ~~E2E tests with Selenium or Playwright~~ -> flows via the Flask
      test client (validated decision, no real headless browser)

---

## 📝 Log

*(updated at every step)*

### 2026-07-11 — 4.1 Restructuring done

Mechanical move (`git mv`, history preserved) of the 26 existing test
files into `tests/unit/` (12, no HTTP client) and `tests/integration/`
(14, go through the Flask test client). `tests/e2e/` and
`tests/fixtures/` created.

`conftest.py` reduced to `test_app`/`client`; model fixtures
(`test_group`, `test_user`, `admin_user`, `test_shift`, `test_leave`,
`test_oncall`, etc.) extracted into `tests/fixtures/*.py`, wired in via
`pytest_plugins` to stay visible everywhere with no explicit import.

**Real bug caught by the tests before commit**: I first removed the
`app = test_app` alias at the bottom of `conftest.py`, mistaking it for
dead code (grep showed no test requesting a fixture named `app`). In
reality, `pytest-flask` relies on it through its autouse
`_configure_application` fixture, which literally looks for a fixture
called `app` - without it, 2 tests crashed at setup
(`fixture 'app' not found`). Alias restored with a comment explaining
why it exists, to avoid falling into the same trap later.

511 tests still passing (197 unit + 314 integration after the
restructuring).

### 2026-07-11 — Service/repository unit tests + E2E tests + performance

`tests/unit/test_repositories.py` (UserRepository, GroupRepository,
ShiftTypeRepository, ShiftRepository, LeaveRepository, OnCallRepository)
and `tests/unit/test_services.py` (UserService, GroupService,
ShiftTypeService, ShiftService, OnCallService, LeaveService,
ExportService): 107 tests calling the business/data layer directly.
Coverage: repositories 100%, services 90%+ (except
`automation_admin_service` and `oncall_service`, not covered here -
`automation_admin_service` delegates to `AdvancedShiftAutomation`, which
already has its own dedicated suite).

Bug caught before commit: `test_add_shifts_for_range_conflict_rolls_back`
used the `test_shift` fixture, whose date is `date.today()`, which falls
on a **Saturday** in this environment - `add_shifts_for_range` skips
weekends before checking for conflicts, so the test wasn't testing
anything at all (`conflict_date` always stayed `None`). Fixed by
explicitly creating a shift on a business day.

`tests/e2e/test_user_flows.py`: 4 multi-request flows (no real browser,
validated decision) - admin creates a group -> user -> assigns shifts ->
the user logs in and sees their schedule; user requests leave for
themselves (accepted) then for someone else (rejected, verified in the
database); login with wrong password then correct password, session
invalidated after logout; authenticated ICS export vs. rejected without
authentication.

`tests/integration/test_performance.py`: broad thresholds on `/schedule`
and `/dashboard` (catches a gross regression, not a micro-benchmark) +
SQL query counting to verify that `joinedload()` in
`ShiftRepository.list_paginated` avoids the N+1. **Verified the test
actually detects a regression**: temporarily removing `joinedload()`
from the code (13 queries instead of 3 for 10 shifts) makes both tests
fail immediately; put back afterward.

Bug caught before commit: `_seed_shifts` used fixed emails
(`perf0@test.com`...) - called twice in the same test with different
sizes, the second insert violated the unique constraint on email. Fixed
with an `offset` parameter.

624 then 628 tests passing as these were added.

### 2026-07-11 — Security tests: two real fixes, not just tests

While writing `tests/integration/test_security.py`, two real issues
surfaced - not test artifacts, gaps actually present in production:

**1. `User.to_dict()` exposed `password_hash` and `ics_token`.**
`BaseModel.to_dict()` serializes every column indiscriminately; `User`
had no override. Nothing calls `user.to_dict()` in the current code
(verified by grep), so it was latent - but the method exists, and any
future JSON endpoint using it would have leaked the password hash and
the ICS export token (a bearer token, equivalent to a password for the
anonymous flow). Fixed with a `User.to_dict()` override that strips
these two fields. Tested (`TestSensitiveDataNotSerialized`).

**2. CSRF protection was completely absent from the application, not
just disabled in tests.** `Flask-WTF` is a dependency,
`WTF_CSRF_ENABLED` exists in `app/config/testing.py`, but `CSRFProtect`
was **instantiated nowhere** in `app/__init__.py`, and **none of the 19
templates with a POST form** had a `csrf_token` field. The config flag
was purely decorative: in both production and dev, every POST route
(login, adding/removing shifts, admin user/group management, etc.) was
exploitable via CSRF.

User decision validated: fix it fully in this same session (not just
document it), given the scale of the production impact:
- `csrf = CSRFProtect()` + `csrf.init_app(app)` in `app/__init__.py`
  (same pattern as `db`/`login_manager`/`limiter`)
- `<meta name="csrf-token" content="{{ csrf_token() }}">` added to
  `base.html` so JS can read it
- Hidden field `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">`
  added right after the `<form method="POST">` tag in the 19 affected
  templates (22 forms total - `schedule.html` and `oncall.html` have
  several each)
- The 5 `fetch()` calls using a write method (PATCH/POST/DELETE) in
  `index.html` (FullCalendar drag & drop, shift creation/deletion via
  modal) now send the `X-CSRFToken` header read from the meta tag

**Verified under real conditions**, not just via the tests: Flask server
with `app.config.Config` (prod-style config, not TestingConfig) and
`WTF_CSRF_ENABLED` at its default value (True, since it isn't overridden
outside TestingConfig):
- POST `/login` with no token -> 400 (rejected)
- GET `/login` then POST with the token extracted from the HTML -> 302
  (logged in), valid session cookie, `/dashboard` reachable afterward
- POST `/api/shifts` with a missing `X-CSRFToken` header -> 400; with the
  correct header (the one rendered in the meta tag) -> 200, shift
  actually created

`tests/integration/test_security.py` (13 tests): builds its own app
instance with both Talisman AND CSRF re-enabled (`TestingConfig`
disables both to simplify the other suites) to specifically test these
two protections, plus Talisman's security headers, password storage
(hashed, never in clear text), and admin/non-admin access control (admin
dashboard, user list, adding a shift, deleting a shift - all 302/403 for
a non-admin or an anonymous user).

641 tests passing.

### 2026-07-11 — End-of-phase summary

Coverage measured right after the services/repositories/e2e/performance/
security tests: **57%** raw, virtually unchanged from the baseline (56%)
despite 130 added tests - the weight of confirmed dead code
(`monitoring/` 344 lines, `pagination/` 248, `env_helpers.py` 47,
`cache_helpers.py` 40, plus `lazy_loading.py` 785 lines and 13 dead
decorators in `optimizations/__init__.py` found while digging, all at
0%, never called) was dragging down the overall average.

**Following the "clean up the dead code" request**: the 5 confirmed
modules removed (git rm, every reference verified at zero elsewhere in
`app/` before removal) + `optimizations/__init__.py` trimmed from 14
decorators down to 1 (`eager_load`, the only one actually used).
`.coveragerc` cleaned up along the way (its `omit` rules pointed at old
flat-file paths gone since the Phase 2 reorganization, matching nothing
anymore). **Result: overall coverage 57% -> 71%**, without writing a
single additional test - just by removing ~1450 never-executed lines
from the denominator. `prometheus_metrics.py` (86 lines, 0%) kept as-is:
not dead, just conditional (`PROMETHEUS_ENABLED`) and not exercised by
the current test suite.

The remaining gap to 80% comes from the routes (`auth.py` 61%,
`leave_routes.py` 57%, `oncall_routes.py` 63%, `shift_routes.py` 64%,
`dashboard_routes.py` 57%) and from `automation_admin_service.py`/
`oncall_service.py`, untouched by this phase - a logical follow-up for a
future coverage pass, out of scope for this Phase 4 as defined.

Phase summary:
- Full `unit/`/`integration/`/`e2e/`/`fixtures/` restructuring (26 files
  moved, history preserved)
- 130 tests added (107 services/repositories + 6 E2E + 4 performance +
  13 security): repositories 100%, services 90%+
- 3 real bugs caught and fixed before commit (the `app` alias mistaken
  for dead code, a weekend fixture skewing a test, an email collision in
  perf seeding)
- 2 real vulnerabilities found and fixed (not just documented): CSRF
  completely absent from the application (19 templates + 5 fetch() calls
  fixed, verified under real conditions), potential
  `password_hash`/`ics_token` leak via `User.to_dict()`
- ~1450 lines of confirmed dead code removed (5 modules + 13 unused
  decorators), coverage 57% -> 71% with no new test
- E2E scoped in agreement with the user (Flask test client, no headless
  browser - infra unavailable in this environment)

641 tests passing, 0 failures.

### 2026-07-12 — 80%+ target reached (81%)

Following the explicit request to get back above 80%, executed the plan
in 3 steps (Step 0/1/2 discussed with the user before execution).

**Step 0 — additional dead code** (zero caller verified in
`app/models`, `app/auth`, `app/routes`, `app/services` + `tests/` before
removal):
- `app/utils/security/encryption.py` (26 lines) and `token_manager.py`
  (16 lines). The auto classifier blocked the first attempt to remove
  `token_manager.py`, since `CLAUDE.md` documents it as "ICS export
  tokens" - a deeper check showed `User.generate_ics_token()` uses
  `secrets.token_urlsafe()` directly (`app/models/user.py:137`), zero
  import of `token_manager` anywhere: `CLAUDE.md` was stale on this
  specific point. Explicitly confirmed with the user before retrying the
  removal.
- `app/utils/automation/shift_automation.py` (32 lines, the legacy
  module predating `AdvancedShiftAutomation`) - `generate_shifts`,
  `generate_oncall_rotations`, `check_shift_conflicts`,
  `check_oncall_conflicts` with no real caller.
- `security/__init__.py` and `automation/__init__.py` trimmed
  accordingly (otherwise an `ImportError` at startup).

**Step 1 — two real bugs found while writing tests, not test
artifacts**:
1. `prometheus_metrics.py`: `after_request` used `request.method`/
   `request.path` without ever importing `request` at module level -
   `NameError` on **every request** as soon as `PROMETHEUS_ENABLED=True`.
   Since this flag had never been tested, nobody had noticed. Fixed
   (import added).
2. `health.py`: `check_database()` did
   `db.session.execute('SELECT 1')` - a raw SQL string, rejected by
   SQLAlchemy 2.x (`ObjectNotExecutableError`), silently swallowed by
   the broad `except Exception` wrapping it. Result: `/ready` responded
   `database: False` / 503 **permanently**, with no flag to disable it -
   a real production bug, active since day one, not hidden behind an
   optional feature. If this endpoint serves as a Kubernetes readiness
   probe, the pod would never have gone "ready". Fixed with
   `text('SELECT 1')`.

New tests: `test_cache_manager.py` (branches of `init_cache`,
`SimpleDictCache`), `test_health.py`, `test_prometheus_metrics.py` (a
dedicated app with `PROMETHEUS_ENABLED=True`, same pattern as
`secure_app` for CSRF in the previous Phase 4 step), an addition to
`test_helpers.py` (`get_bool`/`get_int`/`format_*`/`parse_*`/
`get_days_in_month` + the two overlap helpers never called by the
existing tests).

**Step 2 — route edge cases** (error/validation/exception branches
uncovered by the existing suites, `unittest.mock.patch` mocks to
simulate service failures):
`test_shift_routes_coverage.py` (29 tests), `test_leave_routes_coverage.py`
(17), `test_oncall_routes_coverage.py` (19), `test_auth_routes_coverage.py`
(10 - non-OIDC branches only; OIDC would require mocking the Authlib
client, a separate effort, out of scope).

**Result: 768 tests passing, coverage 71% -> 81%.** Plan target reached
without touching `oidc_auth.py`/`user_manager.py` (236+43 uncovered
lines, left aside as planned - would require mocking a full OIDC flow).

---

*Last updated: 2026-07-12*
