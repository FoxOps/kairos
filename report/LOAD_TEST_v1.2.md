# Load test v1.2

> Follow-up to `LOAD_TEST_v1.1.md`, run as part of a full validation pass
> on `1.0.0-RC2` (PR #159-165: on-call algorithm rework, ANSSI password
> policy, i18n audit, 405 fix - see `ROADMAP.md` and
> `report/TESTING_SUMMARY.md`). Re-runs the same methodology to confirm
> no regression; no new endpoint added by this batch that changes the
> read-path surface, so the same endpoint set as v1.1 was kept, plus
> `/admin/automation` (new merged automation dashboard, replacing the two
> separate pages `/admin/automation/status` and
> `/admin/automation/refresh-shifts` that v1.0/v1.1 never covered
> individually).

## Methodology

Same as v1.0/v1.1: `wrk`/`hey` (the tools `scripts/load_test.sh` wraps)
were not installable in this sandbox (no interactive `sudo`), so a
standalone Python script using only the standard library
(`concurrent.futures` + `urllib`, no dependency added to the project) was
used to produce real numbers. `scripts/load_test.sh` remains the shipped,
recommended tool for a real deployment. Authenticated endpoints log in
through a real `/login` POST (CSRF token scraped from the rendered form)
per worker thread, then reuse that session's cookie jar for the duration
of the run - not a bypass of authentication.

### Configuration tested

- Server: `gunicorn --workers 1 --threads 4 --timeout 120` - exactly the
  command from `docker/entrypoint.sh` in production mode.
- Database: SQLite, freshly seeded - 31 users, 128 shifts (weekdays only,
  60 days past / 120 days future), 12 on-call rotations. Same order of
  magnitude as v1.1's dataset.
- Machine: same development workstation as v1.0/v1.1, shared with the
  rest of this session - absolute numbers are indicative only (see
  "Limitations"), not directly comparable across reports; the shape of
  the results (zero errors, saturation pattern at 50 connections) is
  what matters.
- `TALISMAN_FORCE_HTTPS=false`, `SESSION_COOKIE_SECURE=false`,
  `RATE_LIMIT_ENABLED=false` - the last one specifically to let a 10-
  second burst run without tripping the app's own default rate limit
  (`200 per day, 50 per hour`), which would otherwise throttle this
  synthetic test long before any real capacity limit is reached; a real
  deployment should leave rate limiting on.

## Results

10 seconds per endpoint, sequential requests per thread (no pause -
continuous load).

| Endpoint | Concurrency | Total req. | Errors | req/s | p50 | p95 | p99 | max |
|---|---|---|---|---|---|---|---|---|
| `/health` | 10 | 8305 | 0 | 830.5 | 11.5 ms | 18.0 ms | 22.5 ms | 33.1 ms |
| `/login` (GET) | 10 | 1556 | 0 | 155.6 | 63.3 ms | 81.2 ms | 88.7 ms | 116.9 ms |
| `/dashboard` (auth) | 10 | 593 | 0 | 59.3 | 145.2 ms | 177.3 ms | 200.3 ms | 242.7 ms |
| `/schedule` (auth) | 10 | 340 | 0 | 34.0 | 252.0 ms | 330.1 ms | 354.8 ms | 382.9 ms |
| `/schedule` (auth) | 50 | 149 | 0 | 14.9 | 1264.0 ms | 1331.1 ms | 1364.7 ms | 1371.6 ms |
| `/api/shifts` (auth, calendar JSON) | 10 | 502 | 0 | 50.2 | 168.9 ms | 225.1 ms | 246.5 ms | 293.9 ms |
| `/admin/audit-log` (auth, admin) | 10 | 595 | 0 | 59.5 | 141.2 ms | 180.0 ms | 198.3 ms | 222.8 ms |
| `/oncall` (auth) | 10 | 529 | 0 | 52.9 | 158.2 ms | 197.8 ms | 216.8 ms | 241.4 ms |
| `/admin/automation` (auth, admin) | 10 | 450 | 0 | 45.0 | 190.8 ms | 234.4 ms | 254.0 ms | 279.3 ms |

**Zero errors across the entire test suite** (no timed-out requests, no
5xx) - confirmed by both the client-side results above and a grep of the
gunicorn server log for the run (no traceback, no exception logged).

## Analysis

- Same saturation pattern as v1.0/v1.1: `/schedule` at 50 concurrent
  connections vs. 10 shows a large latency increase for lower absolute
  throughput (34.0 → 14.9 req/s here) - the expected effect of
  `--workers 1 --threads 4` queuing the remaining connections under a
  single-worker gunicorn process, not an application-level regression.
  Confirms v1.0/v1.1's conclusion still holds after this batch's
  changes.
- **`/admin/automation`** - new to this report, replacing the two
  separate pages this batch merged into one (see
  `Docs/guides/ADMIN_GUIDE.md`). Lands in the same 150-250 ms p50 range
  as the other authenticated admin pages (`/admin/audit-log`), no sign
  that the merge (a single template now rendering the gap-detection
  banner plus the dashboard stats) introduced extra per-request cost.
- On-call generation and the ANSSI password policy - the two heaviest
  functional changes in this batch - are not directly exercised by this
  read-path load test: the backtracking search only runs on an explicit
  admin-triggered generate/refresh action (not a page users hit
  repeatedly under load), and password validation runs once per
  change-password submission, not per request. Both are covered by
  their own targeted tests (`tests/unit/test_automation.py`,
  `tests/integration/test_password_policy.py`) rather than a load test,
  which is the right tool for neither.
- Numbers are within noise of v1.1's run on the same machine (e.g.
  `/health` p50 11.5 ms here vs. 11.5 ms in v1.1, `/dashboard` p50 145.2
  ms here vs. 145.2 ms in v1.1) - expected, since this batch touched
  none of the hot paths (N+1 fixes, timezone caching) that v1.1 was
  specifically re-validating.

## Limitations of this measurement

- Same as v1.0/v1.1: shared development machine, not an isolated bench -
  absolute numbers aren't comparable across reports or to a future
  production environment, only the relative shape (saturation curve,
  zero-error baseline) is informative.
- SQLite, single worker, read-only routes - identical scope limitations
  to v1.0/v1.1, not re-litigated here.
- Rate limiting was disabled for this run (see "Configuration tested") -
  a real deployment under the same synthetic burst would see 429s once
  the default quota is exhausted; that is expected, intended behavior,
  not a finding.

## Verdict

No regression from v1.1, zero errors, and the new merged automation page
lands in the same latency range as the rest of the authenticated
surface. Nothing in this batch (on-call algorithm rework, password
policy, i18n audit, 405 fix) blocks production readiness.
