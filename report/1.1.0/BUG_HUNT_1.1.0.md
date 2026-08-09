# Bug Hunt 1.1.0

> First dedicated optimization/bug-hunt pass over the code that landed in
> the 1.1.0 cycle (the configurable automation rules engine, per-group
> scheduling, calendar group colors/filter, unified filter-bar bulk-delete,
> ICS export modal, dashboard day-based stats) — unlike the pre-1.1.0
> codebase, which already had a dedicated 1.0.0 security audit, bug hunt,
> and load test (`SECURITY_AUDIT_v1.0.md`, `BUG_HUNT_v1.0.md`,
> `LOAD_TEST_v1.0.md`), this cycle's new code had not been through an
> equivalent pass yet. **Naming note**: this file uses the new bare-SemVer
> naming (`1.1.0`, no `v` prefix) adopted in `Docs/reference/QA_PROTOCOL.md`
> — distinct from `BUG_HUNT_v1.0.md`/`v1.1.md`, whose `v1.0`/`v1.1` numbers
> were pre-1.0.0 RC-stabilization-batch counters, not real release versions.
>
> Conducted in two rounds: an initial pass (4 parallel agents, split by code
> area — automation engine, repositories/routes, frontend JS/templates,
> remaining services/models — each reviewing for correctness + efficiency
> against the diff since `main`) found and fixed 7 issues; a second,
> narrower pass — the first real run of the new tiered release QA protocol
> (`Docs/reference/QA_PROTOCOL.md`, `release-qa` skill) — specifically
> re-reviewed the fixes that came out of round 1 (2 parallel agents, scoped
> to the ~266-line delta rather than the whole diff again) and found 2 more.
> Every finding below was verified by direct code reading, then reproduced
> empirically (a real test that fails before the fix, passes after) — no
> speculation.

## Fixed in this PR

### 1. HIGH — `/schedule`/`/oncall`'s "delete filtered result" 500s when a group filter is active

**Files**: `app/repositories/shift_repository.py`,
`app/repositories/oncall_repository.py`.

