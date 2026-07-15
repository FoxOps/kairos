"""
Targeted tests for the error/edge-case branches of
app/routes/shift_routes.py not covered by the existing suites
(test_routes.py, test_main_*.py): form validation, 404s, exceptions,
the full drag & drop API.
"""

from datetime import date, datetime, timedelta
from unittest.mock import patch

from app import db
from app.models import Shift


def _next_weekday():
    d = date.today() + timedelta(days=1)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


class TestScheduleRoutePerPage:
    def test_per_page_zero_shows_all(self, test_app, logged_in_client):
        resp = logged_in_client.get("/schedule?per_page=0")
        assert resp.status_code == 200


class TestAddShiftValidation:
    def test_invalid_shift_type_id(self, test_app, logged_in_client, test_user):
        resp = logged_in_client.post(
            "/schedule/add",
            data={
                "user_id": str(test_user.id),
                "shift_type_id": "999999",
                "start_date": _next_weekday().isoformat(),
                "end_date": _next_weekday().isoformat(),
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert b"Type de shift invalide" in resp.data

    def test_invalid_user_id(self, test_app, logged_in_client, test_shift_type):
        resp = logged_in_client.post(
            "/schedule/add",
            data={
                "user_id": "999999",
                "shift_type_id": str(test_shift_type.id),
                "start_date": _next_weekday().isoformat(),
                "end_date": _next_weekday().isoformat(),
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert b"Utilisateur invalide" in resp.data

    def test_start_date_after_end_date(
        self, test_app, logged_in_client, test_user, test_shift_type
    ):
        weekday = _next_weekday()
        resp = logged_in_client.post(
            "/schedule/add",
            data={
                "user_id": str(test_user.id),
                "shift_type_id": str(test_shift_type.id),
                "start_date": weekday.isoformat(),
                "end_date": (weekday - timedelta(days=1)).isoformat(),
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert b"anterieure" in resp.data

    def test_conflict_date_shows_error(
        self, test_app, logged_in_client, test_user, test_shift_type
    ):
        weekday = _next_weekday()
        db.session.add(
            Shift(
                date=weekday,
                start_time=datetime.combine(weekday, datetime.min.time()),
                end_time=datetime.combine(weekday, datetime.min.time())
                + timedelta(hours=8),
                user_id=test_user.id,
                shift_type_id=test_shift_type.id,
            )
        )
        db.session.commit()

        resp = logged_in_client.post(
            "/schedule/add",
            data={
                "user_id": str(test_user.id),
                "shift_type_id": str(test_shift_type.id),
                "start_date": weekday.isoformat(),
                "end_date": weekday.isoformat(),
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert b"Impossible d" in resp.data

    def test_invalid_date_format(
        self, test_app, logged_in_client, test_user, test_shift_type
    ):
        resp = logged_in_client.post(
            "/schedule/add",
            data={
                "user_id": str(test_user.id),
                "shift_type_id": str(test_shift_type.id),
                "start_date": "not-a-date",
                "end_date": "not-a-date",
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert b"Format de date invalide" in resp.data

    def test_service_exception_handled(
        self, test_app, logged_in_client, test_user, test_shift_type
    ):
        weekday = _next_weekday()
        with patch(
            "app.routes.shift_routes.ShiftService.add_shifts_for_range",
            side_effect=RuntimeError("boom"),
        ):
            resp = logged_in_client.post(
                "/schedule/add",
                data={
                    "user_id": str(test_user.id),
                    "shift_type_id": str(test_shift_type.id),
                    "start_date": weekday.isoformat(),
                    "end_date": weekday.isoformat(),
                },
                follow_redirects=True,
            )
        assert resp.status_code == 200
        assert b"Erreur" in resp.data


class TestDeleteShift:
    def test_delete_nonexistent_shift_404(self, test_app, logged_in_client):
        resp = logged_in_client.post("/schedule/delete/999999")
        assert resp.status_code == 404

    def test_delete_shift_exception_handled(
        self, test_app, logged_in_client, test_shift
    ):
        with patch(
            "app.routes.shift_routes.ShiftService.delete_shift",
            side_effect=RuntimeError("boom"),
        ):
            resp = logged_in_client.post(
                f"/schedule/delete/{test_shift.id}", follow_redirects=True
            )
        assert resp.status_code == 200
        assert b"Erreur" in resp.data


class TestBulkDeleteExceptions:
    def test_delete_all_shifts_exception_handled(
        self, test_app, logged_in_client, test_shift
    ):
        with patch(
            "app.routes.shift_routes.ShiftService.delete_all",
            side_effect=RuntimeError("boom"),
        ):
            resp = logged_in_client.post("/shift/delete-all", follow_redirects=True)
        assert resp.status_code == 200
        assert b"Erreur" in resp.data

    def test_delete_all_for_user_exception_handled(
        self, test_app, logged_in_client, test_user, test_shift
    ):
        with patch(
            "app.routes.shift_routes.ShiftService.delete_all_for_user",
            side_effect=RuntimeError("boom"),
        ):
            resp = logged_in_client.post(
                f"/shift/delete-all-for-user/{test_user.id}", follow_redirects=True
            )
        assert resp.status_code == 200
        assert b"Erreur" in resp.data

    def test_delete_for_day_exception_handled(
        self, test_app, logged_in_client, test_shift
    ):
        with patch(
            "app.routes.shift_routes.ShiftService.delete_for_day",
            side_effect=RuntimeError("boom"),
        ):
            resp = logged_in_client.post(
                f"/shift/delete-day/{date.today().isoformat()}", follow_redirects=True
            )
        assert resp.status_code == 200
        assert b"Erreur" in resp.data

    def test_delete_for_week_exception_handled(
        self, test_app, logged_in_client, test_shift
    ):
        with patch(
            "app.routes.shift_routes.ShiftService.delete_for_week",
            side_effect=RuntimeError("boom"),
        ):
            resp = logged_in_client.post(
                f"/shift/delete-week/{date.today().isoformat()}", follow_redirects=True
            )
        assert resp.status_code == 200
        assert b"Erreur" in resp.data


class TestApiCreateShift:
    def test_no_json_body(self, test_app, logged_in_client):
        resp = logged_in_client.post(
            "/api/shifts", data="null", content_type="application/json"
        )
        assert resp.status_code == 400

    def test_missing_fields(self, test_app, logged_in_client):
        resp = logged_in_client.post("/api/shifts", json={"userId": 1})
        assert resp.status_code == 400

    def test_user_not_found(self, test_app, logged_in_client, test_shift_type):
        weekday = _next_weekday()
        resp = logged_in_client.post(
            "/api/shifts",
            json={
                "userId": 999999,
                "shiftTypeId": test_shift_type.id,
                "start": datetime.combine(weekday, datetime.min.time()).isoformat(),
            },
        )
        assert resp.status_code == 404

    def test_shift_type_not_found(self, test_app, logged_in_client, test_user):
        weekday = _next_weekday()
        resp = logged_in_client.post(
            "/api/shifts",
            json={
                "userId": test_user.id,
                "shiftTypeId": 999999,
                "start": datetime.combine(weekday, datetime.min.time()).isoformat(),
            },
        )
        assert resp.status_code == 404

    def test_success(self, test_app, logged_in_client, test_user, test_shift_type):
        weekday = _next_weekday()
        resp = logged_in_client.post(
            "/api/shifts",
            json={
                "userId": test_user.id,
                "shiftTypeId": test_shift_type.id,
                "start": datetime.combine(weekday, datetime.min.time()).isoformat(),
                "end": (
                    datetime.combine(weekday, datetime.min.time()) + timedelta(hours=8)
                ).isoformat(),
            },
        )
        assert resp.status_code == 200
        assert resp.get_json()["success"] is True

    def test_service_error_returns_400(
        self, test_app, logged_in_client, test_user, test_shift_type
    ):
        saturday = date.today()
        while saturday.weekday() != 5:
            saturday += timedelta(days=1)
        resp = logged_in_client.post(
            "/api/shifts",
            json={
                "userId": test_user.id,
                "shiftTypeId": test_shift_type.id,
                "start": datetime.combine(saturday, datetime.min.time()).isoformat(),
            },
        )
        assert resp.status_code == 400

    def test_invalid_date_format_returns_400(
        self, test_app, logged_in_client, test_user, test_shift_type
    ):
        resp = logged_in_client.post(
            "/api/shifts",
            json={
                "userId": test_user.id,
                "shiftTypeId": test_shift_type.id,
                "start": "not-a-date",
            },
        )
        assert resp.status_code == 400

    def test_unexpected_exception_returns_500(
        self, test_app, logged_in_client, test_user, test_shift_type
    ):
        weekday = _next_weekday()
        with patch(
            "app.routes.shift_routes.ShiftService.api_create",
            side_effect=RuntimeError("boom"),
        ):
            resp = logged_in_client.post(
                "/api/shifts",
                json={
                    "userId": test_user.id,
                    "shiftTypeId": test_shift_type.id,
                    "start": datetime.combine(weekday, datetime.min.time()).isoformat(),
                },
            )
        assert resp.status_code == 500


class TestApiCreateShiftTimezoneConversion:
    """Round-trip: FullCalendar (timeZone: 'UTC') sends the viewer's own
    wall-clock digits with no real conversion (see
    fullcalendar-config.js's comment on the Calendar options and
    app/utils/helpers/timezone_helpers.py). The server must convert
    those digits from the viewer's effective_timezone into the org's
    canonical default_timezone before storing, and convert back for
    display - this is what makes the /profile/update timezone
    preference actually affect the calendar, not just the ICS export."""

    def test_create_converts_viewer_tz_to_org_tz_for_storage(
        self, test_app, logged_in_client, test_user, test_shift_type
    ):
        with test_app.app_context():
            from app.services import SettingsService

            SettingsService.set_default_timezone("Europe/Paris")

        logged_in_client.post(
            "/profile/update",
            data={
                "name": "Admin",
                "email": "login@example.com",
                "timezone": "America/New_York",
            },
            follow_redirects=True,
        )

        # 2024-07-01 is a Monday, clear of the weekend rejection rule.
        resp = logged_in_client.post(
            "/api/shifts",
            json={
                "userId": test_user.id,
                "shiftTypeId": test_shift_type.id,
                # Viewer (America/New_York) wall-clock digits, exactly as
                # FullCalendar/the create-shift modal would send them.
                "start": "2024-07-01T09:00:00",
                "end": "2024-07-01T17:00:00",
            },
        )

        assert resp.status_code == 200
        body = resp.get_json()
        assert body["success"] is True

        # Paris (CEST, UTC+2) is 6 hours ahead of New York (EDT, UTC-4)
        # in summer: 09:00 New York -> 15:00 Paris, same instant.
        with test_app.app_context():
            stored_shift = db.session.get(Shift, body["shift"]["id"])
            assert stored_shift.start_time.isoformat() == "2024-07-01T15:00:00"
            assert stored_shift.end_time.isoformat() == "2024-07-01T23:00:00"

        # The response echoes back in the viewer's own timezone (round
        # trip), not the org's.
        assert body["shift"]["start"] == "2024-07-01T09:00:00"
        assert body["shift"]["end"] == "2024-07-01T17:00:00"


class TestApiUpdateShift:
    def test_shift_not_found(self, test_app, logged_in_client):
        resp = logged_in_client.patch(
            "/api/shifts/999999", json={"start": datetime.now().isoformat()}
        )
        assert resp.status_code == 404

    def test_no_json_body(self, test_app, logged_in_client, test_shift):
        resp = logged_in_client.patch(
            f"/api/shifts/{test_shift.id}", data="null", content_type="application/json"
        )
        assert resp.status_code == 400

    def test_missing_start(self, test_app, logged_in_client, test_shift):
        resp = logged_in_client.patch(f"/api/shifts/{test_shift.id}", json={})
        assert resp.status_code == 400

    def test_success_without_end_uses_original_duration(
        self, test_app, logged_in_client, test_user, test_shift_type
    ):
        weekday = _next_weekday()
        shift = Shift(
            date=weekday,
            start_time=datetime.combine(weekday, datetime.min.time()),
            end_time=datetime.combine(weekday, datetime.min.time())
            + timedelta(hours=8),
            user_id=test_user.id,
            shift_type_id=test_shift_type.id,
        )
        db.session.add(shift)
        db.session.commit()

        new_weekday = _next_weekday() + timedelta(days=1)
        while new_weekday.weekday() >= 5:
            new_weekday += timedelta(days=1)

        resp = logged_in_client.patch(
            f"/api/shifts/{shift.id}",
            json={
                "start": datetime.combine(new_weekday, datetime.min.time()).isoformat()
            },
        )
        assert resp.status_code == 200
        assert resp.get_json()["success"] is True

    def test_invalid_date_format(self, test_app, logged_in_client, test_shift):
        resp = logged_in_client.patch(
            f"/api/shifts/{test_shift.id}", json={"start": "bogus"}
        )
        assert resp.status_code == 400

    def test_unexpected_exception_returns_500(
        self, test_app, logged_in_client, test_shift
    ):
        with patch(
            "app.routes.shift_routes.ShiftService.api_update",
            side_effect=RuntimeError("boom"),
        ):
            resp = logged_in_client.patch(
                f"/api/shifts/{test_shift.id}",
                json={"start": datetime.now().isoformat()},
            )
        assert resp.status_code == 500


class TestApiDeleteShift:
    def test_not_found(self, test_app, logged_in_client):
        resp = logged_in_client.delete("/api/shifts/999999")
        assert resp.status_code == 404

    def test_unexpected_exception_returns_500(
        self, test_app, logged_in_client, test_shift
    ):
        with patch(
            "app.routes.shift_routes.ShiftService.api_delete",
            side_effect=RuntimeError("boom"),
        ):
            resp = logged_in_client.delete(f"/api/shifts/{test_shift.id}")
        assert resp.status_code == 500
