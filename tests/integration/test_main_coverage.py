"""
Additional tests to improve coverage of app/routes/main.py
"""

from datetime import date, datetime, timedelta

from app.models import Leave, OnCall, Shift


class TestCalendarWindow:
    """Tests for the _calendar_window function."""

    def test_calendar_window_returns_tuple(self, test_app):
        """Test that _calendar_window returns a 2-date tuple."""
        with test_app.app_context():
            from app.services.schedule_service import ScheduleService

            start, end = ScheduleService.calendar_window()
            assert isinstance(start, datetime)
            assert isinstance(end, datetime)
            assert end > start

    def test_calendar_window_180_days(self, test_app):
        """Test that the calendar window spans 180 days."""
        with test_app.app_context():
            from app.services.schedule_service import (
                CALENDAR_WINDOW_DAYS,
                ScheduleService,
            )

            start, end = ScheduleService.calendar_window()
            now = datetime.now()
            expected_start = now - timedelta(days=CALENDAR_WINDOW_DAYS)
            expected_end = now + timedelta(days=CALENDAR_WINDOW_DAYS)
            # Check that the dates are close (within a few seconds)
            assert abs((start - expected_start).total_seconds()) < 10
            assert abs((end - expected_end).total_seconds()) < 10


class TestBuildCalendarEvents:
    """Tests for the _build_calendar_events function."""

    def test_build_calendar_events_empty(self, test_app):
        """Test that _build_calendar_events returns an empty list for empty inputs."""
        with test_app.app_context():
            from app.services.schedule_service import ScheduleService

            events = ScheduleService.build_calendar_events([], [], [], None)
            assert events == []

    def test_build_calendar_events_with_shift(
        self, test_app, test_user, test_shift_type
    ):
        """Test that _build_calendar_events creates events for shifts."""
        with test_app.app_context():
            from app.services.schedule_service import ScheduleService

            now = datetime.now()
            shift = Shift(
                user_id=test_user.id,
                shift_type_id=test_shift_type.id,
                start_time=now + timedelta(days=1),
                end_time=now + timedelta(days=1, hours=8),
                date=(now + timedelta(days=1)).date(),
                user=test_user,
                shift_type=test_shift_type,
            )
            events = ScheduleService.build_calendar_events([shift], [], [], test_user)
            assert len(events) == 1
            assert events[0]["className"] == "fc-event-shift"
            assert test_user.name in events[0]["title"]

    def test_build_calendar_events_with_oncall(self, test_app, test_user):
        """Test that _build_calendar_events creates events for on-calls."""
        with test_app.app_context():
            from app.services.schedule_service import ScheduleService

            now = datetime.now()
            oncall = OnCall(
                user_id=test_user.id,
                start_time=now + timedelta(days=1),
                end_time=now + timedelta(days=8),
                user=test_user,
            )
            events = ScheduleService.build_calendar_events([], [oncall], [], test_user)
            assert len(events) == 1
            assert events[0]["className"] == "fc-event-oncall"
            assert "Astreinte" in events[0]["title"]

    def test_build_calendar_events_with_leave(self, test_app, test_user):
        """Test that _build_calendar_events creates events for leaves."""
        with test_app.app_context():
            from app.services.schedule_service import ScheduleService

            leave = Leave(
                user_id=test_user.id,
                start_date=date.today() + timedelta(days=1),
                end_date=date.today() + timedelta(days=5),
                user=test_user,
            )
            events = ScheduleService.build_calendar_events([], [], [leave], test_user)
            assert len(events) == 1
            assert events[0]["className"] == "fc-event-leave"
            assert events[0]["allDay"] is True


