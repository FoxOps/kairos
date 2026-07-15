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
        not_friday = date.today()
        while not_friday.weekday() == 4:
            not_friday += timedelta(days=1)
        resp = logged_in_client.post(
            "/oncall/add",
            data={"user_id": str(test_user.id), "start_date": not_friday.isoformat()},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert b"vendredi" in resp.data

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
    def test_delete_all_exception_handled(
        self, test_app, logged_in_client, test_oncall
    ):
        with patch(
            "app.routes.oncall_routes.OnCallService.delete_all",
            side_effect=RuntimeError("boom"),
        ):
            resp = logged_in_client.post("/oncall/delete-all", follow_redirects=True)
        assert resp.status_code == 200
        assert b"Erreur" in resp.data

    def test_delete_all_for_user_not_found_404(self, test_app, logged_in_client):
        resp = logged_in_client.post("/oncall/delete-all-for-user/999999")
        assert resp.status_code == 404

    def test_delete_all_for_user_exception_handled(
        self, test_app, logged_in_client, test_user, test_oncall
    ):
        with patch(
            "app.routes.oncall_routes.OnCallService.delete_all_for_user",
            side_effect=RuntimeError("boom"),
        ):
            resp = logged_in_client.post(
                f"/oncall/delete-all-for-user/{test_user.id}", follow_redirects=True
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
        resp = logged_in_client.patch(f"/api/oncall/{test_oncall.id}", json={})
        assert resp.status_code == 400

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
