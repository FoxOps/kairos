# 📋 Report - E2E Playwright Tests (real browser)

**Branch**: `feature/e2e-playwright`
**PR**: [#104](https://github.com/FoxOps/kairos/pull/104) (draft)
**Start date**: 2026-07-13
**Status**: 🟢 Implementation complete, verified for real
**Base**: `main` (post UI/UX overhaul, PR #103, commit `b881b3d`)

---

## 🎯 Decision: complement, not replace

The existing `tests/e2e/test_user_flows.py` uses the Flask test client
(no real browser) — its own docstring explicitly states:
"No real headless browser (Selenium/Playwright not available
in this dev environment — no chromedriver/geckodriver, no sudo)".
**This claim is false**: `playwright install chromium` (without
`--with-deps`, which does need sudo) downloads and installs a
standalone Chromium without root privileges, verified in practice in
the previous session (UI/UX overhaul — allowed finding 3 real CSP bugs
otherwise invisible).

**Decision: keep the existing Flask E2E tests AND add a
new Playwright layer**, not a replacement:

- The Flask E2E tests (test client, no browser) remain
  useful: fast (no browser startup), zero heavy dependency,
  good for checking permissions/redirects/data
  (e.g. `TestUserRequestsLeave.test_user_cannot_request_leave_for_someone_else`).
- The Playwright tests cover a category of bug **structurally
  invisible** to the Flask test client, since it never executes JS nor
  applies CSS/CSP: this is exactly the category of the 3 bugs
  found manually during the UI/UX overhaul (inline script blocked
  by CSP on 2 pages, FullCalendar icon font blocked by a missing
  `font-src`). The main goal of this PR is to turn
  this one-off manual check into a permanent regression guardrail.

## 🔍 Design

- **Optional dependency**, not in the main `requirements.txt`:
  `requirements-e2e.txt` (playwright only). The app runs perfectly fine without it.
- Tests marked and **skip cleanly** if playwright/chromium is absent
  (`pytest.importorskip`) — the existing `make test`/CI never breaks,
  no obligation to install a browser to contribute to the project.
- Real Flask server launched in a thread (not the test client) with
  Talisman **actually active** (CSP genuinely applied, not
  `TestingConfig`, which disables it) — otherwise the CSP bugs would
  stay invisible even with a real browser.
- Priority given to high-value / low-flakiness tests: zero console
  errors on key pages (generalizes the manual audit), mobile burger
  navbar (pure JS, untestable server-side), dark theme (localStorage,
  untestable server-side), ICS clipboard copy (verifies the
  UI/UX overhaul fix). No FullCalendar drag & drop tests (fragile,
  low added value vs. effort).

## ⚠️ Limitation

These tests require `pip install -r requirements-e2e.txt &&
playwright install chromium` locally to run — otherwise they are
skipped (visible in the pytest summary as `skipped`, not hidden).

---

## 📝 Log

### Implementation (commits `d01e9e4`, `6991b7d`, `0650b21`)

- `requirements-e2e.txt`: `playwright==1.61.0` + `pytest-playwright==0.8.0`
  (auto-registers the `page`/`browser`/`context` fixtures).
- `tests/e2e/conftest.py`: `live_server_url` fixture (module-scope) —
  launches a real `app.run()` in a daemon thread on a free port,
  Talisman genuinely active (CSP applied), CSRF disabled (out of
  scope here, already covered by `test_security.py`), admin seeded with
  known credentials (`e2e-admin@kairos.local` /
  `e2e-password-123` — not a random password like
  `run.py`/`DEFAULT_ADMIN_PASSWORD`, which had tripped up the
  previous manual verification: password generated on the fly, never
  logged, login impossible without setting it explicitly).
- `tests/e2e/test_browser_flows.py`: real login, mobile burger,
  dark theme, **zero console errors on 8 pages** (the main
  guardrail), ICS copy button.
- `.gitlab-ci/.gitlab-ci.yml`: `run_e2e_browser` job (official
  `mcr.microsoft.com/playwright/python` image, `allow_failure: true`
  while it proves its stability in real CI, doesn't affect
  `run_tests`).
- `CLAUDE.md` updated (commands + Testing conventions section) —
  fixed a wrong claim along the way: `test_user_flows.py`'s docstring
  incorrectly stated that Playwright wasn't installable without sudo
  in this environment (false, `playwright install chromium` without
  `--with-deps` doesn't need it).

### Real verifications performed (not just written and assumed correct)

1. **14/14 tests pass** under real conditions (Chromium installed
   in `.venv`, real server, CSP active).
2. **The guardrail genuinely catches regressions**: `font-src`
   temporarily removed from `CSP_POLICY`, `test_page_has_no_console_errors[chromium-/]`
   fails with the exact console error message (CSP violation),
   restored, re-verified green. Without this step, nothing
   would guarantee the test did anything other than pass
   unconditionally.
3. **Clean skip confirmed**: suite installed in a throwaway venv
   without `requirements-e2e.txt` — the 6 existing Flask E2E tests
   pass normally, `test_browser_flows.py` becomes exactly
   1 `skipped` entry (not 14 failures, no collection error).
4. Full project suite (795 tests including the 14 new ones) passes
   with no regression.
5. `--junitxml` successfully generated locally (the flag used in the
   new CI job actually works, not just copied from another
   job by analogy).

### OIDC tests (commits `a9788f7`, `ae7ddbc`, `8e07a41`)

Extension of the initial scope (generic Playwright): added test
coverage for OIDC/SSO authentication
(`config_oidc.py`, `app/auth/oidc_auth.py`, `app/auth/user_manager.py`),
previously at zero tests despite ~450 lines of logic. Three levels:

1. **Unit** (68 tests, `tests/unit/test_oidc_config.py`,
   `test_oidc_auth.py`, `test_user_manager_oidc_sync.py`): each
   method in isolation, network calls (`requests.get/post`) mocked, unsigned
   test JWT (the code never verifies a signature).
2. **Integration** (13 tests, `tests/integration/test_oidc_routes.py`):
   Flask route wiring (`/login`, `/oidc/login`, `/oidc/callback`,
   `/logout`), `oidc_auth` mocked at the routes module boundary.
   **Found a real, blocking bug**: infinite redirect
   loop (`/login` ↔ `/oidc/login`) on any OIDC failure when SSO
   is enforced (`OIDC_DISABLE_BASIC_AUTH=true`) - the app became
   completely inaccessible as soon as the provider had an issue.
   Fixed (`oidc_error=1` parameter that breaks the automatic bounce-back).
3. **Real-browser E2E** (5 tests, `tests/e2e/test_oidc_browser_flow.py`):
   real end-to-end HTTP flow against a minimal but genuine fake OIDC
   provider (`tests/e2e/oidc_mock_provider.py`, no Python
   mocks, no Docker) — browser redirect, real login page with a click,
   real server-to-server exchanges, session genuinely established and invalidated.

Each level verified under real conditions before commit (see
commit messages for the precise detail of each verification).

---

*Last updated: 2026-07-13 — generic Playwright implementation
+ full OIDC coverage (unit/integration/browser E2E), one
real bug found and fixed (infinite SSO redirect loop). 881
tests pass in total. PR #104 in draft, ready for review.*