class TestBuildCalendarEventsTimezoneConversion:
    """A shift stored at 09:00 (naive, meaning org default_timezone) must
    be translated to the viewer's own effective_timezone before being
    serialized - this is what makes the /profile/update timezone
    preference actually visible in the calendar (not just in ICS
    exports, which always stay in the org's canonical timezone)."""

    def test_shift_translated_to_viewer_timezone(
        self, test_app, test_user, test_shift_type
    ):
        with test_app.app_context():
            from app.services import ScheduleService, SettingsService

            SettingsService.set_default_timezone("Europe/Paris")
            test_user.timezone = "America/New_York"

            start_time = datetime(2024, 7, 1, 9, 0)  # summer: CEST = UTC+2
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

        # New York (EDT, UTC-4) is 6 hours behind Paris in summer: 09:00
        # Paris -> 03:00 New York, same instant.
        assert events[0]["start"] == "2024-07-01T03:00:00"

    def test_viewer_without_preference_sees_org_timezone(
        self, test_app, test_user, test_shift_type
    ):
        with test_app.app_context():
            from app.services import ScheduleService, SettingsService

            SettingsService.set_default_timezone("Europe/Paris")
            assert test_user.timezone is None

            start_time = datetime(2024, 7, 1, 9, 0)
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

        assert events[0]["start"] == "2024-07-01T09:00:00"


class TestIndexRoute:
    """Tests for the index route."""

    def test_index_route_returns_200(self, logged_in_client):
        """Test that the index route returns 200."""
        response = logged_in_client.get("/")
        assert response.status_code == 200

    def test_index_route_requires_login(self, client):
        """Test that the index route requires login."""
        response = client.get("/")
        assert response.status_code == 302


class TestScheduleRoute:
    """Tests for the schedule route."""

    def test_schedule_route_returns_200(self, logged_in_client):
        """Test that the schedule route returns 200."""
        response = logged_in_client.get("/schedule")
        assert response.status_code == 200

    def test_schedule_route_requires_login(self, client):
        """Test that the schedule route requires login."""
        response = client.get("/schedule")
        assert response.status_code == 302

    def test_schedule_route_with_pagination(self, logged_in_client):
        """Test that the schedule route handles pagination."""
        response = logged_in_client.get("/schedule?page=1&per_page=10")
        assert response.status_code == 200


class TestLeaveRoute:
    """Tests for the leave route."""

    def test_leave_route_returns_200(self, logged_in_client):
        """Test that the leave route returns 200."""
        response = logged_in_client.get("/leave")
        assert response.status_code == 200

    def test_leave_route_with_pagination(self, logged_in_client):
        """Test that the leave route handles pagination."""
        response = logged_in_client.get("/leave?page=1&per_page=10")
        assert response.status_code == 200


class TestOnCallRoute:
    """Tests for the oncall route."""

    def test_oncall_route_returns_200(self, logged_in_client):
        """Test that the oncall route returns 200."""
        response = logged_in_client.get("/oncall")
        assert response.status_code == 200

    def test_oncall_route_with_pagination(self, logged_in_client):
        """Test that the oncall route handles pagination."""
        response = logged_in_client.get("/oncall?page=1&per_page=10")
        assert response.status_code == 200


class TestAddLeaveRoute:
    """Tests for the add_leave route."""

    def test_add_leave_get_returns_200(self, logged_in_client):
        """Test that the add_leave route (GET) returns 200."""
        response = logged_in_client.get("/leave/add")
        assert response.status_code == 200

    def test_add_leave_post_missing_fields(self, logged_in_client):
        """Test that add_leave POST fails with missing fields."""
        response = logged_in_client.post("/leave/add", data={})
        assert response.status_code == 302

    def test_add_leave_post_invalid_dates(self, logged_in_client):
        """Test that add_leave POST fails with invalid dates."""
        response = logged_in_client.post(
            "/leave/add",
            data={
                "user_id": 1,
                "start_date": "invalid-date",
                "end_date": "invalid-date",
            },
        )
        assert response.status_code == 302


