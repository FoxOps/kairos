# Release QA protocol

What to actually check before tagging a Kairos release, beyond the
mechanical version-bump/tag/publish steps already covered in
[`VERSIONING.md`](VERSIONING.md). This protocol grew out of a real pass
done ahead of the 1.1.0 release: a multi-agent review of everything that
had landed since `1.0.0` found and fixed a crash bug, a data-loss edge
case, an i18n bug, a stats-consistency bug, and several N+1 query
patterns — none of which `make all` (tests/lint/security) would have
caught, since they were correctness/efficiency issues in code that was
already covered by passing tests. This doc turns that into a repeatable
process instead of a one-time effort.

Driven by the `release-qa` Claude Code skill
(`.claude/skills/release-qa/SKILL.md`) — invoke it explicitly
(`disable-model-invocation: true`, it never fires from a passing mention
of "release"). This doc is the source of truth the skill implements; if
they ever disagree, this doc wins and the skill should be updated to
match.

## Picking a tier

Same [SemVer](VERSIONING.md) meaning as everywhere else in this project:

- **Patch/hotfix** (`X.Y.Z+1`): a fix, no new feature surface.
- **Minor** (`X.Y+1.0`): new features, backward-compatible.
- **Major** (`X+1.0.0`): breaking changes.

The skill asks which tier applies if not told — never guesses. Each tier
includes everything from the tier(s) below it.

## §0 — Always, every tier

Run first: cheapest checks, catch the most common problems.

1. **`make all`** (test + lint + format + security) must be 100% green.
   No tolerance here, unlike CI's `e2e` job (see §0.3) — a failure at
   this stage blocks everything else.
2. **Migration round-trip check** — only if `migrations/versions/`
   gained a file since the last tag:
   ```bash
   git diff --stat "$(git describe --tags --abbrev=0 --match '[0-9]*.[0-9]*.[0-9]*' --exclude '*-*')"..HEAD -- migrations/versions/
   # if non-empty:
   rm -f /tmp/kairos_migration_check.db
   FLASK_APP=run.py DATABASE_URL=sqlite:////tmp/kairos_migration_check.db flask db upgrade
   FLASK_APP=run.py DATABASE_URL=sqlite:////tmp/kairos_migration_check.db flask db downgrade -1
   FLASK_APP=run.py DATABASE_URL=sqlite:////tmp/kairos_migration_check.db flask db upgrade
   ```
   Confirms both directions actually run — catches a migration missing a
   working `downgrade()`. If there's no new migration this release, say
   so explicitly rather than silently skipping the line.
3. **E2E Playwright, blocking here**: `tests/e2e/test_browser_flows.py`
   stays `continue-on-error: true` in regular CI (informational there —
   see `.github/workflows/tests.yml`), but a failure here blocks the
   release.
   ```bash
   pip install -r requirements-e2e.txt && playwright install chromium
   python -m pytest tests/e2e/test_browser_flows.py -v --tb=short
   ```
4. **`CHANGELOG.md`**: rename `## [Unreleased] — X.Y.Z` to
   `## [X.Y.Z] — <YYYY-MM-DD>`, and re-read every entry under it against
   what actually shipped — an entry can go stale if something was
   reverted mid-cycle.
5. **`ROADMAP.md`**: bump the `**Current version**` line, move any
   completed "In progress" items into "Done".
6. **Manual smoke test** — see §4. Always run, every tier: it's the
   cheapest real check and the only one with a human's judgment in the
   loop.

## §1 — Patch/hotfix tier

Exactly §0. Nothing more — a patch release doesn't warrant re-auditing
code that didn't change.

## §2 — Minor tier

§0, plus:

7. **Multi-agent bug-hunt pass** (full spec below) →
   `report/BUG_HUNT_<version>.md` plus grouped `fix:`/`perf:`/`test:`
   commits, TDD throughout (reproduce red, fix, confirm green).
8. **Documentation-sync pass** (full spec below) → `docs:` commit(s).
9. **`report/TESTING_SUMMARY.md`**: update the numbers if the test count
   or coverage moved materially.
10. **Conditional load test** — only if the bug-hunt pass touched query
    patterns, generation algorithms, or dashboard aggregation:
    ```bash
    ./scripts/load_test.sh
    ```
    Produce `report/LOAD_TEST_<version>.md`, diffed against the most
    recent prior `LOAD_TEST_*.md` for regressions (same methodology:
    same endpoint set unless new routes were added, note why if it
    changed). If nothing perf-sensitive changed, say so explicitly
    rather than silently skipping the report.

## §3 — Major tier

§2, plus:

11. **Dedicated security-review pass**: run the `security-review` skill
    against the full diff since the last stable tag, and separately
    launch the `security-reviewer` subagent (`.claude/agents/security-reviewer.md`)
    scoped explicitly to that same diff — not just its default trigger
    paths, since a major release's diff can touch security-sensitive
    surface indirectly. `bandit`/`pip-audit` (already run in §0.1) are a
    baseline here, not re-litigated in depth. Produce
    `report/SECURITY_AUDIT_<version>.md`: `## Summary`, `## Fixes
    applied during this audit` (severity-tagged, root cause +
    reproduction + fix), `## Findings not fixed` (documented, not
    silently dropped). Any HIGH/CRITICAL finding blocks the release
    until fixed and regression-tested.

## §4 — Manual smoke test (every tier)

~10-15 minutes, fresh local instance (`python run.py`, default admin
`admin@kairos.local` / `admin123` unless overridden). Deliberately
covers flows either absent from `tests/e2e/test_browser_flows.py` or
only covered there at the UI-interaction level:

