# Load test v1.0

## Methodology

**Recommended tool for real-world use**: `scripts/load_test.sh`, a
wrapper around `wrk` (preferred) or `hey` — two external binaries, zero
additional Python dependency (consistent with this project's philosophy:
few dependencies, see CLAUDE.md and the choice already made for
`hey`/`wrk` over Locust). Neither was installable in this session's
sandbox environment (no interactive `sudo` available for
`pacman -S wrk`) — the results below were therefore obtained with a
standalone Python script using only the standard library
(`concurrent.futures` + `urllib`, no dependency added to the
project), to produce real numbers rather than leaving this section
empty. **`scripts/load_test.sh` remains the shipped and
recommended script** for any future measurement — faster and more
complete than the ad hoc script used here (HTTP/2 support, more
accurate latencies, histograms).

### Configuration tested

- Server: `gunicorn --workers 1 --threads 4 --timeout 120` — exactly
  the command from `docker/entrypoint.sh` in production mode (see
  CLAUDE.md "Database backups" for the context behind this choice: a
  single worker + 4 threads, no multi-process).
- Database: SQLite, ~31 users, ~390 shifts (60 days in the past,
  120 in the future), 12 on-call rotations — modest but realistic volume
  for a team using this app (see CLAUDE.md: a team scheduling tool,
  not a large-scale multi-tenant SaaS).
- Machine: development workstation shared with the rest of this session
  (results are indicative only, not a dedicated isolated test bench — see
  "Limitations" below).

### A real bug found while preparing this test

While simply trying to log in via script to test authenticated pages,
the login was failing silently (`/dashboard` always redirected to
`/login`, as if no session was ever persisted) — even though
`TALISMAN_FORCE_HTTPS=false` and `SESSION_COOKIE_SECURE` at its default
value (`false`), the documented default configuration for a deployment
without a TLS proxy. Investigation: Flask-Talisman has its **own**
independent default for `session_cookie_secure` (`True`), unrelated to
`force_https`, and its `before_request` hook rewrites
`app.config["SESSION_COOKIE_SECURE"] = True` on **every request** as
soon as `app.debug` is `False` — silently overriding the app's
`SESSION_COOKIE_SECURE` setting. Consequence: in exactly the documented
default configuration (`TALISMAN_FORCE_HTTPS=false`, no TLS proxy), the
session cookie was marked `Secure`, therefore never sent back by the
browser over plain HTTP — **login broken in practice** for any
deployment following the default configuration without HTTPS
(`python run.py` → `http://localhost:5000`, or Docker without an
already-configured TLS proxy).

This bug had remained invisible until now for a precise reason, itself
a second bug: `run.py` forced `debug=True` on the Flask development
server **regardless of** `FLASK_DEBUG`/`Config.DEBUG` — and since
Talisman's hook only rewrites the cookie `if not app.debug`, this first
bug accidentally masked the second one locally. Fixing only the first
one (`debug=True` hardcoded, a real security risk: the interactive
Werkzeug debugger always active, potential RCE on any unhandled
exception) without fixing the second would have **broken local login**
for anyone without explicit `FLASK_DEBUG=true`. Both were fixed
together (`run.py`: `debug=app.config.get("DEBUG", False)`;
`app/__init__.py`: `Talisman(..., session_cookie_secure=app.config.get("SESSION_COOKIE_SECURE", False))`),
with a manual end-to-end test (real login, cookie inspected,
`/dashboard` accessible after login) confirming the fix before
running the load test itself.

## Results

10 seconds per endpoint unless stated otherwise, sequential requests
per thread (no pause between requests — continuous load).

| Endpoint | Concurrency | Total req. | Errors | req/s | p50 | p95 | p99 | max |
|---|---|---|---|---|---|---|---|---|
| `/health` | 10 | 2324 | 0 | 232.4 | 14.6 ms | 44.0 ms | 71.7 ms | 166.2 ms |
| `/login` (GET) | 10 | 1338 | 0 | 133.8 | 54.5 ms | 97.9 ms | 140.9 ms | 199.2 ms |
| `/dashboard` (auth) | 10 | 1059 | 0 | 105.9 | 75.5 ms | 113.6 ms | 154.7 ms | 207.3 ms |
| `/schedule` (auth) | 10 | 1108 | 0 | 110.8 | 73.7 ms | 115.2 ms | 163.9 ms | 219.8 ms |
| `/schedule` (auth) | 50 | 1176 | 0 | 117.6 | 408.5 ms | 491.0 ms | 683.3 ms | 760.6 ms |

**Zero errors across the entire test suite** (no timed-out requests,
no 5xx).

## Analysis

- `/health` (no DB access, just static JSON) serves as a baseline:
  ~230 req/s, latency dominated by the HTTP/WSGI overhead itself on this
  machine, not by the app.
- `/login` (GET, template rendering + generating a CSRF token per
  request) adds about 40 ms of median latency compared to
  `/health` — consistent with the cost of Jinja rendering + Flask-WTF's
  cryptographic CSRF token generation, not a red flag.
- `/dashboard` and `/schedule` (authenticated, with real DB access —
  aggregates, `joinedload` on the shifts/on-calls of the displayed
  period) add another ~20 ms compared to `/login` — consistent with
  a handful of SQL queries per page on SQLite, not an unexpected
  degradation.
- **The notable point**: going from 10 to 50 concurrent connections on
  `/schedule` pushes median latency from 74 ms to 409 ms (×5.5)
  for almost identical throughput (110.8 → 117.6 req/s, +6%) — a clear
  sign of saturation, not an application issue: with `--workers 1
  --threads 4`, only 4 requests actually run in parallel at any given
  moment, the other 46 simultaneous connections wait in queue.
  This is the **expected** behavior of the gunicorn configuration
  documented for this project (a single, lightweight worker, designed
  for a team using the app internally — see CLAUDE.md) and not a flaw
  of the application itself: the same 50 connections against several
  gunicorn workers (`--workers 4` for example) would spread the load
  instead of queuing it.

## Limitations of this measurement

- Shared development machine, not an isolated test bench — the
  absolute numbers (ms, req/s) are not comparable to a future
  production environment; the **proportions** (×5.5 factor between
  10 and 50 connections, gap between `/health` and authenticated pages)
  remain informative.
- SQLite, not PostgreSQL/MySQL — the recommended production database
  (see CLAUDE.md "Configuration: two parallel systems") has a
  different concurrency model (row-level locking, not file-level)
  that would likely behave better under heavy write concurrency.
  This test only covers read routes.
- No concurrent write scenario tested (shift creation/modification) —
  out of scope for this pass, a candidate for a more thorough future
  load test if the need arises after a first real deployment.
- Only a single gunicorn worker tested (`--workers 1`, the documented
  default configuration) — the concurrency ceiling observed (×5.5
  factor at 50 connections) is directly an artifact of this choice,
  not a limitation of the application; moving to several workers
  remains the standard answer if a real deployment sees higher
  concurrent load than what was tested here.

## Verdict

No regression, no errors, latencies consistent with the work actually
performed by each endpoint. The only notable signal
(saturation at 50 concurrent connections with a single worker) is
expected behavior of the default configuration, not a code issue —
documented here so the team knows which lever to pull
(`--workers`) if a real deployment exceeds the load tested here. Nothing in
this test blocks v1.0 stabilization.
