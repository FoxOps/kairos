# 📋 Refactoring Report - Phase 6: Additional Optimizations
**Branch**: `refacto/phase6`
**PR**: [#102](https://github.com/FoxOps/leviia-schedule/pull/102)
**Start date**: 2026-07-12
**Status**: 🟢 Ready for review
**Base**: `main` (includes Phases 1 to 5, PR #101 merged)

---

## 📈 Current state

Auditing the real status of each sub-item before writing any code —
several previous phases showed that the original doc/plan sometimes
describes things that are already done, already dead, or inapplicable
without a major tooling change (JS bundler, real Kubernetes infra,
etc.). Details follow in the Log.

---

## 🎯 Work plan

### 6.1 Performance
- [x] Image lazy loading — not applicable, see Log
- [ ] JS code splitting — documented, deferred (no bundler)
- [ ] CSS/JS tree shaking — documented, deferred (no bundler)
- [x] Gzip/Brotli compression

### 6.2 Security
- [x] CSP (Content Security Policy)
- [x] Security headers
- [x] Regular dependency audit — bandit/safety already in CI, cadence documented

### 6.3 DevOps
- [x] Improved CI/CD (GitLab, future repo)
- [x] Optimized Docker
- [x] Kubernetes ready
- [x] Monitoring (Prometheus, Grafana)

---

## 📝 Log

### CSP + security headers always active (commit `6764d19`)

**Real bug found and fixed**: in `app/__init__.py`, Talisman was only
initialized if `TALISMAN_FORCE_HTTPS` was true. Yet this flag should
only control the HTTP->HTTPS redirect and HSTS, not the other headers
(CSP, X-Content-Type-Options, X-Frame-Options...). Concrete
consequence: `docker/docker-compose.yml` sets
`TALISMAN_FORCE_HTTPS=false` (no TLS termination inside the container,
a reverse proxy handles it) — this deployment therefore had **no**
security header at all. Fixed: Talisman is now always initialized
except in `TESTING`.

**Strict CSP added** (`CSP_POLICY` in `app/__init__.py`):
`script-src 'self'` (blocks any injected `<script>`), `object-src
'none'`, `style-src 'self' 'unsafe-inline'` (a single dynamic style in
`dashboard.html`, chart bar width), `script-src-attr 'unsafe-inline'`
(21 remaining `onclick=""` attributes in templates — static content
written by developers, never user data; `script-src-attr` is a
distinct level-3 CSP directive from `script-src`, nonces don't cover
event attributes).

To allow `script-src 'self'` without `unsafe-inline` or a nonce, the
~576-line inline script in `index.html` (FullCalendar config: drag &
drop, shift creation via modal, etc.) was externalized to
`app/static/js/calendar/fullcalendar-config.js` (ES6 module). Server
data (event list, `is_admin`, CSRF token) now passes through `data-*`
attributes and a `<script type="application/json">` block rather than
Jinja interpolation inside inline JS.

4 regression tests added in `tests/integration/test_security.py`
(gating even without `TALISMAN_FORCE_HTTPS`, exact CSP content, no
executable inline script on `/`). 771 tests pass.

### Gzip/Brotli compression (flask-compress)

**Real bug found and fixed**: `flask-compress==1.24` is a declared
dependency with its config (`COMPRESS_REGISTER`,
`COMPRESS_MIMETYPES`) in `app/config/production.py`, but `Compress`
was neither imported nor instantiated anywhere in `app/__init__.py`.
Compression therefore did **nothing** in practice, regardless of
environment — the config existed but the extension had never actually
been wired to the application.

Fixed: `compress = Compress()` instance at module level (same
pattern as `db`/`login_manager`/`csrf`), `compress.init_app(app)`
called in `create_app()`, disabled in `TESTING` (the test client
doesn't decode `Content-Encoding`, which would break the text
assertions on `resp.data` across the rest of the suite).

Verified on a real server (`curl -H "Accept-Encoding: gzip" ...`):
`/login` → `Content-Encoding: gzip`, reduced size. Static files served
via streaming (`fullcalendar-config.js`, 27 KB) use br/zstd rather
than gzip (flask-compress's default behavior for streamed responses —
gzip is excluded from `COMPRESS_ALGORITHM_STREAMING` upstream): 27,166
→ 5,099 bytes in br, 5,407 in zstd.

2 regression tests added in `tests/integration/test_performance.py`
(`TestCompression`): compressed response if `Accept-Encoding: gzip`,
uncompressed otherwise.

### Image lazy loading — not applicable

Audit (`find app/static/images app/templates -iname "*.png" -o ...`):
the project's only image is `app/static/images/favicon.png`. No
content image to lazy-load. Nothing to do.

### JS code splitting / tree shaking — documented, deferred

No bundler in the project (`package.json`, `webpack.config.js`,
`vite.config.js`, `rollup.config.js`: all absent). JS is served as-is
as static files (vanilla ES6 modules, local vendor libs). Introducing
a bundler (Vite/esbuild/Rollup) to enable code splitting + tree
shaking would be a major tooling change (build step, config, CI to
adapt) outside the "optimizations" scope of this phase — user
decision: document and defer rather than introduce a bundler in this
phase.

### Regular dependency audit

`bandit` and `safety` were already running (job `run_security` in CI,
local `make security` target) but only on push/MR — never on a
cadence independent of commits (a dependency can become vulnerable
without any code changing). A scheduled GitLab pipeline (CI/CD >
Schedules, a GitLab project property, not configurable from the
repo's YAML) is the standard way to cover this; a comment was added in
`.gitlab-ci.yml` documenting how to wire it up
(`$CI_PIPELINE_SOURCE == "schedule"`) once the GitLab repo is in
place.

### CI/CD (.gitlab-ci.yml) — commit `4ce3c5c`

- `.python-template` installed dependencies twice: once before
  `python -m venv .venv` (into the container's system Python, then
  lost), once after. Reordered to install only once, inside the venv.
- `run_tests` declared `artifacts.reports.junit: junit.xml` and a
  coverage regex (`coverage: '/^TOTAL...'`) without ever passing
  `--junitxml` or `--cov` to pytest — both had been broken from the
  start (no file generated, no line to match). Fixed.
- `deploy_swarm` deployed via `docker stack deploy -c
  docker-compose.prod.yml`, a file not found anywhere in the repo
  (confirmed by exhaustive search) — dead job. Removed (k8s via
  `deploy_production` is the real deployment path).
- `deploy_production`: `kubectl rollout status ... -n production`
  targeted a namespace that doesn't exist in any `k8s/` manifest (all
  of them declare `namespace: kairos`) — would have failed with "not
  found". Fixed. The job never actually deployed the image just built
  by `build_docker` anyway: `k8s/deployment.yaml` has a hard-coded
  `your-registry/kairos:latest` placeholder. Added a `sed` to replace
  it with `$CI_REGISTRY_IMAGE:latest` before `kubectl apply`.

### Optimized Docker — commit `4ce3c5c`

`docker/Dockerfile.optimized` (multi-stage, created in Phase 1 but
never wired up anywhere — not CI, not docker-compose.yml, not the
Makefile) was built and run locally for validation (`docker build` +
`docker run` + `curl /health`), as a starting point before promoting
it. First attempt: `ModuleNotFoundError: No module named 'flask'` at
startup despite an image that builds without error — real bug:
`pip install --user` in the builder stage installs into
`/root/.local`, which inherits the base image's `700` mode on
`/root`; once `USER appuser` (non-root) is active, that directory is
unreadable, and `--chown` on just the copied content changes nothing
since it's `/root` itself blocking traversal. Fixed by installing with
`pip install --prefix=/install` then copying to `/usr/local`
(already in the `python:3.11-alpine` image's default `sys.path`,
already `755`). Retested successfully: `/health` returns `200`,
`docker exec whoami` returns `appuser`, both development mode
(`python run.py`) and production mode (`FLASK_ENV=production` →
Gunicorn) verified.

Size compared with `docker images`: 415 MB (optimized, multi-stage)
vs. 926 MB (old Dockerfile, single-stage) — a bit more than 2x
lighter. `docker/Dockerfile.optimized` replaced `docker/Dockerfile`
(promotion following the plan already written in
`report/DOCKER_OPTIMIZED_TEST.md` §"Next steps"), the old file
removed to avoid drift between two Dockerfiles.
Default `FLASK_ENV` reset to `development` in the image (the
optimized one had `production` by default, which would have run
Gunicorn by default in the dev `docker-compose.yml` stack, which
doesn't set `FLASK_ENV`).

Side bugs found and fixed along the way:
- `docker-compose.yml` had no `build:` key at all — `docker compose
  build` couldn't build anything. Added (`context: ..`, `dockerfile:
  docker/Dockerfile`), verified with a real `docker compose build`.
- `docker/Makefile`: `up-prod` used `up -d -e FLASK_ENV=production`
  — `-e` is not a valid flag for `docker compose up` (it's a `docker
  run` flag). Fixed to `FLASK_ENV=production docker compose ...
  up -d`, and added `FLASK_ENV=${FLASK_ENV:-development}` in
  `docker-compose.yml` so the shell environment variable actually
  reaches the container.
- `docker/Makefile`: `shell` targeted `exec web sh`, a service that
  doesn't exist in `docker-compose.yml` (the service is called
  `kairos`). Fixed.
- `docker/setup-env.sh` looked for `.env.example` in the current
  directory, whereas that file lives at the repo root and the script
  lives in `docker/` — broken regardless of which directory it was
  run from (nothing currently calls it anywhere, an orphaned script,
  but worth fixing anyway). `cd` to its own directory at script entry
  + reference `../.env.example`.

Not touched: the hard-coded IP (`192.168.1.169`) in the mock OIDC
config in `docker-compose.yml`. This is a deliberate workaround for a
problem already solved by a dedicated commit on this work branch
(OIDC issuer reachability from both the container and the host
browser) — touching it again would risk reintroducing that bug, out
of scope for this phase.

### Kubernetes ready — commit `4ce3c5c`

`k8s/deployment.yaml` had `checksum/config` / `checksum/secret`
annotations in Helm syntax (`{{ include (print ...) | sha256sum }}`)
on a manifest applied as-is via `kubectl apply -f k8s/` (no Helm in
this project, confirmed by `find` search — no `Chart.yaml` anywhere):
this syntax was never interpreted, remaining literal text in the
annotation. The intended purpose (forcing a rolling restart of pods
when the ConfigMap or Secret changes) therefore never happened. Dead
annotations removed, alternative documented in a comment (explicit
`kubectl rollout restart`).

The manifests themselves (probes `/health`/`/ready`, Service, Ingress,
ConfigMap, Secret template, PVC, HPA, PDB, Namespace) already existed
and are correct (probes already verified in Phase 4). YAML validation
of all `k8s/*.yaml` files done with `yaml.safe_load_all` (no
`kubectl` available in this environment for a real
`--dry-run=client`).

### Monitoring — Grafana — commit `4ce3c5c`

No Grafana artifact existed in the repo (exhaustive `find`, zero
results). Created `grafana/kairos-dashboard.json` (importable
as-is, Prometheus datasource configurable via a template variable):
requests/s and errors/s per endpoint, p95 latency, p95 SQL query time,
active users/sessions, business volume (shifts/on-call/leave/users/
groups), CPU/memory/disk. Every metric name used in the dashboard
verified one by one against
`app/utils/prometheus_metrics.py` (cross-grep of both lists). JSON
syntactically validated. Dashboard **not** tested against a real
Grafana instance — none available in this environment, explicitly
noted in `grafana/README.md`.

---

*Last updated: 2026-07-12 — Phase 6 complete: 6.1 Performance,
6.2 Security, 6.3 DevOps all handled. Remaining: final review before merge.*
