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

## Finding the diff range: `$BASE_REF`

Several steps below need "everything new since the last release." The
naive `git describe --tags --abbrev=0` **fails outright**
(`fatal: No tag can describe '<HEAD>'`) whenever the release branch was
cut before the previous tag's own final commit landed — `git describe`
requires the tag to be a reachable ancestor of `HEAD`, which a
long-lived feature/release branch doesn't guarantee (confirmed by
hitting this directly while dogfooding this protocol for 1.1.0: the
`1.0.0` tag isn't an ancestor of the `1.1.0` branch at all, since
`1.1.0` branched before `main` got its final `1.0.0` version-bump
commit). Resolve `$BASE_REF` robustly instead — prefer the most recent
stable tag that *is* actually merged into `HEAD`, fall back to
`origin/main` if none is:

```bash
BASE_REF=$(git tag --merged HEAD --sort=-v:refname | grep -E '^[0-9]+\.[0-9]+\.[0-9]+$' | head -1)
BASE_REF=${BASE_REF:-origin/main}
```

## §0 — Always, every tier

Run first: cheapest checks, catch the most common problems.

1. **`make all`** (test + lint + format + security) must be 100% green.
   No tolerance here, unlike CI's `e2e` job (see §0.3) — a failure at
   this stage blocks everything else.
2. **Migration round-trip check** — only if `migrations/versions/`
   gained a file since the release base (see "Finding the diff range"
   below for `$BASE_REF`):
   ```bash
   git diff --stat "$BASE_REF"..HEAD -- migrations/versions/
   # if non-empty:
   rm -f /tmp/kairos_migration_check.db
   FLASK_APP=run.py DATABASE_URL=sqlite:////tmp/kairos_migration_check.db flask db upgrade
   FLASK_APP=run.py DATABASE_URL=sqlite:////tmp/kairos_migration_check.db flask db downgrade -- -1
   FLASK_APP=run.py DATABASE_URL=sqlite:////tmp/kairos_migration_check.db flask db upgrade
   ```
   `-- -1` (not bare `-1`): Flask-Migrate's Click-based CLI parses a
   leading `-1` as an unknown option without the `--` separator, fails
   with `Error: No such option '-1'` — confirmed by hitting this
   directly while dogfooding this protocol for 1.1.0. Confirms both
   directions actually run — catches a migration missing a working
   `downgrade()`. If there's no new migration this release, say
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
6. **Lightweight doc-accuracy check, every tier** — distinct from the
   full multi-agent doc-sync pass (§2.8, minor+ only, which re-reads
   whole docs against the whole diff): even a patch release must not
   ship with documentation that now actively contradicts the code. Diff
   `$BASE_REF..HEAD` for the files this release actually touched, then
   grep those same files' names/behavior across `CLAUDE.md`,
   `README.md`, and `ROADMAP.md` — does any surviving sentence describe
   the *old* behavior? A patch fixing a bug that a doc explicitly called
   out as a "known limitation" is the sharpest version of this: forgetting
   to remove that note is a real, easy-to-miss regression in the docs
   even though the code is correct. Not a full read-every-doc pass —
   just "does anything I changed have a stale mention," every release,
   no exceptions.
7. **Numbers/badges sanity check** — a class of staleness distinct from
   the doc-sync pass (§2.8, minor+ only): free-floating *numbers* in
   prose that silently drift every release even when the surrounding
   text stays accurate. Recompute and compare against what's currently
   written, every tier, every release (cheap, mechanical, no reason to
   gate it behind the minor-tier doc-sync pass):
   - Test count: `ROADMAP.md`'s `**Current version**` line (e.g. "1930+
     automated tests") against `python -m pytest tests/ --collect-only -q`'s
     final count.
   - Coverage %: `README.md`'s coverage badge and
     `report/TESTING_SUMMARY.md`'s stated percentage against
     `make test-coverage`'s actual `TOTAL` line.
   - `report/TESTING_SUMMARY.md`'s per-layer breakdown (unit/
     integration/e2e counts, "Last updated" line) — this file has
     drifted badly before (caught during 1.1.0's own QA-protocol
     dogfood run: it still said "1394" tests and "July 2026 —
     1.0.0-RC2" against an actual 1930/1.1.0), specifically because
     nothing else in this checklist touches it by default. Update it
     whenever any of the counts above moved.
8. **`report/` folder maintenance** — create `report/<version>/` for
   this release's own reports (see "`report/` naming and layout"
   below) before writing any of them. While in there, a quick look for
   any report file that's a genuine same-content duplicate of another,
   fully superseded one (not just "old" — see that section's narrow
   exception to "`report/*.md` stays untouched"): propose the specific
   files to the user by name and wait for explicit confirmation before
   deleting anything. Skip this sub-step entirely if nothing looks
   duplicate — it's opportunistic, not a mandatory every-release task.