1. Login, land on `/dashboard`.
2. Shift CRUD on `/schedule` via the click-to-edit modal (create, edit
   user/type/time, delete).
3. On-call generation from `/admin/automation` — confirm on-calls
   appear and no mandatory-slot `[ALERT]` is silently swallowed.
4. Add a leave for a user who already has shifts/on-calls in that
   window — confirm the automatic rebalance completes cleanly, no 500,
   no duplicate/orphaned entries.
5. Full three-party shift swap: requester creates → target confirms →
   admin approves. Confirm the shift's owner actually reassigns.
6. ICS export ("me" and "everyone", group-scoped) from `/schedule` and
   the profile page — open the resulting `.ics`, confirm it parses and
   the events/labels are correct, not just a 200 response.
7. Toggle fr↔en in profile settings, spot-check `/dashboard`,
   `/schedule`, and one admin page's breadcrumbs for untranslated
   strings.
8. Main calendar: confirm per-group color dots + legend render, and the
   multi-group filter actually filters.
9. `/admin/automation/rules`: change one rule, save, confirm it
   persists and weekday labels render in the *viewer's* locale.
10. One `/api/v1/*` read call with a service-account bearer token —
    confirm 200 + expected JSON shape.
11. `make backup`, confirm a backup file is created; spot-check
    `make backup-restore` against it doesn't error.
12. OIDC login once, if a test provider is configured; otherwise note
    "skipped — no OIDC provider configured" explicitly.
13. `/version` reports the target version, once `make bump-version` has
    run.

Present this list and wait for an explicit human "all pass" or a list of
failures — by design, not something to automate away.

## Multi-agent bug-hunt pass — reusable spec

1. **Diff range**: last stable tag to `HEAD`.
   ```bash
   git describe --tags --abbrev=0 --match '[0-9]*.[0-9]*.[0-9]*' --exclude '*-*'
   ```
2. **Partition** changed files under `app/` into 4-6 axis buckets by
   path glob — starting point (adjust to what the diff actually
   touched; merge a near-empty bucket into a neighbor, split an
   oversized one):
   - Automation engine: `app/utils/automation/**`
   - Repositories/routes/API: `app/repositories/**`, `app/routes/**`, `app/api/**`
   - Frontend JS/templates: `app/static/js/**`, `app/templates/**`
   - Remaining services/models/auth/utils: `app/services/**`, `app/models/**`, `app/auth/**`, `app/utils/**` (minus automation)
3. **One parallel `general-purpose` agent per bucket** — not a fixed
   subagent file, since the axes change every release. Each reviews its
   slice of the diff for **correctness + efficiency only** (not
   security — major-tier-only, see §3; not style — already
   lint-enforced): crash bugs, data-loss edge cases, consistency bugs
   between related values, i18n regressions (hardcoded strings,
   locale resolved once at import instead of per-request), N+1/redundant
   query patterns. Report-only, one line per finding
   (`file:line — problem — suggested fix — how to verify it`); state
   "nothing found" explicitly rather than padding the report.
4. **Triage** in the main thread: dedupe overlapping findings at bucket
   boundaries, discard false positives with a stated reason each (see
   the historical `report/BUG_HUNT_v1.1.md`'s "Investigated, confirmed
   not a bug" section for the pattern).
5. **TDD fix loop** per real finding: reproduce red, apply the minimal
   fix, confirm green, land as its own commit grouped by concern.
6. **Write up**: `report/BUG_HUNT_<version>.md` (provenance blockquote,
   `## Fixed in this PR`, `## Investigated, confirmed not a bug`,
   `## Verdict`); tag new `CHANGELOG.md` entries `**[Optimization
   pass]**` inside their normal `### Fixed`/`### Changed` section.

## Documentation-sync pass — reusable spec

Two parallel agents (smaller fan-out than the bug-hunt pass):

- **A — architecture/reference**: the sections of `CLAUDE.md` actually
  touched by this release's diff (not the whole file blind),
  `Docs/architecture/ARCHITECTURE.md`, `Docs/architecture/ERD.md`,
  `Docs/reference/PERFORMANCE_OPTIMIZATION.md`.
- **B — user-facing**: `Docs/guides/ADMIN_GUIDE.md`,
  `Docs/guides/USER_GUIDE.md`, `ROADMAP.md`.

Both verify every claim against the current code, not against the
existing doc text (this repo's own stated rule, see `Docs/README.md`) —
report every stale, contradictory, or "not yet implemented"/"planned"
claim the diff shows has actually shipped, or the reverse. Report-only;
apply fixes as grouped `docs:` commits.

## `report/` naming

Bare three-component SemVer, no `v` prefix: `report/BUG_HUNT_1.1.0.md`,
`report/SECURITY_AUDIT_1.1.0.md` (major tier only),
`report/LOAD_TEST_1.1.0.md`. This is deliberately distinct from the
older `BUG_HUNT_v1.0.md`/`v1.1.md`, `LOAD_TEST_v1.0.md`/`v1.1.md`/`v1.2.md`,
`SECURITY_AUDIT_v1.0.md`/`v1.1.md` files, which carry a literal `v`
prefix and a two-component number that was a pre-1.0.0
stabilization-batch counter, not a real release version — don't reuse
that scheme, and note the distinction in each new report's own
provenance blockquote so a future reader isn't confused about which
numbering era a file belongs to.

## Where this fits in the release flow

Runs as a new first step in `VERSIONING.md`'s "Typical flow", before
`make bump-version` — see that doc for the rest of the sequence (bump,
tag, push, `make check-version`, manual `docker-release.yml` run).
