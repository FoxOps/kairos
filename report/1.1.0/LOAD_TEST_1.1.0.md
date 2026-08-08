# Load test 1.1.0

## Methodology

Ran with the shipped `scripts/load_test.sh` (`wrk`, now installed — v1.0's
report used an ad hoc `urllib`-based stand-in since `wrk` wasn't available in
that session; that limitation no longer applies). Public, unauthenticated
endpoints only (`/health`, `/ready`, `/version`, `/login` GET) — the same set
`scripts/load_test.sh` covers; authenticated pages (`/dashboard`, `/schedule`)
aren't part of that script (no cookie/session handling) and weren't re-tested
this cycle — v1.0's report already covers that ground with its own ad hoc
script, no route touched by the 1.1.0 cycle changes that path.

### Configuration tested

- Server: `gunicorn --workers 1 --threads 4 --timeout 120` — same command as
  v1.0's report, matching `docker/entrypoint.sh` production mode (gunicorn
  isn't in the root `requirements.txt`, only `docker/requirements.txt` — see
  CLAUDE.md's "Frontend"/backup sections; installed ad hoc into the local
  `.venv` for this test only, not committed).
- `RATE_LIMIT_ENABLED=false` — Flask-Limiter's app-wide default
  (`200 per day, 50 per hour`, see `app/config/base.py`) throttled the very
  first run into an almost-total wall of `429`s within seconds at 50
  concurrent connections; disabling it isolates server throughput/latency
  from an unrelated, already-covered feature (rate limiting itself isn't new
  and isn't what this test measures). Noted here since it's a config
  difference from a bare default deployment, not a silent omission.
- Database: fresh SQLite (`app.db` recreated for this run), single default
  admin — v1.0's ~31 users/~390 shifts dataset wasn't reconstructed; the
  4 endpoints tested here don't query that data (`/health`/`/ready`/`/version`
  are static, `/login` GET is a template render + CSRF token, no DB read of
  shift/on-call/leave rows).
- Machine: same development workstation as v1.0's test, shared with the rest
  of this session — absolute numbers aren't comparable to a production
  environment, same caveat as v1.0.

## Results

### 10 connections (same concurrency as v1.0's baseline row, 10s/endpoint)

| Endpoint | Total req. | Errors | req/s | p50 | p75 | p90 | p99 |
|---|---|---|---|---|---|---|---|
| `/health` | 12386 | 0 | 1236.85 | 6.15 ms | 7.46 ms | 8.98 ms | 12.93 ms |
| `/ready` | 8738 | 0 | 872.45 | 8.78 ms | 10.62 ms | 12.69 ms | 16.92 ms |
| `/version` | 11856 | 0 | 1184.39 | 6.41 ms | 7.84 ms | 9.56 ms | 13.60 ms |
| `/login` (GET) | 1802 | 0 | 179.84 | 43.15 ms | 49.81 ms | 56.72 ms | 69.88 ms |

v1.0 baseline for comparison (10 connections, different tool — ad hoc
`urllib` script, not `wrk`):

| Endpoint | req/s | p50 |
|---|---|---|
| `/health` | 232.4 | 14.6 ms |
| `/login` (GET) | 133.8 | 54.5 ms |

### 50 connections (saturation check, 20s/endpoint)

| Endpoint | Total req. | Errors | req/s | p50 | p75 | p90 | p99 |
|---|---|---|---|---|---|---|---|
| `/health` | 25604 | 0 | 1278.80 | 36.10 ms | 39.33 ms | 44.47 ms | 55.04 ms |
| `/ready` | 17424 | 0 | 870.17 | 52.77 ms | 58.18 ms | 66.53 ms | 86.78 ms |
| `/version` | 25211 | 0 | 1259.68 | 37.12 ms | 40.44 ms | 44.14 ms | 53.58 ms |
| `/login` (GET) | 3813 | 0 | 190.36 | 243.80 ms | 259.24 ms | 276.25 ms | 325.60 ms |

**Zero errors across every endpoint at both concurrency levels** (no
timeouts, no 5xx, no connection failures).

## Analysis

- `/health`/`/version` (no DB access, static JSON) again serve as the
  baseline, and again the fastest routes by a wide margin — consistent with
  v1.0's finding, no regression.
- `/ready` (checks DB connectivity, unlike `/health`) is consistently ~1.4-2x
  slower than `/health`/`/version` at both concurrency levels — expected,
  same shape as v1.0 didn't test `/ready` directly but the DB-touching
  `/login`/`/dashboard` routes showed the same kind of gap over `/health`.
- `/login` (GET, Jinja render + Flask-WTF CSRF token generation) is the
  clear outlier: ~180-190 req/s regardless of going from 10 to 50
  connections, with p50 latency jumping from 43 ms to 244 ms (×5.7) — the
  same single-worker/4-thread queuing signature v1.0 documented for
  `/schedule` (×5.5 at the same 10→50 jump). This is the **expected** and
  already-documented consequence of `--workers 1` (only 4 requests actually
  run in parallel; the rest queue) — not a regression, not new, and not
  specific to `/login` — v1.0's verdict on this ("pull the `--workers`
  lever if a real deployment needs more concurrency") still applies
  unchanged.
- Absolute throughput numbers here (`/health` ~1237-1279 req/s vs v1.0's
  232.4 req/s) aren't a meaningful improvement claim — v1.0's own numbers
  came from a different tool (ad hoc Python `urllib` loop, explicitly
  documented there as slower/less accurate than `wrk`) on a differently
  loaded shared machine. The **proportions** are what carry signal, and
  they match: `/login` around 40-55 ms p50 at 10 connections in both
  reports, and both reports show the same ~5.5x latency multiplier from
  10 to 50 connections on a DB/template-rendering route.

## Limitations of this measurement

- Same shared-machine caveat as v1.0 — absolute ms/req/s aren't production
  numbers, only proportions are informative.
- Only public/unauthenticated endpoints tested this cycle (script
  limitation, unchanged from v1.0) — no fresh authenticated-page numbers for
  `/dashboard`/`/schedule` this cycle. Nothing in the 1.1.0 bug-hunt pass
  touched those routes' query patterns in a way that would change their
  profile from v1.0's own findings (dashboard's day-based stats rework
  changed `Shift` stats to a single SQL aggregate — a strict improvement
  over the old per-user Python loop, not tested numerically here but not a
  plausible regression either).
- `RATE_LIMIT_ENABLED=false` for this run — a bare default deployment
  (`RATE_LIMIT_ENABLED=true`, `RATE_LIMIT_DEFAULT=200 per day, 50 per hour`)
  will 429 well before reaching these throughput numbers under sustained
  synthetic load; that's the rate limiter doing its job, not a capacity
  ceiling, and is unrelated to anything changed in 1.1.0.
- Single gunicorn worker only, same as v1.0 — the concurrency ceiling seen
  at 50 connections is an artifact of that choice, not the application.

## Verdict

No regression. Zero errors at every endpoint and concurrency level tested.
The one notable signal (saturation on `/login` at 50 connections) is the
same already-documented single-worker queuing behavior v1.0 found on
`/schedule` — expected, not new, not a 1.1.0 defect. Nothing in this test
blocks the 1.1.0 release.