class TestAddOnCallRoute:
    """Tests for the add_oncall route."""

    def test_add_oncall_get_requires_admin(self, non_admin_client):
        """Test that add_oncall GET requires admin."""
        response = non_admin_client.get("/oncall/add")
        # 302 = redirect to login (not an admin)
        assert response.status_code in [302, 403]

    def test_add_oncall_post_missing_fields(self, logged_in_client):
        """Test that add_oncall POST fails with missing fields."""
        response = logged_in_client.post("/oncall/add", data={})
        # 302 = redirect with a flash message
        assert response.status_code == 302

    def test_add_oncall_post_invalid_date(self, logged_in_client):
        """Test that add_oncall POST fails with an invalid date."""
        response = logged_in_client.post(
            "/oncall/add", data={"user_id": 1, "start_date": "invalid-date"}
        )
        # 302 = redirect with a flash message
        assert response.status_code == 302


class TestAddShiftRoute:
    """Tests for the add_shift route."""

    def test_add_shift_get_requires_admin(self, non_admin_client):
        """Test that add_shift GET requires admin."""
        response = non_admin_client.get("/schedule/add")
        # 302 = redirect to login (not an admin)
        assert response.status_code in [302, 403]

    def test_add_shift_post_missing_fields(self, logged_in_client):
        """Test that add_shift POST fails with missing fields."""
        response = logged_in_client.post("/schedule/add", data={})
        # 302 = redirect with a flash message
        assert response.status_code == 302


class TestDeleteRoutes:
    """Tests for the delete routes."""

    def test_delete_shift_requires_admin(self, logged_in_client, test_shift):
        """Test that delete_shift requires admin."""
        response = logged_in_client.post(f"/schedule/delete/{test_shift.id}")
        # 302 = redirect to login (not an admin)
        assert response.status_code in [302, 403]

    def test_delete_leave_requires_ownership(
        self, logged_in_client, test_leave, test_user
    ):
        """Test that delete_leave checks ownership."""
        # test_leave belongs to test_user, logged_in_client is test_user
        response = logged_in_client.post(f"/leave/delete/{test_leave.id}")
        # 302 = redirect after deletion
        assert response.status_code == 302

    def test_delete_oncall_requires_admin(self, logged_in_client, test_oncall):
        """Test that delete_oncall requires admin."""
        response = logged_in_client.post(f"/oncall/delete/{test_oncall.id}")
        # 302 = redirect to login (not an admin)
        assert response.status_code in [302, 403]


class TestAPIEndpoints:
    """Tests for the API endpoints."""

    def test_api_get_shifts_returns_json(self, logged_in_client):
        """Test that /api/shifts returns JSON."""
        response = logged_in_client.get("/api/shifts")
        assert response.status_code == 200
        assert response.content_type == "application/json"

    def test_api_get_users_returns_json(self, logged_in_client):
        """Test that /api/users returns JSON."""
        response = logged_in_client.get("/api/users")
        assert response.status_code == 200
        assert response.content_type == "application/json"

    def test_api_get_shift_types_returns_json(self, logged_in_client):
        """Test that /api/shift-types returns JSON."""
        response = logged_in_client.get("/api/shift-types")
        assert response.status_code == 200
        assert response.content_type == "application/json"

    def test_api_create_shift_requires_admin(self, non_admin_client):
        """Test that POST /api/shifts requires admin."""
        response = non_admin_client.post("/api/shifts", json={})
        # 302 = redirect to login (not an admin)
        assert response.status_code in [302, 403]

    def test_api_update_shift_requires_admin(self, non_admin_client):
        """Test that PATCH /api/shifts/<id> requires admin."""
        response = non_admin_client.patch("/api/shifts/1", json={})
        # 302 = redirect to login (not an admin)
        assert response.status_code in [302, 403]

    def test_api_delete_shift_requires_admin(self, non_admin_client):
        """Test that DELETE /api/shifts/<id> requires admin."""
        response = non_admin_client.delete("/api/shifts/1")
        # 302 = redirect to login (not an admin)
        assert response.status_code in [302, 403]
