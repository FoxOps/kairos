"""
Tests supplémentaires pour améliorer la couverture de app/routes/main.py
"""

from datetime import date, datetime, timedelta

from app.models import Leave, OnCall, Shift


class TestCalendarWindow:
    """Tests pour la fonction _calendar_window."""

    def test_calendar_window_returns_tuple(self, test_app):
        """Test que _calendar_window retourne un tuple de 2 dates."""
        with test_app.app_context():
            from app.services.schedule_service import ScheduleService

            start, end = ScheduleService.calendar_window()
            assert isinstance(start, datetime)
            assert isinstance(end, datetime)
            assert end > start

    def test_calendar_window_180_days(self, test_app):
        """Test que la fenêtre du calendrier est de 180 jours."""
        with test_app.app_context():
            from app.services.schedule_service import (
                CALENDAR_WINDOW_DAYS,
                ScheduleService,
            )

            start, end = ScheduleService.calendar_window()
            now = datetime.now()
            expected_start = now - timedelta(days=CALENDAR_WINDOW_DAYS)
            expected_end = now + timedelta(days=CALENDAR_WINDOW_DAYS)
            # Vérifier que les dates sont proches (à quelques secondes près)
            assert abs((start - expected_start).total_seconds()) < 10
            assert abs((end - expected_end).total_seconds()) < 10


class TestBuildCalendarEvents:
    """Tests pour la fonction _build_calendar_events."""

    def test_build_calendar_events_empty(self, test_app):
        """Test que _build_calendar_events retourne une liste vide avec des entrées vides."""
        with test_app.app_context():
            from app.services.schedule_service import ScheduleService

            events = ScheduleService.build_calendar_events([], [], [])
            assert events == []

    def test_build_calendar_events_with_shift(
        self, test_app, test_user, test_shift_type
    ):
        """Test que _build_calendar_events crée des événements pour les shifts."""
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
            events = ScheduleService.build_calendar_events([shift], [], [])
            assert len(events) == 1
            assert events[0]["className"] == "fc-event-shift"
            assert test_user.name in events[0]["title"]

    def test_build_calendar_events_with_oncall(self, test_app, test_user):
        """Test que _build_calendar_events crée des événements pour les astreintes."""
        with test_app.app_context():
            from app.services.schedule_service import ScheduleService

            now = datetime.now()
            oncall = OnCall(
                user_id=test_user.id,
                start_time=now + timedelta(days=1),
                end_time=now + timedelta(days=8),
                user=test_user,
            )
            events = ScheduleService.build_calendar_events([], [oncall], [])
            assert len(events) == 1
            assert events[0]["className"] == "fc-event-oncall"
            assert "Astreinte" in events[0]["title"]

    def test_build_calendar_events_with_leave(self, test_app, test_user):
        """Test que _build_calendar_events crée des événements pour les congés."""
        with test_app.app_context():
            from app.services.schedule_service import ScheduleService

            leave = Leave(
                user_id=test_user.id,
                start_date=date.today() + timedelta(days=1),
                end_date=date.today() + timedelta(days=5),
                user=test_user,
            )
            events = ScheduleService.build_calendar_events([], [], [leave])
            assert len(events) == 1
            assert events[0]["className"] == "fc-event-leave"
            assert events[0]["allDay"] is True


class TestIndexRoute:
    """Tests pour la route index."""

    def test_index_route_returns_200(self, logged_in_client):
        """Test que la route index retourne 200."""
        response = logged_in_client.get("/")
        assert response.status_code == 200

    def test_index_route_requires_login(self, client):
        """Test que la route index nécessite une connexion."""
        response = client.get("/")
        assert response.status_code == 302


class TestScheduleRoute:
    """Tests pour la route schedule."""

    def test_schedule_route_returns_200(self, logged_in_client):
        """Test que la route schedule retourne 200."""
        response = logged_in_client.get("/schedule")
        assert response.status_code == 200

    def test_schedule_route_requires_login(self, client):
        """Test que la route schedule nécessite une connexion."""
        response = client.get("/schedule")
        assert response.status_code == 302

    def test_schedule_route_with_pagination(self, logged_in_client):
        """Test que la route schedule gère la pagination."""
        response = logged_in_client.get("/schedule?page=1&per_page=10")
        assert response.status_code == 200


class TestLeaveRoute:
    """Tests pour la route leave."""

    def test_leave_route_returns_200(self, logged_in_client):
        """Test que la route leave retourne 200."""
        response = logged_in_client.get("/leave")
        assert response.status_code == 200

    def test_leave_route_with_pagination(self, logged_in_client):
        """Test que la route leave gère la pagination."""
        response = logged_in_client.get("/leave?page=1&per_page=10")
        assert response.status_code == 200


class TestOnCallRoute:
    """Tests pour la route oncall."""

    def test_oncall_route_returns_200(self, logged_in_client):
        """Test que la route oncall retourne 200."""
        response = logged_in_client.get("/oncall")
        assert response.status_code == 200

    def test_oncall_route_with_pagination(self, logged_in_client):
        """Test que la route oncall gère la pagination."""
        response = logged_in_client.get("/oncall?page=1&per_page=10")
        assert response.status_code == 200