9. **Manual smoke test** — see §4. Always run, every tier: it's the
   cheapest real check and the only one with a human's judgment in the
   loop.

## §1 — Patch/hotfix tier

Exactly §0. Nothing more — a patch release doesn't warrant re-auditing
code that didn't change.

## §2 — Minor tier

§0, plus:

7. **Multi-agent bug-hunt pass** (full spec below) →
   `report/<version>/BUG_HUNT_<version>.md` plus grouped `fix:`/`perf:`/`test:`
   commits, TDD throughout (reproduce red, fix, confirm green).
8. **Documentation-sync pass** (full spec below) → `docs:` commit(s).
9. **`report/TESTING_SUMMARY.md`**: update the numbers if the test count
   or coverage moved materially.
10. **Conditional load test** — only if the bug-hunt pass touched query
    patterns, generation algorithms, or dashboard aggregation:
    ```bash
    ./scripts/load_test.sh
    ```
    Produce `report/<version>/LOAD_TEST_<version>.md`, diffed against the most
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
    `report/<version>/SECURITY_AUDIT_<version>.md`: `## Summary`, `## Fixes
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

1. **Diff range**: `$BASE_REF` to `HEAD` — see "Finding the diff range"
   above.
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
   the historical `report/1.0.0/BUG_HUNT_v1.1.md`'s "Investigated, confirmed
   not a bug" section for the pattern).
5. **TDD fix loop** per real finding: reproduce red, apply the minimal
   fix, confirm green, land as its own commit grouped by concern.
6. **Write up**: `report/<version>/BUG_HUNT_<version>.md` (provenance blockquote,
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

## `report/` naming and layout

One subfolder per released version, bare three-component SemVer, no `v`
prefix: `report/1.1.0/BUG_HUNT_1.1.0.md`,
`report/1.1.0/SECURITY_AUDIT_1.1.0.md` (major tier only),
`report/1.1.0/LOAD_TEST_1.1.0.md`. Adopted starting with 1.1.0's own
release-qa run, which also reorganized every pre-1.1.0 report file this
way: everything from before the 1.0.0 release (the old
`BUG_HUNT_v1.0.md`/`v1.1.md`, `LOAD_TEST_v1.0.md`/`v1.1.md`/`v1.2.md`,
`SECURITY_AUDIT_v1.0.md`/`v1.1.md`, and every other one-off
pre-1.0.0-era investigation doc) moved into `report/1.0.0/` as-is (`git
mv`, history preserved) — their own `v1.0`/`v1.1`/`v1.2` filenames are
pre-1.0.0 stabilization-batch counters, not real release versions, kept
unrenamed inside the folder since renaming an already-referenced
historical file is its own hazard; the *folder* is what now disambiguates
which real release a batch of reports belongs to. `report/BUG_HUNT_GUIDE.md`
(methodology reference) and `report/TESTING_SUMMARY.md` (continuously
updated, not tied to one release) stay at `report/`'s root, not inside a
version folder.

A handful of same-audit-run, fully-superseded-by-a-later-file reports
(3 different-format outputs of one early bug-hunt run, one early
security-audit report — all replaced by the properly structured
versioned files that became this project's actual methodology) were
deleted outright rather than moved, on explicit confirmation — git
history still has them if ever needed. This is the one narrow exception
to "`report/*.md` stays untouched" (see `CLAUDE.md`'s "Language"
section for that rule's actual scope: it's about the repo-wide
French→English comment translation sweep specifically, not a blanket
ban on ever touching this directory) — reserve it for genuine
same-content duplicates superseded by a later file, not just "old."

## Where this fits in the release flow

Runs as a new first step in `VERSIONING.md`'s "Typical flow", before
`make bump-version` — see that doc for the rest of the sequence (bump,
tag, push, `make check-version`, manual `docker-release.yml` run).
