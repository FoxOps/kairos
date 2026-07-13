"""
Tests ciblés sur les branches d'erreur/edge-case de app/routes/leave_routes.py
non couvertes par les suites existantes.
"""

from datetime import date, timedelta
from unittest.mock import patch


class TestAddLeaveEdgeCases:
    def test_invalid_user_id(self, test_app, non_admin_client, test_user):
        resp = non_admin_client.post(
            "/leave/add",
            data={
                "user_id": "999999",
                "start_date": date.today().isoformat(),
                "end_date": (date.today() + timedelta(days=1)).isoformat(),
            },
            follow_redirects=True,
        )
        # user_id != current_user.id (999999 != test_user.id) -> bloqué par la
        # vérification de permission avant même d'atteindre le lookup utilisateur.
        assert resp.status_code == 200
        assert b"vous-m" in resp.data

    def test_admin_can_target_invalid_user(self, test_app, logged_in_client):
        resp = logged_in_client.post(
            "/leave/add",
            data={
                "user_id": "999999",
                "start_date": date.today().isoformat(),
                "end_date": (date.today() + timedelta(days=1)).isoformat(),
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert b"Utilisateur invalide" in resp.data

    def test_invalid_date_format(self, test_app, logged_in_client, test_user):
        resp = logged_in_client.post(
            "/leave/add",
            data={"user_id": str(test_user.id), "start_date": "bad", "end_date": "bad"},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert b"Format de date invalide" in resp.data

    def test_service_exception_handled(self, test_app, logged_in_client, test_user):
        with patch(
            "app.routes.leave_routes.LeaveService.add_leave",
            side_effect=RuntimeError("boom"),
        ):
            resp = logged_in_client.post(
                "/leave/add",
                data={
                    "user_id": str(test_user.id),
                    "start_date": date.today().isoformat(),
                    "end_date": (date.today() + timedelta(days=1)).isoformat(),
                },
                follow_redirects=True,
            )
        assert resp.status_code == 200


class TestDeleteLeave:
    def test_delete_nonexistent_leave_404(self, test_app, logged_in_client):
        resp = logged_in_client.get("/leave/delete/999999")
        assert resp.status_code == 404

    def test_delete_leave_exception_handled(
        self, test_app, logged_in_client, test_leave
    ):
        with patch(
            "app.routes.leave_routes.LeaveService.delete_leave",
            side_effect=RuntimeError("boom"),
        ):
            resp = logged_in_client.get(
                f"/leave/delete/{test_leave.id}", follow_redirects=True
            )
        assert resp.status_code == 200
        assert b"Erreur" in resp.data


class TestApiDeleteLeave:
    def test_not_found(self, test_app, logged_in_client):
        resp = logged_in_client.delete("/api/leave/999999")
        assert resp.status_code == 404

    def test_forbidden_for_other_users_leave(
        self, test_app, non_admin_client, test_leave, second_user
    ):
        # test_leave appartient à test_user ; non_admin_client est connecté en tant
        # que test_user lui-même par construction du fixture -> tester le cas
        # "autre utilisateur" nécessite un congé appartenant à second_user.
        from app import db
        from app.models import Leave

        other_leave = Leave(
            user_id=second_user.id, start_date=date.today(), end_date=date.today()
        )
        db.session.add(other_leave)
        db.session.commit()

        resp = non_admin_client.delete(f"/api/leave/{other_leave.id}")
        assert resp.status_code == 403

    def test_success(self, test_app, logged_in_client, test_leave):
        resp = logged_in_client.delete(f"/api/leave/{test_leave.id}")
        assert resp.status_code == 200
        assert resp.get_json()["success"] is True

    def test_unexpected_exception_returns_500(
        self, test_app, logged_in_client, test_leave
    ):
        with patch(
            "app.routes.leave_routes.LeaveService.api_delete",
            side_effect=RuntimeError("boom"),
        ):
            resp = logged_in_client.delete(f"/api/leave/{test_leave.id}")
        assert resp.status_code == 500

    def test_rebalance_failure_surfaces_warning(
        self, test_app, logged_in_client, test_leave
    ):
        """Régression : api_delete_leave doit signaler un échec de
        rééquilibrage au lieu de l'avaler silencieusement (bug 3)."""
        with patch(
            "app.routes.leave_routes.LeaveService.api_delete",
            return_value=(True, True),
        ):
            resp = logged_in_client.delete(f"/api/leave/{test_leave.id}")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["rebalance_warning"] is True


class TestApiUpdateLeave:
    def test_not_found(self, test_app, logged_in_client):
        resp = logged_in_client.patch(
            "/api/leave/999999", json={"start": date.today().isoformat()}
        )
        assert resp.status_code == 404

    def test_forbidden_for_other_users_leave(
        self, test_app, non_admin_client, second_user
    ):
        from app import db
        from app.models import Leave

        other_leave = Leave(
            user_id=second_user.id, start_date=date.today(), end_date=date.today()
        )
        db.session.add(other_leave)
        db.session.commit()

        resp = non_admin_client.patch(
            f"/api/leave/{other_leave.id}", json={"start": date.today().isoformat()}
        )
        assert resp.status_code == 403

    def test_no_json_body(self, test_app, logged_in_client, test_leave):
        resp = logged_in_client.patch(
            f"/api/leave/{test_leave.id}", data="null", content_type="application/json"
        )
        assert resp.status_code == 400

    def test_missing_start(self, test_app, logged_in_client, test_leave):
        resp = logged_in_client.patch(f"/api/leave/{test_leave.id}", json={})
        assert resp.status_code == 400

    def test_success_without_end_uses_original_duration(
        self, test_app, logged_in_client, test_user
    ):
        from app import db
        from app.models import Leave

        leave = Leave(
            user_id=test_user.id,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=2),
        )
        db.session.add(leave)
        db.session.commit()

        new_start = date.today() + timedelta(days=10)
        resp = logged_in_client.patch(
            f"/api/leave/{leave.id}",
            json={"start": new_start.isoformat()},
        )
        assert resp.status_code == 200
        assert resp.get_json()["success"] is True

    def test_invalid_date_format(self, test_app, logged_in_client, test_leave):
        resp = logged_in_client.patch(
            f"/api/leave/{test_leave.id}", json={"start": "bogus"}
        )
        assert resp.status_code == 400

    def test_unexpected_exception_returns_500(
        self, test_app, logged_in_client, test_leave
    ):
        with patch(
            "app.routes.leave_routes.LeaveService.api_update",
            side_effect=RuntimeError("boom"),
        ):
            resp = logged_in_client.patch(
                f"/api/leave/{test_leave.id}",
                json={"start": date.today().isoformat()},
            )
        assert resp.status_code == 500

    def test_rebalance_failure_surfaces_warning(
        self, test_app, logged_in_client, test_leave
    ):
        """Régression : api_update_leave doit signaler un échec de
        rééquilibrage au lieu de l'avaler silencieusement (bug 3)."""
        with patch(
            "app.routes.leave_routes.LeaveService.api_update",
            return_value=(test_leave, None, True),
        ):
            resp = logged_in_client.patch(
                f"/api/leave/{test_leave.id}",
                json={"start": date.today().isoformat()},
            )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["rebalance_warning"] is True