`_filtered_query()`'s `group_id` branch built the `WHERE` clause with
`.join(User, ...)`, and SQLAlchemy's bulk `Query.delete()` rejects a query
that already has a `join()`/`outerjoin()` applied
(`InvalidRequestError: Can't call Query.update() or Query.delete() when
join()... has been called`) — this exact restriction was already
documented in this same file's own `delete_overlapping_range()` comment,
which worked around it with a subquery; `delete_filtered()` didn't reuse
that workaround. Concretely: an admin filters `/schedule` or `/oncall` by
group, clicks "delete filtered result" → 500, delete never runs.
Reproduced directly (regression test crashed with the exact error before
the fix). Fixed by switching the `group_id` branch to the same
`User.id`-subquery pattern already used elsewhere in the file, with
`synchronize_session="fetch"` when a subquery is involved (`"evaluate"`
can't reconcile a subquery `IN` against already-loaded session objects).

### 2. MEDIUM — Dashboard on-call stats: `this_month` could exceed `total`

**File**: `app/services/dashboard_service.py`.

`oncall_total` summed fractional duration (`(end-start).total_seconds() /
86400`, rounded); `oncall_this_month`/`last_month` counted whole inclusive
calendar days on `.date()`-truncated bounds — two different units. A
~6.4-day on-call rounds to `total=6`, but its two calendar-day dates are 7
days apart (8 inclusive days), so `this_month` could show 8 against a
total of 6. Fixed by giving on-call spans their own fractional-duration
clipping helper (`_clipped_duration_days()`), matching the unit `total`
already used. `Leave` spans are genuinely date-only and keep the
whole-day `_clipped_days()` helper — this wasn't a shared-helper bug, it
was one entity (`OnCall`) using the wrong one of two legitimately
different helpers.

### 3. MEDIUM — `/admin/automation/rules`' weekday labels frozen to process-startup locale

**File**: `app/routes/admin_automation_rules_routes.py`.

`WEEKDAY_LABELS = [_("Lundi"), ...]` was built at module scope, so
`gettext()` resolved once when the process started (no request context),
never per-viewer language — unlike every other `_()` call in this
codebase, which resolves per-request via `get_locale()`. An English-locale
admin would permanently see French weekday names on this page. Fixed by
moving the list into a function called at render time.

### 4. LOW — 12 "Admin" breadcrumb labels never routed through `_()`

**Files**: 12 admin templates (`app/templates/admin/**`).

Every breadcrumb call site wrapped its other segments in `_(...)` except
the shared "Admin" segment, which was a bare string — invisible to
`pybabel extract`, so it could never be translated even though the
catalogs already had a translated `"Admin"` entry from elsewhere in the
app. Mechanical fix: wrap all 12 in `_("Admin")`.

### 5. MEDIUM — Date-range filter bar discards a valid field when the other one is malformed

**File**: `app/utils/helpers/pagination_helpers.py`.

`parse_date_range_filter()` (shared by `/schedule`, `/oncall`, `/leave`)
parsed `date_from` and `date_to` inside one `try`/`except` block — a
malformed `date_to` silently discarded an already-valid `date_from` too.
Fixed by parsing each field independently.

### 6. HIGH — Per-group "regenerate" can permanently lose a group's data

**Files**: `app/services/automation_admin_service.py`,
`app/repositories/shift_repository.py` (new `group_id` param on
`delete_in_date_range()`).

`clear_period()`/`refresh_shifts()`'s "regenerate" action deleted every
on-call/shift in the target period unconditionally, even under
`"per_group"` scheduling mode, while the regeneration loop right after
only recreates data for *currently* eligible groups
(`is_part_of_oncall`/`is_part_of_schedule`). A group's on-calls/shifts
created while it was still eligible, then toggled out of eligibility,
were silently deleted and never recreated — real data loss, not just
theoretical, though a narrow window (requires a participation toggle
*and* a regenerate covering a period that group already had data in).
Fixed by scoping the delete to exactly the same group list the
regeneration loop is about to repopulate (`_delete_oncalls_scoped()`/
`_delete_shifts_scoped()`, one `DELETE` per group when scoped, a single
unscoped `DELETE` under `"shared"` mode — byte-for-byte equivalent to the
old behavior in that mode). 4 regression tests: `generate_full()` and
`refresh_shifts()`, both entities, each confirming a toggled-out group's
pre-existing data survives.

Round-2 review of this fix (release-qa protocol) found no further issues
— confirmed the group list is computed once and reused for both the
delete and the regeneration loop at every call site (no path recomputes
it separately), confirmed the empty-group subquery case degrades to "no
rows deleted" rather than "all rows deleted" (a real SQL subquery, never
a Python list, so no `.in_([])` footgun), and confirmed shared-mode
behavior is unchanged.

### 7. MEDIUM — N+1 in scheduling-mode settings and the whole rule-resolution path

**Files**: `app/services/settings_service.py`,
`app/utils/automation/rules/base.py`.

`get_shift_scheduling_mode()`/`get_oncall_scheduling_mode()` hit the DB on
every call, called once per user/per day inside generation and validation
loops. `AutomationRuleType.resolve()` (the base class every one of the 8
rule types inherits) had the same problem, plus `generate_full_schedule()`
separately re-resolved the same rules again per day for its own
gap-aggregation pass. A multi-week schedule generation run issued one
`AutomationRule` query per rule *per day* instead of one per rule for the
whole run — confirmed directly: 285 `automation_rules` queries for a
35-day/100-shift generation run before the fix, 5 after. Fixed by caching
both on `flask.g` for the request lifetime, same pattern already
established for `get_default_timezone()`. Regression test asserts the
query count stays bounded regardless of period length
(`test_generate_full_schedule_query_count_stable_across_period_length`).

### 8. MEDIUM — Dashboard shift stats return `Decimal`, not `int`, on MySQL/MariaDB

