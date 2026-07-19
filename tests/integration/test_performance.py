"""
Performance tests for Kairos.

Two deliberately modest angles (no real profiling/benchmarking tool in
place):
1. Response time: wide thresholds to catch a gross regression (a route
   that suddenly takes 10x longer), not a precise micro-benchmark -
   pointless on a shared dev machine.
2. SQL query count: the repositories use joinedload() to avoid N+1
   (e.g. ShiftRepository.list_paginated loads user + shift_type in one
   query). These tests check that the query count doesn't grow linearly
   with the number of records - that's what would actually catch a real
   performance regression here, unlike a wall-clock timer that varies
   too much depending on the machine.
"""

import time
from contextlib import contextmanager
from datetime import date, datetime, timedelta

from sqlalchemy import event

from app import compress, create_app, db
from app.models import Shift, ShiftType, SwapRequest, User


@contextmanager
def count_queries():
    """Count the SQL queries executed inside the `with` block."""
    queries = []

    def _on_execute(conn, cursor, statement, parameters, context, executemany):
        queries.append(statement)

    engine = db.engine
    event.listen(engine, "before_cursor_execute", _on_execute)
    try:
        yield queries
    finally:
        event.remove(engine, "before_cursor_execute", _on_execute)


def _seed_shifts(group, count, offset=0):
    shift_type = ShiftType(
        name=f"perf-{offset}-{count}", label="Perf", start_hour=7, end_hour=15
    )
    db.session.add(shift_type)
    db.session.flush()

    users = []
    for i in range(offset, offset + count):
        user = User(name=f"Perf User {i}", email=f"perf{i}@test.com", group_id=group.id)
        user.set_password("pw")
        db.session.add(user)
        users.append(user)
    db.session.flush()

    start = date.today()
    for i, user in enumerate(users):
        on_date = start + timedelta(days=i % 5)
        db.session.add(
            Shift(
                date=on_date,
                start_time=datetime.combine(on_date, datetime.min.time()),
                end_time=datetime.combine(on_date, datetime.min.time())
                + timedelta(hours=8),
                user_id=user.id,
                shift_type_id=shift_type.id,
            )
        )
    db.session.commit()


class TestResponseTime:
    """Wide thresholds - catches a gross regression, not a micro-benchmark."""

    def test_schedule_route_responds_quickly(
        self, test_app, test_group, logged_in_client
    ):
        with logged_in_client.application.app_context():
            _seed_shifts(test_group, 30)

        start = time.monotonic()
        resp = logged_in_client.get("/schedule?per_page=50")
        elapsed = time.monotonic() - start

        assert resp.status_code == 200
        assert elapsed < 2.0, f"/schedule took {elapsed:.2f}s (2s threshold)"

    def test_dashboard_route_responds_quickly(self, test_app, logged_in_client):
        start = time.monotonic()
        resp = logged_in_client.get("/dashboard")
        elapsed = time.monotonic() - start

        assert resp.status_code == 200
        assert elapsed < 2.0, f"/dashboard took {elapsed:.2f}s (2s threshold)"


class TestCompression:
    """Regression test: flask-compress was a declared dependency but
    Compress(app) was never actually called anywhere - so compression
    never did anything in practice. Compress is now initialized in
    create_app() (except in TESTING, since the test client doesn't
    decode Content-Encoding and resp.data must stay plain text for the
    other tests) - these two tests therefore build their own app with
    Compress manually re-enabled, the same way secure_app already does
    for Talisman."""

    def test_response_is_gzip_compressed_when_accepted(self):
        app = create_app("app.config.TestingConfig")
        compress.init_app(app)
        with app.app_context():
            db.drop_all()
            db.create_all()
        client = app.test_client()
        resp = client.get("/login", headers={"Accept-Encoding": "gzip"})
        assert resp.status_code == 200
        assert resp.headers.get("Content-Encoding") == "gzip"
        with app.app_context():
            db.drop_all()

    def test_response_not_compressed_without_accept_encoding(self):
        app = create_app("app.config.TestingConfig")
        compress.init_app(app)
        with app.app_context():
            db.drop_all()
            db.create_all()
        client = app.test_client()
        resp = client.get("/login", headers={"Accept-Encoding": "identity"})
        assert resp.status_code == 200
        assert "Content-Encoding" not in resp.headers
        with app.app_context():
            db.drop_all()


