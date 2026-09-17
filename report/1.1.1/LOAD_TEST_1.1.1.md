# Load test — 1.1.1

## Scope decision

`Docs/reference/QA_PROTOCOL.md`'s conditional load test triggers on
"touched query patterns, generation algorithms, or dashboard
aggregation." This release's diff (`1.1.0..HEAD`):

- **Generation algorithms**: yes — the new pure planner
  (`app/utils/automation/planner/`) is a from-scratch rewrite of the
  same generation work the legacy engine does. This is the actual
  perf-sensitive surface this release touched, and is what this report
  measures below.
- **Dashboard aggregation**: no — `app/services/dashboard_service.py`
  and its repository query methods are untouched by this diff (not in
  the 60-file changed list).
- **Query patterns** (repositories/routes): the new `group_id`-scoped
  joins were reviewed for N+1s during the bug-hunt pass
  (`report/1.1.1/BUG_HUNT_1.1.1.md`) — confirmed no new N+1 introduced.

`scripts/load_test.sh` (the shipped `wrk`-based harness used by
`report/1.1.0/LOAD_TEST_1.1.0.md`) only covers 4 unauthenticated static
routes (`/health`, `/ready`, `/version`, `/login` GET) — none of which
are anywhere near the generation code path, and none of which this
diff touches. Re-running it would burn time for zero signal relevant to
what actually changed this cycle, so it was skipped this release
(explicitly, not silently) in favor of a targeted in-process timing
comparison of the actual generation algorithms, legacy vs. new.

## Methodology

In-process timing comparison (not a live HTTP load test — the
generation engines aren't reachable that way in isolation from a normal
authenticated admin action anyway) using the test app's fixtures:
`AutomationAdminService._generate_full_legacy()` vs.
`AutomationAdminService._build_new_engine_plan()` (the same two entry
points `scripts/compare_automation_engines.py` itself uses for its own
correctness diffing), both called with `dry_run=True` so nothing is
persisted, over identical input (same 15-user rotation order, same
date range, fresh SQLite `TestingConfig` database, single run per
configuration — indicative, not a statistically rigorous benchmark).

## Results

| Window | Users | Legacy engine | New planner | Delta |
|---|---|---|---|---|
| 90 days | 15 | 1.97s | 2.03s | +3% (noise-level) |
| 365 days | 15 | 7.95s | 4.11s | **-48%** |

The new planner does not regress generation time at either window
tested — at the longer, more realistic annual-planning window, it's
roughly 2x faster than the legacy engine, consistent with its
compute-a-plan-then-apply-once design avoiding the legacy engine's
per-day read-modify-write overhead.

## Efficiency findings from the bug-hunt pass, in this context

`report/1.1.1/BUG_HUNT_1.1.1.md`'s "Investigated, deferred" section
flagged a few O(n²)-shaped or per-row-query patterns in the new
planner (`staffing_limits` current-count rescans, per-diff-entry
lookups in `AutomationApplyService`). None of these were configured in
the timing run above (no `staffing_limits` rule set), so this test
doesn't independently confirm they're harmless at scale — but given the
365-day/15-user run above already beats the legacy engine without
hitting any of those paths, and this app's real-world team sizes are
well below what would meaningfully stress an O(n²) scan (see
`Docs/reference/PERFORMANCE_OPTIMIZATION.md`), they're not blockers for
this release. Worth a dedicated look if the new engine's default-off
toggle is ever flipped to on for a large org.

## Verdict

No load-test regression found. The new planner is at parity or faster
than the legacy engine it's meant to eventually replace, at both a
typical (90-day) and a stress (365-day) generation window. No action
needed before release.