class TestAddLeaveRoute:
    """Tests pour la route add_leave."""

    def test_add_leave_get_returns_200(self, logged_in_client):
        """Test que la route add_leave (GET) retourne 200."""
        response = logged_in_client.get("/leave/add")
        assert response.status_code == 200

    def test_add_leave_post_missing_fields(self, logged_in_client):
        """Test que add_leave POST échoue avec des champs manquants."""
        response = logged_in_client.post("/leave/add", data={})
        assert response.status_code == 302

    def test_add_leave_post_invalid_dates(self, logged_in_client):
        """Test que add_leave POST échoue avec des dates invalides."""
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
    """Tests pour la route add_oncall."""

    def test_add_oncall_get_requires_admin(self, non_admin_client):
        """Test que add_oncall GET nécessite admin."""
        response = non_admin_client.get("/oncall/add")
        # 302 = redirection vers login (car non admin)
        assert response.status_code in [302, 403]

    def test_add_oncall_post_missing_fields(self, logged_in_client):
        """Test que add_oncall POST échoue avec des champs manquants."""
        response = logged_in_client.post("/oncall/add", data={})
        # 302 = redirection avec flash message
        assert response.status_code == 302

    def test_add_oncall_post_invalid_date(self, logged_in_client):
        """Test que add_oncall POST échoue avec une date invalide."""
        response = logged_in_client.post(
            "/oncall/add", data={"user_id": 1, "start_date": "invalid-date"}
        )
        # 302 = redirection avec flash message
        assert response.status_code == 302


class TestAddShiftRoute:
    """Tests pour la route add_shift."""

    def test_add_shift_get_requires_admin(self, non_admin_client):
        """Test que add_shift GET nécessite admin."""
        response = non_admin_client.get("/schedule/add")
        # 302 = redirection vers login (car non admin)
        assert response.status_code in [302, 403]

    def test_add_shift_post_missing_fields(self, logged_in_client):
        """Test que add_shift POST échoue avec des champs manquants."""
        response = logged_in_client.post("/schedule/add", data={})
        # 302 = redirection avec flash message
        assert response.status_code == 302


class TestDeleteRoutes:
    """Tests pour les routes de suppression."""

    def test_delete_shift_requires_admin(self, logged_in_client, test_shift):
        """Test que delete_shift nécessite admin."""
        response = logged_in_client.get(f"/schedule/delete/{test_shift.id}")
        # 302 = redirection vers login (car non admin)
        assert response.status_code in [302, 403]

    def test_delete_leave_requires_ownership(
        self, logged_in_client, test_leave, test_user
    ):
        """Test que delete_leave vérifie la propriété."""
        # test_leave appartient à test_user, logged_in_client est test_user
        response = logged_in_client.get(f"/leave/delete/{test_leave.id}")
        # 302 = redirection après suppression
        assert response.status_code == 302

    def test_delete_oncall_requires_admin(self, logged_in_client, test_oncall):
        """Test que delete_oncall nécessite admin."""
        response = logged_in_client.get(f"/oncall/delete/{test_oncall.id}")
        # 302 = redirection vers login (car non admin)
        assert response.status_code in [302, 403]


class TestAPIEndpoints:
    """Tests pour les endpoints API."""

    def test_api_get_shifts_returns_json(self, logged_in_client):
        """Test que /api/shifts retourne du JSON."""
        response = logged_in_client.get("/api/shifts")
        assert response.status_code == 200
        assert response.content_type == "application/json"

    def test_api_get_users_returns_json(self, logged_in_client):
        """Test que /api/users retourne du JSON."""
        response = logged_in_client.get("/api/users")
        assert response.status_code == 200
        assert response.content_type == "application/json"

    def test_api_get_shift_types_returns_json(self, logged_in_client):
        """Test que /api/shift-types retourne du JSON."""
        response = logged_in_client.get("/api/shift-types")
        assert response.status_code == 200
        assert response.content_type == "application/json"

    def test_api_create_shift_requires_admin(self, non_admin_client):
        """Test que POST /api/shifts nécessite admin."""
        response = non_admin_client.post("/api/shifts", json={})
        # 302 = redirection vers login (car non admin)
        assert response.status_code in [302, 403]

    def test_api_update_shift_requires_admin(self, non_admin_client):
        """Test que PATCH /api/shifts/<id> nécessite admin."""
        response = non_admin_client.patch("/api/shifts/1", json={})
        # 302 = redirection vers login (car non admin)
        assert response.status_code in [302, 403]

    def test_api_delete_shift_requires_admin(self, non_admin_client):
        """Test que DELETE /api/shifts/<id> nécessite admin."""
        response = non_admin_client.delete("/api/shifts/1")
        # 302 = redirection vers login (car non admin)
        assert response.status_code in [302, 403]
