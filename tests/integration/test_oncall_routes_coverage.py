"""
Targeted tests for the error/edge-case branches of
app/routes/oncall_routes.py not covered by the existing suites.
"""

from datetime import date, datetime, timedelta
from unittest.mock import patch


def _next_friday():
    d = date.today()
    days_ahead = (4 - d.weekday()) % 7
    days_ahead = days_ahead or 7
    return d + timedelta(days=days_ahead)


class TestOncallRoutePerPage:
    def test_per_page_zero_shows_all(self, test_app, logged_in_client):
        resp = logged_in_client.get("/oncall?per_page=0")
        assert resp.status_code == 200


class TestAddOncallEdgeCases:
    def test_invalid_user_id(self, test_app, logged_in_client):
        resp = logged_in_client.post(
            "/oncall/add",
            data={"user_id": "999999", "start_date": _next_friday().isoformat()},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert b"Utilisateur invalide" in resp.data

    def test_service_error_flashed(self, test_app, logged_in_client, test_user):
        """Default OnCallAnchorRule (unconfigured) = Friday - the flashed
        error message is now generic ("jour configuré"), not hardcoded
        to say "vendredi", since the anchor day is per-group configurable."""
        not_friday = date.today()
        while not_friday.weekday() == 4:
            not_friday += timedelta(days=1)
        resp = logged_in_client.post(
            "/oncall/add",
            data={"user_id": str(test_user.id), "start_date": not_friday.isoformat()},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert "jour configuré".encode() in resp.data

    def test_invalid_date_format(self, test_app, logged_in_client, test_user):
        resp = logged_in_client.post(
            "/oncall/add",
            data={"user_id": str(test_user.id), "start_date": "bogus"},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert b"Format de date invalide" in resp.data

    def test_service_exception_handled(self, test_app, logged_in_client, test_user):
        with patch(
            "app.routes.oncall_routes.OnCallService.add_oncall",
            side_effect=RuntimeError("boom"),
        ):
            resp = logged_in_client.post(
                "/oncall/add",
                data={
                    "user_id": str(test_user.id),
                    "start_date": _next_friday().isoformat(),
                },
                follow_redirects=True,
            )
        assert resp.status_code == 200


class TestDeleteOncall:
    def test_delete_nonexistent_404(self, test_app, logged_in_client):
        resp = logged_in_client.post("/oncall/delete/999999")
        assert resp.status_code == 404

    def test_delete_exception_handled(self, test_app, logged_in_client, test_oncall):
        with patch(
            "app.routes.oncall_routes.OnCallService.delete_oncall",
            side_effect=RuntimeError("boom"),
        ):
            resp = logged_in_client.post(
                f"/oncall/delete/{test_oncall.id}", follow_redirects=True
            )
        assert resp.status_code == 200
        assert b"Erreur" in resp.data


class TestBulkDeleteExceptions:
    def test_delete_filtered_exception_handled(
        self, test_app, logged_in_client, test_oncall
    ):
        with patch(
            "app.routes.oncall_routes.OnCallService.delete_filtered",
            side_effect=RuntimeError("boom"),
        ):
            resp = logged_in_client.post(
                "/oncall/delete-filtered", follow_redirects=True
            )
        assert resp.status_code == 200
        assert b"Erreur" in resp.data

    def test_delete_selected_exception_handled(
        self, test_app, logged_in_client, test_oncall
    ):
        with patch(
            "app.routes.oncall_routes.OnCallService.delete_filtered",
            side_effect=RuntimeError("boom"),
        ):
            resp = logged_in_client.post(
                "/oncall/delete-selected",
                data={"ids": [str(test_oncall.id)]},
                follow_redirects=True,
            )
        assert resp.status_code == 200
        assert b"Erreur" in resp.data


class TestApiDeleteOncall:
    def test_not_found(self, test_app, logged_in_client):
        resp = logged_in_client.delete("/api/oncall/999999")
        assert resp.status_code == 404

    def test_success(self, test_app, logged_in_client, test_oncall):
        resp = logged_in_client.delete(f"/api/oncall/{test_oncall.id}")
        assert resp.status_code == 200
        assert resp.get_json()["success"] is True

    def test_unexpected_exception_returns_500(
        self, test_app, logged_in_client, test_oncall
    ):
        with patch(
            "app.routes.oncall_routes.OnCallService.api_delete",
            side_effect=RuntimeError("boom"),
        ):
            resp = logged_in_client.delete(f"/api/oncall/{test_oncall.id}")
        assert resp.status_code == 500


class TestApiUpdateOncall:
    def test_not_found(self, test_app, logged_in_client):
        resp = logged_in_client.patch(
            "/api/oncall/999999", json={"start": datetime.now().isoformat()}
        )
        assert resp.status_code == 404

    def test_no_json_body(self, test_app, logged_in_client, test_oncall):
        resp = logged_in_client.patch(
            f"/api/oncall/{test_oncall.id}",
            data="null",
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_missing_start(self, test_app, logged_in_client, test_oncall):
        """A non-empty body without "start" - json={} would be falsy
        and hit the earlier "Aucune donnee recue" guard instead."""
        resp = logged_in_client.patch(
            f"/api/oncall/{test_oncall.id}", json={"end": "2023-12-20T21:00:00"}
        )
        assert resp.status_code == 400
        assert "manquante" in resp.get_json()["error"]

    def test_service_reports_validation_error(
        self, test_app, logged_in_client, test_oncall
    ):
        with patch(
            "app.routes.oncall_routes.OnCallService.api_update",
            return_value=(None, "erreur simulée"),
        ):
            resp = logged_in_client.patch(
                f"/api/oncall/{test_oncall.id}",
                json={"start": datetime.now().isoformat()},
            )
        assert resp.status_code == 400
        assert resp.get_json()["error"] == "erreur simulée"

    def test_success_without_end_uses_original_duration(
        self, test_app, logged_in_client, test_user
    ):
        from app import db
        from app.models import OnCall

        friday = _next_friday()
        start = datetime.combine(friday, datetime.min.time()).replace(hour=21)
        end = start + timedelta(days=7, hours=-14)
        oncall = OnCall(user_id=test_user.id, start_time=start, end_time=end)
        db.session.add(oncall)
        db.session.commit()

        new_friday = _next_friday() + timedelta(days=7)
        new_start = datetime.combine(new_friday, datetime.min.time()).replace(hour=21)
        resp = logged_in_client.patch(
            f"/api/oncall/{oncall.id}",
            json={"start": new_start.isoformat()},
        )
        assert resp.status_code == 200
        assert resp.get_json()["success"] is True

    def test_reassigns_user(self, test_app, logged_in_client, test_user, second_user):
        """The calendar's on-call-edit modal can reassign the on-call
        person via the same PATCH endpoint the drag/resize path
        already uses."""
        from app import db
        from app.models import OnCall

        friday = _next_friday()
        start = datetime.combine(friday, datetime.min.time()).replace(hour=21)
        end = start + timedelta(days=7, hours=-14)
        oncall = OnCall(user_id=test_user.id, start_time=start, end_time=end)
        db.session.add(oncall)
        db.session.commit()

        resp = logged_in_client.patch(
            f"/api/oncall/{oncall.id}",
            json={
                "start": start.isoformat(),
                "end": end.isoformat(),
                "userId": second_user.id,
            },
        )
        assert resp.status_code == 200
        assert resp.get_json()["success"] is True

        updated = db.session.get(OnCall, oncall.id)
        assert updated.user_id == second_user.id


class TestApiGetOncallUsers:
    """Tests for GET /api/oncall-users - populates the calendar's
    on-call-edit modal person picker, scoped to the oncall-eligible
    group (unlike /api/users, which is schedule-eligible-group-scoped)."""

    def test_requires_login(self, test_app, client):
        resp = client.get("/api/oncall-users")
        assert resp.status_code in (302, 401)

    def test_admin_sees_oncall_group(self, test_app, logged_in_client, test_user):
        resp = logged_in_client.get("/api/oncall-users")
        assert resp.status_code == 200
        ids = {u["id"] for u in resp.get_json()}
        assert test_user.id in ids

    def test_non_admin_sees_only_self(self, test_app, non_admin_client, test_user):
        resp = non_admin_client.get("/api/oncall-users")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) == 1
        assert data[0]["id"] == test_user.id

    def test_invalid_date_format(self, test_app, logged_in_client, test_oncall):
        resp = logged_in_client.patch(
            f"/api/oncall/{test_oncall.id}", json={"start": "bogus"}
        )
        assert resp.status_code == 400

    def test_unexpected_exception_returns_500(
        self, test_app, logged_in_client, test_oncall
    ):
        with patch(
            "app.routes.oncall_routes.OnCallService.api_update",
            side_effect=RuntimeError("boom"),
        ):
            resp = logged_in_client.patch(
                f"/api/oncall/{test_oncall.id}",
                json={"start": datetime.now().isoformat()},
            )
        assert resp.status_code == 500

    def test_update_converts_viewer_tz_to_org_tz_for_storage(
        self, test_app, logged_in_client, test_user
    ):
        """Same round-trip as
        TestApiCreateShiftTimezoneConversion in
        test_shift_routes_coverage.py, for the on-call drag & drop
        update path. Uses Europe/London (1h behind Paris in summer,
        rather than New York's 6h) so the converted start still falls on
        the same Friday - OnCallService.api_update rejects any start
        that isn't a Friday, a business rule that operates on the org-tz
        canonical value."""
        from app import db
        from app.models import OnCall
        from app.services import SettingsService

        with test_app.app_context():
            SettingsService.set_default_timezone("Europe/Paris")
            oncall = OnCall(
                user_id=test_user.id,
                start_time=datetime(2024, 7, 5, 21, 0),
                end_time=datetime(2024, 7, 12, 7, 0),
            )
            db.session.add(oncall)
            db.session.commit()
            oncall_id = oncall.id

        logged_in_client.post(
            "/profile/settings",
            data={"timezone": "Europe/London"},
            follow_redirects=True,
        )

        resp = logged_in_client.patch(
            f"/api/oncall/{oncall_id}",
            # Viewer (Europe/London) wall-clock digits.
            json={"start": "2024-07-05T20:00:00", "end": "2024-07-12T06:00:00"},
        )

        assert resp.status_code == 200
        body = resp.get_json()
        assert body["success"] is True

        # Paris (CEST, UTC+2) is 1 hour ahead of London (BST, UTC+1) in
        # summer.
        with test_app.app_context():
            updated = db.session.get(OnCall, oncall_id)
            assert updated.start_time.isoformat() == "2024-07-05T21:00:00"
            assert updated.end_time.isoformat() == "2024-07-12T07:00:00"

        assert body["oncall"]["start"] == "2024-07-05T20:00:00"
        assert body["oncall"]["end"] == "2024-07-12T06:00:00"