class TestNPlusOneQueries:
    """The SQL query count must not grow linearly with the number of
    listed records (otherwise joinedload() isn't doing its job anymore)."""

    def test_schedule_query_count_stable_across_dataset_size(
        self, test_app, test_group, logged_in_client
    ):
        with logged_in_client.application.app_context():
            _seed_shifts(test_group, 5)
        with count_queries() as small_queries:
            resp_small = logged_in_client.get("/schedule?per_page=50")
        assert resp_small.status_code == 200

        with logged_in_client.application.app_context():
            _seed_shifts(test_group, 25, offset=100)
        with count_queries() as big_queries:
            resp_big = logged_in_client.get("/schedule?per_page=50")
        assert resp_big.status_code == 200

        # An N+1 regression would grow the query count roughly
        # proportionally to the number of shifts shown (30 here). With
        # joinedload(), the gap must stay small (a margin of 5 for
        # incidental pagination/count queries).
        assert len(big_queries) <= len(small_queries) + 5, (
            f"{len(small_queries)} queries for 5 shifts, "
            f"{len(big_queries)} for 25 additional shifts - "
            "possible N+1 (broken joinedload?)"
        )

    def test_calendar_api_query_count_stable_across_dataset_size(
        self, test_app, test_group, logged_in_client
    ):
        """Regression guard: ScheduleService.build_calendar_events()
        calls to_viewer_timezone() twice per shift/on-call (start+end),
        which used to re-resolve SettingsService.get_default_timezone()
        via an uncached Setting.get() on every single call - a real N+1
        on the calendar's own hot path (/, /api/shifts). Fixed by
        caching the resolved timezone on flask.g for the request (see
        SettingsService.get_default_timezone())."""
        with logged_in_client.application.app_context():
            _seed_shifts(test_group, 5)
        with count_queries() as small_queries:
            resp_small = logged_in_client.get("/api/shifts")
        assert resp_small.status_code == 200

        with logged_in_client.application.app_context():
            _seed_shifts(test_group, 25, offset=200)
        with count_queries() as big_queries:
            resp_big = logged_in_client.get("/api/shifts")
        assert resp_big.status_code == 200

        assert len(big_queries) <= len(small_queries) + 5, (
            f"{len(small_queries)} queries for 5 shifts, "
            f"{len(big_queries)} for 25 additional shifts - "
            "possible N+1 (timezone resolution not cached?)"
        )

    def test_shift_repository_list_paginated_uses_eager_load(
        self, test_app, test_group
    ):
        _seed_shifts(test_group, 10)

        from app.repositories.shift_repository import ShiftRepository

        with count_queries() as queries:
            paginated = ShiftRepository.list_paginated(1, 50)
            # Accessing the relationships must trigger NO additional
            # query if the joinedload worked.
            for shift in paginated.items:
                _ = shift.user.name
                _ = shift.shift_type.label

        assert len(queries) <= 3, (
            f"{len(queries)} queries to list 10 shifts with their "
            "relationships - joinedload doesn't seem to be working"
        )

    def _seed_swap_requests(self, group, shift_type, count, offset=0):
        """Create `count` SwapRequest rows, each with its own
        requester/target_user/shift - no sharing across rows, so the
        bulk preload is genuinely put to the test."""
        on_date = date.today() + timedelta(days=3)
        while on_date.weekday() >= 5:
            on_date += timedelta(days=1)

        for i in range(offset, offset + count):
            requester = User(
                name=f"Swap Requester {i}",
                email=f"swap-req-{i}@test.com",
                group_id=group.id,
            )
            requester.set_password("pw")
            target = User(
                name=f"Swap Target {i}",
                email=f"swap-target-{i}@test.com",
                group_id=group.id,
            )
            target.set_password("pw")
            db.session.add_all([requester, target])
            db.session.flush()

            shift = Shift(
                date=on_date,
                start_time=datetime.combine(on_date, datetime.min.time()),
                end_time=datetime.combine(on_date, datetime.min.time())
                + timedelta(hours=8),
                user_id=requester.id,
                shift_type_id=shift_type.id,
            )
            db.session.add(shift)
            db.session.flush()

            db.session.add(
                SwapRequest(
                    requester_id=requester.id,
                    shift_id=shift.id,
                    target_user_id=target.id,
                    status=SwapRequest.PENDING,
                )
            )
        db.session.commit()

    def test_swap_request_repository_preloads_related_rows(self, test_app, test_group):
        """Regression test: SwapRequest has no db.relationship() (see
        app/models/swap_request.py) - without SwapRequestRepository's
        bulk preload (_preload_related), accessing
        requester/target_user/shift on each row would cost 3 extra
        queries per row, making the total grow proportionally to the
        number of listed requests."""
        shift_type = ShiftType(
            name="swap-perf", label="Perf", start_hour=7, end_hour=15
        )
        db.session.add(shift_type)
        db.session.flush()

        self._seed_swap_requests(test_group, shift_type, 3)
        with count_queries() as small_queries:
            from app.repositories.swap_request_repository import (
                SwapRequestRepository,
            )

            pending = SwapRequestRepository.list_pending()
            for sr in pending:
                _ = sr.requester.name
                _ = sr.target_user.name
                _ = sr.shift.date

        self._seed_swap_requests(test_group, shift_type, 15, offset=100)
        with count_queries() as big_queries:
            from app.repositories.swap_request_repository import (
                SwapRequestRepository,
            )

            pending = SwapRequestRepository.list_pending()
            for sr in pending:
                _ = sr.requester.name
                _ = sr.target_user.name
                _ = sr.shift.date

        # 18 more requests (15 vs 3) should only add a handful of bulk
        # queries, not ~54 individual queries (3 per row).
        assert len(big_queries) <= len(small_queries) + 5, (
            f"{len(small_queries)} queries for 3 requests, "
            f"{len(big_queries)} for 18 additional requests - "
            "possible N+1 (broken preload?)"
        )

    def test_list_for_user_repositories_preload_the_user_relationship(
        self, test_app, test_group, test_user, test_shift_type
    ):
        """Regression guard: ShiftRepository/OnCallRepository/
        LeaveRepository's list_for_user() used to load rows without
        joinedload(<Model>.user) - harmless for the current callers
        (they already hold the same User object, so SQLAlchemy's
        identity map absorbs the lookup) but a latent N+1 trap for any
        future caller iterating rows and reading .user. Now eager-loaded
        like every other list_* method in these repositories."""
        from app.models import Leave, OnCall
        from app.repositories.leave_repository import LeaveRepository
        from app.repositories.oncall_repository import OnCallRepository
        from app.repositories.shift_repository import ShiftRepository

        on_date = date.today() + timedelta(days=3)
        while on_date.weekday() >= 5:
            on_date += timedelta(days=1)
        db.session.add(
            Shift(
                date=on_date,
                start_time=datetime.combine(on_date, datetime.min.time()),
                end_time=datetime.combine(on_date, datetime.min.time())
                + timedelta(hours=8),
                user_id=test_user.id,
                shift_type_id=test_shift_type.id,
            )
        )
        db.session.add(
            OnCall(
                user_id=test_user.id,
                start_time=datetime.combine(on_date, datetime.min.time()),
                end_time=datetime.combine(on_date, datetime.min.time())
                + timedelta(days=7),
            )
        )
        db.session.add(
            Leave(user_id=test_user.id, start_date=on_date, end_date=on_date)
        )
        db.session.commit()
        # Capture the id before expiring: test_user is itself a
        # session-attached object, so expire_all() would otherwise make
        # the `.id` access below issue its own refresh SELECT, polluting
        # the query count this test is trying to measure.
        user_id = test_user.id
        db.session.expire_all()

        with count_queries() as queries:
            for shift in ShiftRepository.list_for_user(user_id):
                _ = shift.user.name
        assert len(queries) == 1, "ShiftRepository.list_for_user: expected joinedload"

        db.session.expire_all()
        with count_queries() as queries:
            for oncall in OnCallRepository.list_for_user(user_id):
                _ = oncall.user.name
        assert len(queries) == 1, "OnCallRepository.list_for_user: expected joinedload"

        db.session.expire_all()
        with count_queries() as queries:
            for leave in LeaveRepository.list_for_user(user_id):
                _ = leave.user.name
        assert len(queries) == 1, "LeaveRepository.list_for_user: expected joinedload"

    def test_generate_oncall_schedule_query_count_stable_across_period_length(
        self, test_app, test_group, test_user, second_user
    ):
        """Regression test: before AvailabilityIndex (see
        app/utils/automation/oncall_automation.py), find_next_available_user
        and check_oncall_constraint queried the database for every
        candidate tested for every week (up to 3 queries/candidate) - a
        several-month generation climbed to 1500+ queries."""
        from app.utils.automation import OnCallAutomation

        start_date = date(2024, 1, 5)  # Friday

        with count_queries() as short_queries:
            oncalls_short, _, _u1 = OnCallAutomation.generate_oncall_schedule(
                start_date, start_date + timedelta(days=28), dry_run=True
            )
        assert len(oncalls_short) > 0

        with count_queries() as long_queries:
            oncalls_long, _, _u2 = OnCallAutomation.generate_oncall_schedule(
                start_date, start_date + timedelta(days=180), dry_run=True
            )
        assert len(oncalls_long) > len(oncalls_short)

        # ~26 more weeks (180 vs 28 days) shouldn't add queries
        # proportional to the number of weeks - just the bulk preload
        # (bounded by the number of eligible users).
        assert len(long_queries) <= len(short_queries) + 5, (
            f"{len(short_queries)} queries for {len(oncalls_short)} on-calls, "
            f"{len(long_queries)} for {len(oncalls_long)} on-calls - "
            "possible N+1 (broken AvailabilityIndex?)"
        )

    def test_audit_log_repository_preloads_actor(self, test_app, test_group):
        """AuditLog.actor is a plain @property (see app/models/audit_log.py),
        not a real relationship - AuditLogRepository.list_paginated()
        must bulk-preload it (same idea as SwapRequestRepository) or
        /admin/audit-log's `entry.actor.name` triggers one query per
        distinct actor on the page."""
        from app.repositories.audit_log_repository import AuditLogRepository

        users = []
        for i in range(10):
            user = User(
                name=f"Audit Actor {i}",
                email=f"audit-actor-{i}@test.com",
                group_id=test_group.id,
            )
            user.set_password("pw")
            db.session.add(user)
            users.append(user)
        db.session.flush()

        for user in users:
            AuditLogRepository.create(actor_id=user.id, action="shift.create")
        db.session.commit()

        db.session.expire_all()
        with count_queries() as queries:
            page = AuditLogRepository.list_paginated(page=1, per_page=50)
            for entry in page.items:
                _ = entry.actor.name

        assert len(queries) <= 3, (
            f"{len(queries)} queries to list 10 audit log entries with "
            "distinct actors - actor preload doesn't seem to be working"
        )
