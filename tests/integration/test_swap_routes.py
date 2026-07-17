"""
Integration tests for the shift-swap routes: create/confirm/decline/list/
cancel on the user side (swap_routes.py) and approve/reject/revert on the
admin side (admin_swap_routes.py).
"""

from app import db
from app.models import Shift, SwapRequest
from app.services import SwapService


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
            assert SwapRequest.query.first().status == SwapRequest.PENDING

    def test_add_swap_missing_fields(self, test_app, non_admin_client):
        resp = non_admin_client.post("/swaps/add", data={}, follow_redirects=True)
        assert resp.status_code == 200
        with test_app.app_context():
            assert SwapRequest.query.count() == 0

    def test_add_swap_not_owner_rejected(
        self, test_app, non_admin_client, second_user, test_swap_shift, test_user
    ):
        """non_admin_client is test_user, the shift's real owner - a
        different target is forced here to check the business-rule error
        message rather than a plain HTTP 404/permission error."""
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

    def test_swaps_page_survives_deleted_shift(
        self, test_app, non_admin_client, test_swap_request, test_swap_shift
    ):
        """Bug hunt regression (v1.0): SwapRequest.shift is a plain
        property doing db.session.get() (see app/models/swap_request.py),
        not an ORM relationship, so it silently returns None once the
        referenced Shift row is deleted - nothing in ShiftService's
        delete paths is aware a SwapRequest can reference a shift.
        swaps.html used to dereference swap.shift.date with no null
        guard (unlike target_shift, always guarded) - a single deleted
        shift 500'd the whole /swaps page for every user who could see
        that request."""
        with test_app.app_context():
            db.session.delete(db.session.get(Shift, test_swap_shift.id))
            db.session.commit()

        resp = non_admin_client.get("/swaps")
        assert resp.status_code == 200
        assert "Shift supprimé".encode() in resp.data

    def test_confirm_page_renders_for_target(
        self, test_app, client, second_user, test_swap_request
    ):
        client.post(
            "/login",
            data={"email": second_user.email, "password": "test123"},
            follow_redirects=True,
        )
        resp = client.get(f"/swaps/{test_swap_request.id}/confirm")
        assert resp.status_code == 200

    def test_confirm_post_moves_to_awaiting_admin(
        self, test_app, client, second_user, test_swap_request
    ):
        client.post(
            "/login",
            data={"email": second_user.email, "password": "test123"},
            follow_redirects=True,
        )
        resp = client.post(
            f"/swaps/{test_swap_request.id}/confirm",
            data={},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        with test_app.app_context():
            swap = db.session.get(SwapRequest, test_swap_request.id)
            assert swap.status == SwapRequest.AWAITING_ADMIN

    def test_confirm_page_survives_deleted_shift(
        self, test_app, client, second_user, test_swap_request, test_swap_shift
    ):
        with test_app.app_context():
            db.session.delete(db.session.get(Shift, test_swap_shift.id))
            db.session.commit()

        client.post(
            "/login",
            data={"email": second_user.email, "password": "test123"},
            follow_redirects=True,
        )
        resp = client.get(f"/swaps/{test_swap_request.id}/confirm")
        assert resp.status_code == 200
        assert "Shift supprimé".encode() in resp.data

    def test_target_reject_post_declines(
        self, test_app, client, second_user, test_swap_request
    ):
        client.post(
            "/login",
            data={"email": second_user.email, "password": "test123"},
            follow_redirects=True,
        )
        resp = client.post(
            f"/swaps/{test_swap_request.id}/target-reject",
            data={"reason": "Pas disponible"},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        with test_app.app_context():
            swap = db.session.get(SwapRequest, test_swap_request.id)
            assert swap.status == SwapRequest.REJECTED
            assert swap.admin_comment == "Pas disponible"

    def test_confirm_page_by_non_target_404(
        self, test_app, non_admin_client, test_swap_request
    ):
        """non_admin_client is test_user (the requester), not the target
        - only the target may confirm."""
        resp = non_admin_client.get(f"/swaps/{test_swap_request.id}/confirm")
        assert resp.status_code == 404

    def test_confirm_nonexistent_404(self, test_app, non_admin_client):
        resp = non_admin_client.get("/swaps/999999/confirm")
        assert resp.status_code == 404

    def test_target_reject_nonexistent_404(self, test_app, non_admin_client):
        resp = non_admin_client.post("/swaps/999999/target-reject")
        assert resp.status_code == 404

    def test_target_reject_by_non_target_404(
        self, test_app, non_admin_client, test_swap_request
    ):
        """non_admin_client is test_user, the requester - not the target,
        who alone may confirm/decline."""
        resp = non_admin_client.post(f"/swaps/{test_swap_request.id}/target-reject")
        assert resp.status_code == 404

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

    def test_cancel_swap_while_awaiting_admin(
        self, test_app, non_admin_client, confirmed_swap_request
    ):
        resp = non_admin_client.post(
            f"/swaps/{confirmed_swap_request.id}/cancel", follow_redirects=True
        )
        assert resp.status_code == 200
        with test_app.app_context():
            swap = db.session.get(SwapRequest, confirmed_swap_request.id)
            assert swap.status == SwapRequest.CANCELLED

    def test_cancel_swap_nonexistent_404(self, test_app, non_admin_client):
        resp = non_admin_client.post("/swaps/999999/cancel")
        assert resp.status_code == 404


class TestAdminSwapRoutes:
    def test_list_swaps_requires_admin(self, test_app, non_admin_client):
        resp = non_admin_client.get("/admin/swaps", follow_redirects=False)
        assert resp.status_code == 302

    def test_list_swaps_shows_awaiting_target(
        self, test_app, logged_in_client, test_swap_request
    ):
        resp = logged_in_client.get("/admin/swaps")
        assert resp.status_code == 200
        assert b"Test User" in resp.data

    def test_list_swaps_shows_awaiting_admin(
        self, test_app, logged_in_client, confirmed_swap_request
    ):
        resp = logged_in_client.get("/admin/swaps")
        assert resp.status_code == 200

    def test_admin_swaps_page_survives_deleted_shift(
        self, test_app, logged_in_client, test_swap_request, test_swap_shift
    ):
        with test_app.app_context():
            db.session.delete(db.session.get(Shift, test_swap_shift.id))
            db.session.commit()

        resp = logged_in_client.get("/admin/swaps")
        assert resp.status_code == 200
        assert "Shift supprimé".encode() in resp.data

    def test_approve_swap_reassigns_shift(
        self, test_app, logged_in_client, confirmed_swap_request, second_user
    ):
        resp = logged_in_client.post(
            f"/admin/swaps/{confirmed_swap_request.id}/approve", follow_redirects=True
        )
        assert resp.status_code == 200
        with test_app.app_context():
            swap = db.session.get(SwapRequest, confirmed_swap_request.id)
            assert swap.status == SwapRequest.APPROVED
            shift = db.session.get(Shift, swap.shift_id)
            assert shift.user_id == second_user.id

    def test_approve_swap_not_yet_confirmed_by_target_fails(
        self, test_app, logged_in_client, test_swap_request
    ):
        resp = logged_in_client.post(
            f"/admin/swaps/{test_swap_request.id}/approve", follow_redirects=True
        )
        assert resp.status_code == 200
        with test_app.app_context():
            swap = db.session.get(SwapRequest, test_swap_request.id)
            assert swap.status == SwapRequest.PENDING

    def test_approve_swap_requires_admin(
        self, test_app, non_admin_client, confirmed_swap_request
    ):
        resp = non_admin_client.post(
            f"/admin/swaps/{confirmed_swap_request.id}/approve", follow_redirects=False
        )
        assert resp.status_code == 302
        with test_app.app_context():
            swap = db.session.get(SwapRequest, confirmed_swap_request.id)
            assert swap.status == SwapRequest.AWAITING_ADMIN

    def test_reject_swap(self, test_app, logged_in_client, confirmed_swap_request):
        resp = logged_in_client.post(
            f"/admin/swaps/{confirmed_swap_request.id}/reject",
            data={"reason": "Pas assez de couverture"},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        with test_app.app_context():
            swap = db.session.get(SwapRequest, confirmed_swap_request.id)
            assert swap.status == SwapRequest.REJECTED
            assert swap.admin_comment == "Pas assez de couverture"

    def test_approve_nonexistent_404(self, test_app, logged_in_client):
        resp = logged_in_client.post("/admin/swaps/999999/approve")
        assert resp.status_code == 404

    def test_list_swaps_shows_approved(
        self, test_app, logged_in_client, confirmed_swap_request
    ):
        logged_in_client.post(f"/admin/swaps/{confirmed_swap_request.id}/approve")

        resp = logged_in_client.get("/admin/swaps")
        assert resp.status_code == 200
        assert b"Test User" in resp.data

    def test_revert_swap_reassigns_shift_back(
        self, test_app, logged_in_client, confirmed_swap_request, test_user
    ):
        logged_in_client.post(f"/admin/swaps/{confirmed_swap_request.id}/approve")

        resp = logged_in_client.post(
            f"/admin/swaps/{confirmed_swap_request.id}/revert", follow_redirects=True
        )
        assert resp.status_code == 200
        with test_app.app_context():
            swap = db.session.get(SwapRequest, confirmed_swap_request.id)
            assert swap.status == SwapRequest.REVERTED
            shift = db.session.get(Shift, swap.shift_id)
            assert shift.user_id == test_user.id

    def test_revert_swap_requires_admin(
        self, test_app, non_admin_client, confirmed_swap_request, admin_user
    ):
        # Only one HTTP client in this test (two test_client() calls off
        # the same test_app end up sharing a cookiejar - an artifact of
        # this test harness, not an app bug; see logged_in_client/
        # non_admin_client in conftest, never combined in a single test
        # elsewhere in this repo for the same reason). The "already
        # approved" state is therefore set up directly via the service,
        # not via a second authenticated admin HTTP request.
        with test_app.app_context():
            SwapService.approve_swap(confirmed_swap_request, admin_user)

        resp = non_admin_client.post(
            f"/admin/swaps/{confirmed_swap_request.id}/revert", follow_redirects=False
        )
        assert resp.status_code == 302
        with test_app.app_context():
            swap = db.session.get(SwapRequest, confirmed_swap_request.id)
            assert swap.status == SwapRequest.APPROVED

    def test_revert_awaiting_admin_swap_fails(
        self, test_app, logged_in_client, confirmed_swap_request
    ):
        resp = logged_in_client.post(
            f"/admin/swaps/{confirmed_swap_request.id}/revert", follow_redirects=True
        )
        assert resp.status_code == 200
        with test_app.app_context():
            swap = db.session.get(SwapRequest, confirmed_swap_request.id)
            assert swap.status == SwapRequest.AWAITING_ADMIN

    def test_revert_nonexistent_404(self, test_app, logged_in_client):
        resp = logged_in_client.post("/admin/swaps/999999/revert")
        assert resp.status_code == 404

    def test_purge_requires_admin(
        self, test_app, non_admin_client, confirmed_swap_request, admin_user
    ):
        with test_app.app_context():
            SwapService.reject_swap(confirmed_swap_request, admin_user)
        resp = non_admin_client.post("/admin/swaps/purge", follow_redirects=False)
        assert resp.status_code == 302
        with test_app.app_context():
            assert SwapRequest.query.count() == 1

    def test_purge_deletes_all_resolved(
        self, test_app, logged_in_client, confirmed_swap_request, admin_user
    ):
        with test_app.app_context():
            SwapService.reject_swap(confirmed_swap_request, admin_user)

        resp = logged_in_client.post("/admin/swaps/purge", follow_redirects=True)
        assert resp.status_code == 200
        with test_app.app_context():
            assert SwapRequest.query.count() == 0


class TestUserPurgeSwaps:
    def test_purge_deletes_own_resolved(
        self, test_app, non_admin_client, confirmed_swap_request, admin_user
    ):
        with test_app.app_context():
            SwapService.reject_swap(confirmed_swap_request, admin_user)

        resp = non_admin_client.post("/swaps/purge", follow_redirects=True)
        assert resp.status_code == 200
        with test_app.app_context():
            assert SwapRequest.query.count() == 0

    def test_purge_keeps_pending(self, test_app, non_admin_client, test_swap_request):
        resp = non_admin_client.post("/swaps/purge", follow_redirects=True)
        assert resp.status_code == 200
        with test_app.app_context():
            assert SwapRequest.query.count() == 1

    def test_purge_keeps_awaiting_admin(
        self, test_app, non_admin_client, confirmed_swap_request
    ):
        resp = non_admin_client.post("/swaps/purge", follow_redirects=True)
        assert resp.status_code == 200
        with test_app.app_context():
            assert SwapRequest.query.count() == 1
