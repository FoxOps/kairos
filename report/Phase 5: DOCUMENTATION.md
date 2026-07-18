# 📋 Refactoring Report - Phase 5: Documentation
**Branch**: `refacto/phase5`
**PR**: [#101](https://github.com/FoxOps/leviia-schedule/pull/101)
**Start date**: 2026-07-12
**Status**: 🟢 Complete
**Base**: `main` (includes Phases 1 + 2 + 3 + 4, PR #100 merged)

---

## 📈 Current state (before restructuring)

A (lowercase) `docs/` folder already exists: 14 markdown files,
~340 KB, all dated July 4th — **before** Phases 2/3/4, which
massively changed the architecture (main.py → services/repositories,
CSS/JS restructured, tests reorganized, CSRF added, dead code
removed). Audit under way to distinguish what remains accurate from what is
now wrong/outdated, before deciding what to keep, rewrite, or
delete.

The user explicitly requested that all documentation live
in a (capitalized) `Docs/` folder, with subfolders by type where
relevant — the existing (lowercase) `docs/` will therefore be renamed/reorganized,
not duplicated.

---

## 🎯 Work plan

### 5.1 Technical Documentation
- [x] Architecture: Mermaid diagrams (`Docs/architecture/ARCHITECTURE.md`)
- [x] API: OpenAPI/Swagger documentation (`Docs/api/API.md` + `openapi.yaml`)
- [x] Database: ERD schema (`Docs/architecture/ERD.md`)
- [x] User flows: sequence diagrams (`Docs/architecture/SEQUENCE_DIAGRAMS.md`)

### 5.2 User Documentation
- [x] Quick start guide (`Docs/guides/QUICK_START.md`)
- [x] Installation guide (dedicated section in `Docs/guides/USER_GUIDE.md`,
      more complete than the quickstart)
- [x] Admin guide (`Docs/guides/ADMIN_GUIDE.md`, SSO/OIDC
      section added — promised by QUICK_START.md but never written)
- [x] FAQ (`Docs/guides/FAQ.md`, new, extracted and corrected from
      USER_GUIDE.md)

---

## 📝 Log

*(updated at each step)*

### 2026-07-12 — docs/ → Docs/ reorganization + 5.1 Technical Documentation complete

**Preliminary audit** (Explore agent, reading the 14 files + comparison
with `app/routes/*.py`, `app/models/*.py`, `CLAUDE.md`): per-file
verdict (KEEP / UPDATE / REWRITE / DELETE), real list of HTTP
endpoints, real list of model fields. Basis for all the work that
followed rather than rewriting blindly.

**Reorganization**: `docs/` (14 files, lowercase) → `Docs/`
(capitalized, explicit request), split into 5 subfolders by type
(`architecture/`, `api/`, `guides/`, `deployment/`, `reference/`).
`SUMMARY.md` removed (confirmed to be a pure summary-of-summaries, no unique
content). Broken links fixed in the root `README.md`, `ROADMAP.md`,
`.gitlab-ci/.gitlab-ci.yml`. The root `README.md` also fixed along the way on
several outdated points found in passing: `app/models.py` →
`app/models/`, Authlib/icalendar versions, test statistics (522
tests/66% before Phase 4 → 768 tests/81% today), dead link to a
`TESTING_SUMMARY.md` that never existed.

**ARCHITECTURE.md** rewritten in full (the old version described
`app/models.py` as a flat file, no mention of services/repositories
or the app-wide CSRF) — 2 Mermaid diagrams (layered view,
blueprint split across multiple files).

**ERD.md** (new): Mermaid `erDiagram` generated from the real models.
Fixes an error in the old doc (`Leave` has no `reason`
field) and documents `AutomationConfig`, absent from any prior
doc.

**SEQUENCE_DIAGRAMS.md** (new): 5 diagrams — basic login,
OIDC/SSO login, adding leave with automatic shift
rebalancing, updating a shift via the JSON API with CSRF
verification, ICS export (session or bearer token).

**API.md** rewritten in full (the old version documented
fictitious routes — `/leaves/my-leaves`, `/schedule/my-shifts`,
`/admin/users/generate-token/<id>` — and omitted nearly all of the
real `/api/*` endpoints). **`openapi.yaml`** (new): OpenAPI
3.0 spec for the 9 real JSON endpoints, validated with
`openapi-spec-validator`.

### 2026-07-12 — 5.2 User Documentation + reference/ cleanup complete

**QUICK_START.md / USER_GUIDE.md**: neither mentioned
`cp .env.example .env` before the first startup — without this file,
`DEFAULT_ADMIN_PASSWORD` is unset and `run.py` generates a random admin
password that is never displayed, not `admin123` as documented
everywhere. Verified by comparing `run.py::create_default_data` against the
real `.env.example`, fixed in both places. `USER_GUIDE.md` also fixed
on `SQLALCHEMY_DATABASE_URI` (internal Flask config, not the real
name of the environment variable — that's `DATABASE_URL`), the
"edit a shift/an on-call/a leave" sections (possible via
drag-and-drop in edit mode, admin-only, not just "delete and
recreate"), and the leave validation rules (read from
`can_add_leave()`: no future-date check, no blocking
on a shift/on-call overlap — automatic rebalancing instead).

**FAQ.md** (new): FAQ section extracted from `USER_GUIDE.md` (avoids the
duplication observed with `SUMMARY.md`), fixed on the same points,
plus an entry on CSRF-related 400 errors.

**ADMIN_GUIDE.md**: all references to `config.py` fixed to point to
`app/config/` (+ a note on the distinction with the legacy root
`config.py`); "Generate an ICS token via Admin > Users" fixed — it's
a self-service action (`POST /profile/ics-token`), the admin route described
never existed; business-rule customization paths updated
(`app/auth/decorators.py`, moved in Phase 2); "MySQL/MariaDB -
coming soon" fixed — already supported via `DATABASE_URL`. **Full
SSO/OIDC section added** (enabling it, disabling basic auth,
RP-initiated logout, claim mapping, Docker case with
`OIDC_INTERNAL_ISSUER`): `QUICK_START.md` had promised this content
("Administrator Guide for a full SSO/OIDC setup")
all along without it ever having existed.

**ENVIRONMENT_VARIABLES.md**: Pagination/Lazy Loading/
Query Optimization/Performance Monitoring sections removed — all
read by `config_performance.py`, a module verified to be imported
nowhere in `app/` or `run.py` (the features they configured
were removed as dead code in Phase 4). Setting them in `.env` now has
no effect; documented explicitly rather than silently removed.
Cache section trimmed to the variables actually read. Full SSO/OIDC
section added (previously absent).

**PERFORMANCE_OPTIMIZATION.md** rewritten in full: 1397 → ~100
lines. ~90% of the old content documented systems that no longer exist
(advanced pagination, 785-line lazy loading, a `PerformanceMonitor`
that, per the Phase 4 audit, had actually never worked — broken
import to a nonexistent module). New content: cache, `eager_load`,
composite indexes, pointer to `prometheus_metrics.py`/`health.py`.

**ERROR_HANDLING.md**: `config.py` references fixed to point to
`app/config/`, renamed logging function (`configure_logging()` in
`app/utils/logging/logger.py`, not `setup_logging()` in
`app/__init__.py`), CSRF note added.

**DEPLOYMENT_GUIDE.md**: file detected as binary by `file`
(191 corrupted sequences — emoji and accented characters replaced by
a control byte + the Unicode code point's hex code as literal text).
Fully deterministic and reversible pattern, decoded by script; 4 edge
cases resolved manually from context. Verified: 0 remaining control
bytes, all Unicode characters valid, no other file in `Docs/` affected by
the same issue.

**Docs/README.md** rebuilt to reflect the subfolder structure.
Systematic check of every internal markdown link
(`Docs/` + root `README.md` + `ROADMAP.md`, Python script,
real path resolution): 2 dead links found and fixed
(`CONTRIBUTING.md` missing in `ROADMAP.md`, anchor invalidated by a
section rename).

**Phase summary**:
- `docs/` → `Docs/` reorganized into 5 subfolders, `SUMMARY.md` removed
- 3 files rewritten in full (`ARCHITECTURE.md`, `API.md`,
  `PERFORMANCE_OPTIMIZATION.md` — all judged mostly fictitious by
  the initial audit)
- 3 new technical documents (`ERD.md`, `SEQUENCE_DIAGRAMS.md`,
  `openapi.yaml`) + 1 new guide (`FAQ.md`)
- 5 files fixed (`USER_GUIDE.md`, `ADMIN_GUIDE.md`, `QUICK_START.md`,
  `ENVIRONMENT_VARIABLES.md`, `ERROR_HANDLING.md`)
- 1 real encoding bug fixed (`DEPLOYMENT_GUIDE.md`, 191 corrupted
  sequences, deterministic decoding)
- SSO/OIDC section written for the first time (promised since
  `QUICK_START.md`, never delivered)
- Several factual inaccuracies fixed after reading the code directly
  (leave validation, ICS token workflow, default admin
  password, editing shifts/on-calls/leave)

---

*Last updated: 2026-07-12*
