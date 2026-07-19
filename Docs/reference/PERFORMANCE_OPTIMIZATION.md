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
queries within a single request: `SettingsService.get_default_timezone()`
and `app/__init__.py`'s `get_date_format()`/`get_time_format()` cache
their resolved `Setting` lookup on `flask.g` for the lifetime of the
request — without it, rendering a page with many shifts/on-calls would
run one `Setting.get()` per row instead of one per request, since these
resolvers are called once per displayed item.

## Database indexes

Composite indexes defined directly on the models (`app/models/*.py`), to
be preserved if you modify query patterns in `app/repositories/`:

| Table | Index |
|---|---|
| `Shift` | `(user_id, date)`, `(date, start_time)` |
| `OnCall` | `(user_id, start_time, end_time)` |
| `Leave` | `(user_id, start_date, end_date)` |

See [`architecture/ERD.md`](../architecture/ERD.md) for the full schema.

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
