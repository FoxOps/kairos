# Load test v1.1

> Follow-up to `LOAD_TEST_v1.0.md`, conducted as part of the
> production-readiness audit (batch 8, see `ROADMAP.md`). Re-runs the same
> methodology against the current codebase (post batches 1-7: N+1 fixes on
> the calendar/audit-log, OIDC security fixes, dead code removal, i18n
> completion) to confirm no regression, plus two new endpoints touched by
> those fixes (`/admin/audit-log`, `/api/shifts`).

## Methodology

Same as v1.0: `wrk`/`hey` (the tools `scripts/load_test.sh` wraps) were
not installable in this sandbox (no interactive `sudo`), so a standalone
Python script using only the standard library
(`concurrent.futures` + `urllib`, no dependency added to the project) was
used to produce real numbers. `scripts/load_test.sh` remains the shipped,
recommended tool for a real deployment.

### Configuration tested

- Server: `gunicorn --workers 1 --threads 4 --timeout 120` — exactly the
  command from `docker/entrypoint.sh` in production mode.
- Database: SQLite, freshly seeded — 31 users, 128 shifts (weekdays only,
  60 days past / 120 days future), 12 on-call rotations. Slightly smaller
  than v1.0's 390-shift dataset (weekends excluded here) but comparable
  order of magnitude for this app's target scale (a team scheduling tool,
  not a large multi-tenant SaaS).
- Machine: same development workstation as v1.0, shared with the rest of
  this session — absolute numbers are indicative only (see "Limitations"),
  not directly comparable across the two reports; the shape of the results
  (zero errors, saturation pattern at 50 connections) is what matters.
- `TALISMAN_FORCE_HTTPS=false`, `SESSION_COOKIE_SECURE=false` — the
  documented no-TLS-proxy default, the exact configuration a v1.0 bug
  (already fixed) used to break login for entirely.

## Results

10 seconds per endpoint, sequential requests per thread (no pause —
continuous load).

| Endpoint | Concurrency | Total req. | Errors | req/s | p50 | p95 | p99 | max |
|---|---|---|---|---|---|---|---|---|
| `/health` | 10 | 4939 | 0 | 493.9 | 19.0 ms | 33.7 ms | 44.5 ms | 106.0 ms |
| `/login` (GET) | 10 | 1216 | 0 | 121.6 | 76.3 ms | 130.3 ms | 153.3 ms | 174.0 ms |
| `/dashboard` (auth) | 10 | 660 | 0 | 66.0 | 151.4 ms | 186.8 ms | 198.8 ms | 214.9 ms |
| `/schedule` (auth) | 10 | 401 | 0 | 40.1 | 249.8 ms | 327.1 ms | 372.2 ms | 419.7 ms |
| `/schedule` (auth) | 50 | 437 | 0 | 43.7 | 1273.4 ms | 1409.5 ms | 1474.2 ms | 1518.6 ms |
| `/api/shifts` (auth, calendar JSON) | 10 | 598 | 0 | 59.8 | 168.5 ms | 212.9 ms | 245.2 ms | 276.1 ms |
| `/admin/audit-log` (auth, admin) | 10 | 745 | 0 | 74.5 | 133.1 ms | 173.1 ms | 210.6 ms | 247.5 ms |
| `/oncall` (auth) | 10 | 586 | 0 | 58.6 | 165.2 ms | 243.7 ms | 276.0 ms | 309.6 ms |

**Zero errors across the entire test suite** (no timed-out requests, no
5xx) — confirmed by both the client-side results above and a grep of the
gunicorn server log for the run (no traceback, no exception logged).

## Analysis

- Same saturation pattern as v1.0: `/schedule` at 50 concurrent
  connections vs. 10 shows a ~5× latency increase for roughly flat
  throughput (40.1 → 43.7 req/s, +9%) — the expected effect of
  `--workers 1 --threads 4` queuing the remaining connections, not an
  application-level issue. Confirms v1.0's conclusion still holds after
  every change made in this session's batches.
- **`/admin/audit-log`** (133 ms p50) — specifically exercised here because
  batch 1 fixed a real N+1 on this route (`AuditLogRepository.list_paginated()`
  now bulk-preloads `AuditLog.actor` instead of one `db.session.get(User,
  ...)` per row). Latency stays flat and comparable to the other
  authenticated pages under load — no sign of the fixed N+1 resurfacing.
- **`/api/shifts`** (168 ms p50) — the calendar JSON endpoint whose
  timezone resolution (`SettingsService.get_default_timezone()`) batch 1
  cached on `flask.g` (previously one `Setting.get()` per shift/on-call
  rendered). Comparable latency to `/dashboard`/`/oncall`, consistent
  with a fixed per-request cost rather than one growing with the number
  of events on the calendar.
- `/dashboard` and `/oncall` land in the same 150-250 ms p50 range as
  v1.0's authenticated pages, scaled by this run's higher baseline
  overhead (`/health` itself is ~5ms slower here at p50 than in v1.0,
  most likely session/machine load — see "Limitations").

## Limitations of this measurement

- Same as v1.0: shared development machine, not an isolated bench —
  absolute numbers aren't comparable across reports or to a future
  production environment, only the relative shape (saturation curve,
  zero-error baseline) is informative.
- SQLite, single worker, read-only routes — identical scope limitations
  to v1.0, not re-litigated here.
- Smaller on-disk dataset than v1.0 (128 vs. 390 shifts, weekdays only) —
  chosen for setup speed in this pass; large enough to exercise the
  `joinedload`/bulk-preload paths fixed in batch 1, not large enough to
  stress-test them at a materially bigger scale than v1.0 already did.

## Verdict

No regression from v1.0, zero errors, and the two routes specifically
touched by this session's N+1 fixes (`/admin/audit-log`, `/api/shifts`)
show flat, comparable latency to the rest of the authenticated surface —
consistent with those fixes actually holding under concurrent load, not
just in the unit-level query-count tests already in the suite
(`tests/integration/test_performance.py`). Nothing in this pass blocks
production readiness.
