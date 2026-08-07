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

**Known gap, not yet cached**: `AutomationRule.resolve_params()` (used
by every rule type in `app/utils/automation/rules/`) still hits the DB
on every call, with no `flask.g` cache — `AdvancedShiftAutomation`'s
shift-slot resolution and mandatory/staffing-coverage checks each
re-resolve the same rule once per user/per day inside `generate_daily_shifts()`,
and `generate_full_schedule()` separately recomputes the same coverage
gaps `generate_daily_shifts()` already computed internally. Both are
real, identified N+1/duplicate-work patterns in the rule-resolution
path, deliberately left unfixed in the 1.1.0 pass — they require
restructuring the generation loop itself (hoisting rule resolution
above the per-user/per-day loop), not just adding a cache, and that
code is dense enough (see the "real regression caught by..." comments
throughout `automation_admin_service.py`) to warrant its own dedicated
pass rather than a rushed pre-release change. Composite index on
`AutomationRule(rule_type, group_id)` (migration `b8e2f4a91c6d`) was
added regardless, since every real lookup filters on both columns
together.

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

## Dashboard stats: full history fetched into Python

`DashboardService.get_stats()` (`/dashboard`'s day-based total/this-month/
last-month counts) pulls every shift/on-call/leave row a user has ever
had via `ShiftRepository.list_dates_for_user()`/`OnCallRepository.list_spans_for_user()`/
`LeaveRepository.list_spans_for_user()` — no date bound at all — then
does the month-boundary math with Python loops over that full list.
Cost grows unbounded with a user's tenure: a long-employed user's
dashboard load does 3 full-history table scans on every visit instead
of DB-side aggregation (`func.count`/`func.sum` with a `CASE WHEN`/date
filter). Identified during the 1.1.0 optimization pass, deliberately
not rewritten in that pass — it would change the aggregation logic
this file's own straddle-a-month-boundary tests exercise closely, a
larger and riskier change than fits a pre-release cleanup. Revisit if
dashboard load time becomes a real complaint.

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
