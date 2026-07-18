# Performance optimization

> Fully rewritten in Phase 5 (2026-07). The previous version (1397 lines)
> documented in detail three systems that no longer exist in the code:
> advanced pagination (`app/utils/pagination/`), lazy loading
> (`app/utils/lazy_loading.py`, 785 lines), and a performance monitoring
> module (`PerformanceMonitor`) which — according to the audit conducted
> in Phase 4 — **never actually existed**: the `measure_time` decorator
> that claimed to use it imported a module (`app.utils.performance_monitor`)
> that could not be found, proof it had never run. All three were removed
> as confirmed dead code in Phase 4 (see `report/Phase 4: AMÉLIORATION
> DES TESTS.md`). What follows only documents what actually remains in
> the code.

## Cache

`app/utils/cache/` provides a simple application-level cache,
unconditionally initialized at startup (`init_cache(app)` in
`app/__init__.py`).

```bash
# .env
CACHE_TYPE=simple   # or redis
CACHE_DEFAULT_TIMEOUT=300
CACHE_REDIS_URL=redis://localhost:6379/0   # if CACHE_TYPE=redis
```

- `simple`: `flask_caching.backends.SimpleCache` if `Flask-Caching` is
  installed, otherwise an automatic fallback to `SimpleDictCache`
  (`app/utils/cache/cache_manager.py`) — a minimal in-memory dictionary
  cache, visible in the logs
  (`Flask-Caching not available, using simple dictionary cache`).
- `redis`: `flask_caching.backends.RedisCache`, requires `Flask-Caching`
  installed and a reachable Redis server.

The cache is initialized but **nothing in the current code actively uses
it** (no route or service calls `get_cache()` to read/write an entry) —
the decorators that used to exploit it (`cached_route`, `cache_result`)
were removed in Phase 4 as dead code (zero callers, and their import
`from app.utils.cache import cache` never actually matched a real export
of the module anyway). This is infrastructure ready to be reconnected if
a real application-caching need arises, not an optimization currently in
service.

## Avoiding N+1: `eager_load`

The only decorator remaining in `app/utils/optimizations/__init__.py`
(reduced from 14 decorators down to 1 in Phase 4, see the same report) —
loads one or more SQLAlchemy relationships in a single query instead of
N:

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

No advanced, environment-variable-configurable pagination system
(contrary to what the previous version of this file documented). Paginated
lists (`/schedule`, `/oncall`, `/leave`) directly use Flask-SQLAlchemy's
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
