"""
Priority tests for main.py.
"""

from datetime import datetime, timedelta

from app import db
from app.models import OnCall, Shift, User


class TestDeleteAllShifts:
    """Tests for /shift/delete-all."""

    def test_delete_all_shifts(self, logged_in_client, test_shift):
        """Test deleting all shifts."""
        initial_count = Shift.query.count()
        assert initial_count > 0

        response = logged_in_client.post("/shift/delete-all", follow_redirects=True)
        assert response.status_code == 200
        assert Shift.query.count() == 0


class TestDeleteAllShiftsForUser:
    """Tests for /shift/delete-all-for-user/<user_id>."""

    def test_delete_all_shifts_for_user(
        self, logged_in_client, test_user, test_shift_type
    ):
        """Test deleting all shifts for a user."""
        # Create shifts
        for i in range(3):
            start_time = datetime.now() + timedelta(days=i + 1)
            shift = Shift(
                user_id=test_user.id,
                shift_type_id=test_shift_type.id,
                start_time=start_time,
                end_time=start_time + timedelta(hours=8),
                date=start_time.date(),
            )
            db.session.add(shift)
        db.session.commit()

        response = logged_in_client.post(
            f"/shift/delete-all-for-user/{test_user.id}",
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert Shift.query.filter_by(user_id=test_user.id).count() == 0


class TestDeleteAllShiftsForDay:
    """Tests for /shift/delete-day/<date_str>."""

    def test_delete_all_shifts_for_day(
        self, logged_in_client, test_user, test_shift_type
    ):
        """Test deleting all shifts for a day."""
        today = datetime.now().date()
        # Create shifts for today, one per user - uq_shift_user_date
        # allows at most one shift per (user, date), so this needs 3
        # distinct users rather than 3 shifts for the same one.
        users = [test_user]
        for i in range(2):
            other = User(
                name=f"Day User {i}",
                email=f"day-user-{i}@test.com",
                group_id=test_user.group_id,
            )
            other.set_password("pw")
            db.session.add(other)
            users.append(other)
        db.session.commit()

        for i, user in enumerate(users):
            start_time = datetime.combine(today, datetime.min.time()).replace(
                hour=9 + i * 2
            )
            shift = Shift(
                user_id=user.id,
                shift_type_id=test_shift_type.id,
                start_time=start_time,
                end_time=start_time + timedelta(hours=8),
                date=today,
            )
            db.session.add(shift)
        db.session.commit()

        response = logged_in_client.post(
            f"/shift/delete-day/{today.strftime('%Y-%m-%d')}",
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert Shift.query.filter_by(date=today).count() == 0


class TestDeleteAllShiftsForWeek:
    """Tests for /shift/delete-week/<date_str>."""

    def test_delete_all_shifts_for_week(
        self, logged_in_client, test_user, test_shift_type
    ):
        """Test deleting all shifts for a week."""
        today = datetime.now().date()
        monday = today - timedelta(days=today.weekday())

        # Create shifts for the week
        for day in range(5):
            current_date = monday + timedelta(days=day)
            start_time = datetime.combine(current_date, datetime.min.time()).replace(
                hour=9
            )
            shift = Shift(
                user_id=test_user.id,
                shift_type_id=test_shift_type.id,
                start_time=start_time,
                end_time=start_time + timedelta(hours=8),
                date=current_date,
            )
            db.session.add(shift)
        db.session.commit()

        response = logged_in_client.post(
            f"/shift/delete-week/{monday.strftime('%Y-%m-%d')}",
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert (
            Shift.query.filter(
                Shift.date >= monday, Shift.date <= monday + timedelta(days=4)
            ).count()
            == 0
        )


class TestDeleteAllOnCalls:
    """Tests for /oncall/delete-all."""

    def test_delete_all_oncalls(self, logged_in_client, test_oncall):
        """Test deleting all on-calls."""
        initial_count = OnCall.query.count()
        assert initial_count > 0

        response = logged_in_client.post("/oncall/delete-all", follow_redirects=True)
        assert response.status_code == 200
        assert OnCall.query.count() == 0


class TestDeleteAllOnCallsForUser:
    """Tests for /oncall/delete-all-for-user/<user_id>."""

    def test_delete_all_oncalls_for_user(self, logged_in_client, test_user):
        """Test deleting all on-calls for a user."""
        # Create on-calls
        for i in range(3):
            now = datetime.now()
            days_until_friday = (4 - now.weekday() + i * 7) % 7
            start_time = datetime.combine(now.date(), datetime.min.time()).replace(
                hour=21
            ) + timedelta(days=days_until_friday + i * 7)
            end_time = start_time + timedelta(days=7, hours=-14)

            oncall = OnCall(
                user_id=test_user.id, start_time=start_time, end_time=end_time
            )
            db.session.add(oncall)
        db.session.commit()

        response = logged_in_client.post(
            f"/oncall/delete-all-for-user/{test_user.id}",
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert OnCall.query.filter_by(user_id=test_user.id).count() == 0


class TestCalendarFunctions:
    """Tests for the calendar utility functions."""

    def test_calendar_window(self, test_app):
        """Test _calendar_window."""
        from app.services.schedule_service import CALENDAR_WINDOW_DAYS, ScheduleService

        start, end = ScheduleService.calendar_window()
        assert isinstance(start, datetime)
        assert isinstance(end, datetime)

        now = datetime.now()
        expected_start = now - timedelta(days=CALENDAR_WINDOW_DAYS)
        expected_end = now + timedelta(days=CALENDAR_WINDOW_DAYS)

        assert abs((start - expected_start).total_seconds()) < 10
        assert abs((end - expected_end).total_seconds()) < 10

    def test_build_calendar_events_empty(self, test_app):
        """Test _build_calendar_events with empty lists."""
        from app.services.schedule_service import ScheduleService

        events = ScheduleService.build_calendar_events([], [], [], None)
        assert events == []

    def test_build_calendar_events_with_data(
        self, test_app, test_user, test_shift_type
    ):
        """Test _build_calendar_events with data."""
        from app.services.schedule_service import ScheduleService

        start_time = datetime.now() + timedelta(days=1)
        # no_autoflush: shift is a transient object (never added to the
        # session) but user=/shift_type= set the relationship backref on
        # test_user/test_shift_type, which are session-bound - any query
        # run afterward (build_calendar_events() queries Setting
        # internally) triggers autoflush against that dangling
        # relationship state and raises a SAWarning. Wrap the whole
        # sequence, not just the construction.
        with db.session.no_autoflush:
            shift = Shift(
                user_id=test_user.id,
                shift_type_id=test_shift_type.id,
                start_time=start_time,
                end_time=start_time + timedelta(hours=8),
                date=start_time.date(),
                user=test_user,
                shift_type=test_shift_type,
            )

            events = ScheduleService.build_calendar_events([shift], [], [], test_user)

        assert len(events) == 1
        assert events[0]["title"] == f"{test_user.name} - {test_shift_type.label}"
