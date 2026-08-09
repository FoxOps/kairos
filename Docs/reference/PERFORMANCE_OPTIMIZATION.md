# Performance optimization

This documents what actually exists in the code - there is no cache
system, no advanced pagination, and no lazy-loading system in this
application. Caching, if needed, is expected to be handled externally
(reverse proxy / dedicated cache), not by the app itself.

## Avoiding N+1

There is no decorator-based eager-loading helper — an earlier
`app/utils/optimizations/eager_load` decorator was removed once it was
confirmed to be a no-op on its only remaining call site (`index()` in
`app/routes/dashboard_routes.py` returns a rendered template, and the
decorator only acted on a returned `Query`/model instance). N+1
avoidance instead lives directly in the repository layer, via
SQLAlchemy's `joinedload()` — see for example
`ShiftRepository.list_paginated()` in
`app/repositories/shift_repository.py`, which loads `user` and
`shift_type` in a single query, or `AuditLogRepository.list_paginated()`
(`app/repositories/audit_log_repository.py`), which bulk-preloads
`AuditLog.actor` (a plain `@property`, not a real `db.relationship()`,
so it can't use `joinedload()` — see `architecture/ERD.md`) since one
`db.session.get()` per row would otherwise run once per page. A
dedicated test suite (`tests/integration/test_performance.py`) verifies
that the number of SQL queries doesn't grow with the size of the
dataset displayed — see that file for the pattern if you want to verify
another route.

A related pattern, not about query count but about repeated identical
queries within a single request: `SettingsService.get_default_timezone()`,
`get_shift_scheduling_mode()`/`get_oncall_scheduling_mode()`, and
`app/__init__.py`'s `get_date_format()`/`get_time_format()` cache
their resolved `Setting` lookup on `flask.g` for the lifetime of the
request — without it, rendering a page with many shifts/on-calls would
run one `Setting.get()` per row instead of one per request, since these
resolvers are called once per displayed item. The two scheduling-mode
getters were added by the configurable automation rules engine and
initially missed this pattern: `AdvancedShiftAutomation`/
`check_shift_rule_violations()` (`app/utils/helpers/common_helpers.py`)
call them once per day/per user inside a generation or validation loop
— caught and fixed as part of the 1.1.0 optimization pass.

**`AutomationRuleType.resolve()`** (`app/utils/automation/rules/base.py`
— the base class every rule type in `app/utils/automation/rules/`
inherits, so this one fix covers all of them) is cached the same way,
keyed by `(rule_type, group_id)`: `AdvancedShiftAutomation`'s shift-slot
resolution and mandatory/staffing-coverage checks call it once per
user/per day inside `generate_daily_shifts()`, and
`generate_full_schedule()` separately recomputes the same coverage gaps
`generate_daily_shifts()` already computed internally — without the
cache, a multi-week generation run issued one `AutomationRule` query
per rule *per day* instead of one per rule for the whole run. Fixed as
part of the 1.1.0 optimization pass (initially left as a known gap,
then addressed once the risk of the single-point base-class fix was
confirmed low - see `tests/integration/test_performance.py::
TestNPlusOneQueries::test_generate_full_schedule_query_count_stable_across_period_length`,
which asserts the query count stays bounded, not proportional to the
period length). `generate_full_schedule()`'s duplicate *computation*
of the same coverage gaps `generate_daily_shifts()` already computed
internally is a separate, much smaller concern now that the query cost
behind it is gone (it's cheap in-memory list/dict work over
already-fetched, session-identity-mapped rows) - not restructured, not
worth the risk of touching this generation loop's return-value contract
for a purely CPU-level saving. Composite index on
`AutomationRule(rule_type, group_id)` (migration `b8e2f4a91c6d`) was
added alongside the cache, since every real lookup filters on both
columns together.

## Database indexes

Composite indexes defined directly on the models (`app/models/*.py`), to
be preserved if you modify query patterns in `app/repositories/`:

| Table | Index |
|---|---|
| `Shift` | `(user_id, date)`, `(date, start_time)` |
| `OnCall` | `(user_id, start_time, end_time)` |
| `Leave` | `(user_id, start_date, end_date)` |
| `AutomationRule` | `(rule_type, group_id)` |

See [`architecture/ERD.md`](../architecture/ERD.md) for the full schema.

## Dashboard stats: Shift aggregated in SQL, OnCall/Leave stay in Python

`DashboardService.get_stats()` (`/dashboard`'s day-based total/this-month/
last-month counts) used to pull every shift/on-call/leave row a user
had ever had into Python — no date bound at all — and do the
month-boundary math there. Cost grew unbounded with a user's tenure: a
long-employed user's dashboard load did 3 full-history table scans on
every visit. Fixed for `Shift` (the dominant volume driver — one row
per person per work day, easily thousands over a few years, versus at
most ~52 `OnCall` rows/year and a handful of `Leave` rows/year):
`ShiftRepository.get_day_count_stats()` replaces
`list_dates_for_user()` + a Python loop with one SQL aggregate query
(`COUNT` + conditional `SUM`) — plain, portable SQL with no date
arithmetic, safe across all 3 supported engines (SQLite/PostgreSQL/
MySQL). See `tests/integration/test_performance.py::TestNPlusOneQueries::
test_dashboard_get_stats_query_count_stable_across_shift_count`.

**`OnCall`/`Leave` deliberately still compute in Python**, not pushed
into SQL: their "this month"/"last month" figures need each span's
duration *clipped* to the month window (`_clipped_duration_days()`/
`_clipped_days()` in `dashboard_service.py`), which requires either
per-row date/datetime arithmetic (`LEAST`/`GREATEST`-style clipping) or
engine-specific SQL — this app deliberately supports SQLite, PostgreSQL,
and MySQL (see CLAUDE.md's Database section), and this repo's test
suite only exercises SQLite, so shipping unverified cross-engine SQL
arithmetic here isn't a decision to make without a way to check it
against a real Postgres/MySQL instance. Given the low row count in
practice, the Python-side cost is not the same class of problem `Shift`
was. Revisit with real multi-engine test coverage if it ever becomes
one.

## Pagination

No advanced, environment-variable-configurable pagination system.
Paginated lists (`/schedule`, `/oncall`, `/leave`) directly use Flask-SQLAlchemy's
own pagination (`Query.paginate(page=, per_page=)`), with a fixed page
size choice on the route side (`5, 10, 25, 50, 100` or "show all").

## What doesn't exist (yet)

No active query caching, no frontend lazy loading (batch loading on
scroll), no built-in performance monitoring dashboard. For production
monitoring, see
[`app/utils/prometheus_metrics.py`](../../app/utils/prometheus_metrics.py)
(gated by `PROMETHEUS_ENABLED`, exposes `/metrics` in Prometheus format)
and [`app/utils/health.py`](../../app/utils/health.py) (`/health`,
`/ready`).
