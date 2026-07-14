"""
Tests d'intégration pour les routes d'échange de shifts : création/liste/
annulation côté utilisateur (swap_routes.py) et validation côté admin
(admin_swap_routes.py).
"""

from app import db
from app.models import Shift, SwapRequest


class TestUserSwapRoutes:
    def test_swaps_page_requires_login(self, test_app, client):
        resp = client.get("/swaps")
        assert resp.status_code in (302, 401)

    def test_swaps_page_lists_sent_and_received(
        self, test_app, non_admin_client, test_swap_request
    ):
        resp = non_admin_client.get("/swaps")
        assert resp.status_code == 200
        assert b"Second User" in resp.data

    def test_add_swap_form_renders(self, test_app, non_admin_client, test_swap_shift):
        resp = non_admin_client.get("/swaps/add")
        assert resp.status_code == 200

    def test_add_swap_creates_request(
        self, test_app, non_admin_client, test_swap_shift, second_user
    ):
        resp = non_admin_client.post(
            "/swaps/add",
            data={"shift_id": test_swap_shift.id, "target_user_id": second_user.id},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        with test_app.app_context():
            assert SwapRequest.query.count() == 1

    def test_add_swap_missing_fields(self, test_app, non_admin_client):
        resp = non_admin_client.post("/swaps/add", data={}, follow_redirects=True)
        assert resp.status_code == 200
        with test_app.app_context():
            assert SwapRequest.query.count() == 0

    def test_add_swap_not_owner_rejected(
        self, test_app, non_admin_client, second_user, test_swap_shift, test_user
    ):
        """non_admin_client est test_user, propriétaire réel du shift -
        on force un autre target pour vérifier le message d'erreur métier
        plutôt qu'une simple 404/permission HTTP."""
        with test_app.app_context():
            foreign_shift = Shift(
                date=test_swap_shift.date,
                start_time=test_swap_shift.start_time,
                end_time=test_swap_shift.end_time,
                user_id=second_user.id,
                shift_type_id=test_swap_shift.shift_type_id,
            )
            db.session.add(foreign_shift)
            db.session.commit()
            foreign_shift_id = foreign_shift.id

        resp = non_admin_client.post(
            "/swaps/add",
            data={"shift_id": foreign_shift_id, "target_user_id": second_user.id},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        with test_app.app_context():
            assert SwapRequest.query.count() == 0

    def test_cancel_swap_by_requester(
        self, test_app, non_admin_client, test_swap_request
    ):
        resp = non_admin_client.post(
            f"/swaps/{test_swap_request.id}/cancel", follow_redirects=True
        )
        assert resp.status_code == 200
        with test_app.app_context():
            swap = db.session.get(SwapRequest, test_swap_request.id)
            assert swap.status == SwapRequest.CANCELLED

    def test_cancel_swap_nonexistent_404(self, test_app, non_admin_client):
        resp = non_admin_client.post("/swaps/999999/cancel")
        assert resp.status_code == 404

    def test_api_target_shifts(
        self, test_app, non_admin_client, test_swap_shift, second_user
    ):
        with test_app.app_context():
            other_shift = Shift(
                date=test_swap_shift.date,
                start_time=test_swap_shift.start_time,
                end_time=test_swap_shift.end_time,
                user_id=second_user.id,
                shift_type_id=test_swap_shift.shift_type_id,
            )
            db.session.add(other_shift)
            db.session.commit()

        resp = non_admin_client.get(
            f"/api/swaps/target-shifts?user_id={second_user.id}"
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert len(data["shifts"]) == 1


class TestAdminSwapRoutes:
    def test_list_swaps_requires_admin(self, test_app, non_admin_client):
        resp = non_admin_client.get("/admin/swaps", follow_redirects=False)
        assert resp.status_code == 302

    def test_list_swaps_shows_pending(
        self, test_app, logged_in_client, test_swap_request
    ):
        resp = logged_in_client.get("/admin/swaps")
        assert resp.status_code == 200

    def test_approve_swap_reassigns_shift(
        self, test_app, logged_in_client, test_swap_request, second_user
    ):
        resp = logged_in_client.post(
            f"/admin/swaps/{test_swap_request.id}/approve", follow_redirects=True
        )
        assert resp.status_code == 200
        with test_app.app_context():
            swap = db.session.get(SwapRequest, test_swap_request.id)
            assert swap.status == SwapRequest.APPROVED
            shift = db.session.get(Shift, swap.shift_id)
            assert shift.user_id == second_user.id

    def test_approve_swap_requires_admin(
        self, test_app, non_admin_client, test_swap_request
    ):
        resp = non_admin_client.post(
            f"/admin/swaps/{test_swap_request.id}/approve", follow_redirects=False
        )
        assert resp.status_code == 302
        with test_app.app_context():
            swap = db.session.get(SwapRequest, test_swap_request.id)
            assert swap.status == SwapRequest.PENDING

    def test_reject_swap(self, test_app, logged_in_client, test_swap_request):
        resp = logged_in_client.post(
            f"/admin/swaps/{test_swap_request.id}/reject",
            data={"reason": "Pas assez de couverture"},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        with test_app.app_context():
            swap = db.session.get(SwapRequest, test_swap_request.id)
            assert swap.status == SwapRequest.REJECTED
            assert swap.admin_comment == "Pas assez de couverture"

    def test_approve_nonexistent_404(self, test_app, logged_in_client):
        resp = logged_in_client.post("/admin/swaps/999999/approve")
        assert resp.status_code == 404