**File**: `app/repositories/shift_repository.py`
(`get_day_count_stats()`, added by finding #7's sibling fix — see below).

Found in round 2, reviewing the new SQL-aggregation dashboard fix (see
"Changed" note below): MySQL/MariaDB's `SUM()` of an exact-numeric `CASE`
expression returns `DECIMAL`, not `INT` — so `this_month`/`last_month`
came back as `decimal.Decimal` on those two engines (both explicitly
supported per `CLAUDE.md`'s Database section) while `oncall`/`leave`
stayed plain `int` in the same `get_stats()` return dict. Invisible under
this repo's SQLite-only test suite; would raise
`TypeError: Object of type Decimal is not JSON serializable` if this dict
ever went through `jsonify()`. Fixed with an explicit `int(...)` wrap.
Regression test asserts `type(...) is int` on all three returned values.

### 9. LOW — Rule-resolution cache had no invalidation path

**File**: `app/models/automation_rule.py` (`AutomationRule.set()`).

Found in round 2, reviewing finding #7's cache: the "safe to cache"
reasoning depended entirely on today's one caller
(`admin_automation_rules_routes.py`) always redirecting after saving, with
nothing enforcing it — a future same-request "save and preview" action
calling `resolve()` again would have silently seen the stale pre-save
value. Not reachable by any current caller (confirmed: the only two
`set()` call sites both precede a `redirect()`), but now enforced rather
than left to caller discipline: `set()` pops its own `(rule_type,
group_id)` key from the `flask.g` cache after committing. Regression test
calls `set()` then `resolve()` again inside one request context and
asserts the fresh value.

## Changed (not bugs, efficiency)

- **`/dashboard`'s shift stats moved from an unbounded Python fetch to a
  single SQL aggregate query.** `ShiftRepository.get_day_count_stats()`
  (`COUNT` + conditional `SUM`) replaces `list_dates_for_user()` + a
  Python loop, which transferred one row per shift a user had *ever* been
  assigned, unbounded by tenure, on every dashboard load. `OnCall`/`Leave`
  deliberately stay Python-side — see `Docs/reference/PERFORMANCE_OPTIMIZATION.md`
  for the cross-engine date-arithmetic reasoning.
- Composite DB index `AutomationRule(rule_type, group_id)` (migration
  `b8e2f4a91c6d`) — every real lookup filters on both columns together.
- Test suite parallelized with pytest-xdist — 548s → 166s locally (4
  cores), unrelated to correctness but found/fixed in the same pass.

## Investigated, confirmed not currently reachable

- **`app/utils/automation/rules/base.py`'s cache key,
  `group.id if group is not None else None`** — round-2 review flagged
  that an unsaved (`id is None`) transient `Group` instance would collide
  with the org-wide-default cache key. No current call site ever resolves
  rules against an unsaved `Group` (confirmed by grep of every `resolve()`
  call site), so left as-is rather than adding defensive code for a path
  nothing exercises — revisit if a future "preview for a not-yet-saved
  group" flow is added.

## Deferred, lower priority (real, not fixed in this pass)

Identified in round 1, deliberately not fixed — each would need its own
change rather than a rushed one, tracked here so they're visible, not
silent:

- Automation rule resolution inside `generate_daily_shifts()`/
  `generate_full_schedule()` still does some duplicate *computation* (not
  queries — finding #7 already fixed the query cost) recomputing the same
  coverage gaps twice. Cheap now that the query it depends on is cached;
  restructuring the generation loop's return contract to avoid it isn't
  worth the risk this cycle. See `Docs/reference/PERFORMANCE_OPTIMIZATION.md`.
- `LeaveService.purge_resolved_for_user`/`purge_all_resolved`-adjacent
  `delete_filtered` for `Leave` triggers one rebalance per matching row,
  with no upper bound — pre-existing, documented, intentional
  correctness-over-speed tradeoff (per its own docstring), not something
  this pass changed.
- `admin_automation_routes.py`'s `get_automation_status()` issues one
  query batch per group for the dashboard's per-group breakdown cards —
  real N+1, bounded by group count (naturally small at this app's scale),
  not worth the restructuring risk this cycle.
- Redundant `/api/users`+`/api/shift-types` fetches on every calendar
  edit-modal open (`fullcalendar-config.js`) — no caching between calls.
  Frontend-only, no server cost, deferred.
- Minor duplicated time-construction logic between `shift_service.py` and
  `common_helpers.py` — cosmetic, no behavior difference.

## Verdict

9 real findings across two rounds, all fixed with a regression test each
(TDD: reproduced red, fixed, confirmed green). Two of the nine (#8, #9)
were only found because the new release QA protocol's round-2 pass
specifically re-reviewed round 1's own fixes instead of treating them as
already correct — the protocol's own first real-world validation. Nothing
found in either round blocks the 1.1.0 release; the 5 deferred items are
tracked, not forgotten.
