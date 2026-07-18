# Performance optimization

This documents what actually exists in the code - there is no cache
system, no advanced pagination, and no lazy-loading system in this
application. Caching, if needed, is expected to be handled externally
(reverse proxy / dedicated cache), not by the app itself.

## Avoiding N+1: `eager_load`

The only decorator in `app/utils/optimizations/__init__.py` — loads one
or more SQLAlchemy relationships in a single query instead of N:

```python
from app.utils.optimizations import eager_load

@eager_load(Shift, ['user', 'shift_type'])
def get_shifts():
    return Shift.query...
```

Used in `app/routes/dashboard_routes.py` (home page) and in several
admin routes (`admin_user_routes.py`, `admin_group_routes.py`,
`admin_shift_type_routes.py`).

The repositories also use SQLAlchemy's `joinedload()` directly without
going through this decorator — see for example
`ShiftRepository.list_paginated()` in
`app/repositories/shift_repository.py`, which loads `user` and
`shift_type` in a single query. A dedicated test
(`tests/integration/test_performance.py`) verifies that the number of
SQL queries doesn't grow with the number of shifts displayed — see that
file for the method if you want to verify another route.

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
