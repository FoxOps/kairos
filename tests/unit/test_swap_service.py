"""
Tests pour SwapService : règles métier des échanges de shifts entre
utilisateurs (création, annulation, approbation, rejet).
"""

from datetime import datetime, timedelta

from app import db
from app.models import Leave, Shift, SwapRequest
from app.services import SwapService


class TestRequestSwap:
    def test_request_swap_success(
        self, test_app, test_user, second_user, test_swap_shift
    ):
        with test_app.app_context():
            swap_request, error = SwapService.request_swap(
                test_user, test_swap_shift, second_user
            )
            assert error is None
            assert swap_request is not None
            assert swap_request.status == SwapRequest.PENDING

    def test_request_swap_not_owner(
        self, test_app, test_user, second_user, test_swap_shift
    ):
        """second_user essaie de proposer un shift qui n'est pas le sien."""
        with test_app.app_context():
            swap_request, error = SwapService.request_swap(
                second_user, test_swap_shift, test_user
            )
            assert swap_request is None
            assert "appartient" in error

    def test_request_swap_to_self(self, test_app, test_user, test_swap_shift):
        with test_app.app_context():
            swap_request, error = SwapService.request_swap(
                test_user, test_swap_shift, test_user
            )
            assert swap_request is None
            assert "vous-même" in error

    def test_request_swap_duplicate_pending(
        self, test_app, test_user, second_user, test_swap_shift, test_swap_request
    ):
        """Une demande pending existe déjà pour ce shift (fixture test_swap_request)."""
        with test_app.app_context():
            swap_request, error = SwapService.request_swap(
                test_user, test_swap_shift, second_user
            )
            assert swap_request is None
            assert "déjà en attente" in error

    def test_request_swap_target_on_leave(
        self, test_app, test_user, second_user, test_swap_shift
    ):
        with test_app.app_context():
            leave = Leave(
                user_id=second_user.id,
                start_date=test_swap_shift.date - timedelta(days=1),
                end_date=test_swap_shift.date + timedelta(days=1),
            )
            db.session.add(leave)
            db.session.commit()

            swap_request, error = SwapService.request_swap(
                test_user, test_swap_shift, second_user
            )
            assert swap_request is None
            assert "congé" in error

    def test_request_swap_target_already_has_shift(
        self, test_app, test_user, second_user, test_swap_shift, test_shift_type
    ):
        with test_app.app_context():
            other_shift = Shift(
                date=test_swap_shift.date,
                start_time=datetime.combine(test_swap_shift.date, datetime.min.time()),
                end_time=datetime.combine(test_swap_shift.date, datetime.max.time()),
                user_id=second_user.id,
                shift_type_id=test_shift_type.id,
            )
            db.session.add(other_shift)
            db.session.commit()

            swap_request, error = SwapService.request_swap(
                test_user, test_swap_shift, second_user
            )
            assert swap_request is None
            assert "autre shift" in error


class TestCancelSwap:
    def test_cancel_by_requester(self, test_app, test_swap_request, test_user):
        with test_app.app_context():
            error = SwapService.cancel_swap(test_swap_request, test_user)
            assert error is None
            assert test_swap_request.status == SwapRequest.CANCELLED

    def test_cancel_by_unrelated_user_denied(
        self, test_app, test_swap_request, second_user
    ):
        """second_user est le target, pas le requester, et n'est pas admin."""
        with test_app.app_context():
            error = SwapService.cancel_swap(test_swap_request, second_user)
            assert error is not None
            assert test_swap_request.status == SwapRequest.PENDING

    def test_cancel_already_decided_fails(
        self, test_app, test_swap_request, test_user, admin_user
    ):
        with test_app.app_context():
            SwapService.approve_swap(test_swap_request, admin_user)
            error = SwapService.cancel_swap(test_swap_request, test_user)
            assert error is not None


class TestApproveSwap:
    def test_approve_reassigns_shift(
        self, test_app, test_swap_request, admin_user, second_user, test_swap_shift
    ):
        with test_app.app_context():
            error = SwapService.approve_swap(test_swap_request, admin_user)
            assert error is None
            assert test_swap_request.status == SwapRequest.APPROVED
            assert test_swap_request.reviewed_by_id == admin_user.id

            updated_shift = db.session.get(Shift, test_swap_shift.id)
            assert updated_shift.user_id == second_user.id

    def test_approve_reciprocal_swap(
        self,
        test_app,
        test_user,
        second_user,
        test_swap_shift,
        test_shift_type,
        admin_user,
    ):
        with test_app.app_context():
            target_shift = Shift(
                date=test_swap_shift.date + timedelta(days=1),
                start_time=datetime.combine(
                    test_swap_shift.date + timedelta(days=1), datetime.min.time()
                ),
                end_time=datetime.combine(
                    test_swap_shift.date + timedelta(days=1), datetime.max.time()
                ),
                user_id=second_user.id,
                shift_type_id=test_shift_type.id,
            )
            db.session.add(target_shift)
            db.session.commit()

            swap_request, error = SwapService.request_swap(
                test_user, test_swap_shift, second_user, target_shift
            )
            assert error is None

            error = SwapService.approve_swap(swap_request, admin_user)
            assert error is None

            assert db.session.get(Shift, test_swap_shift.id).user_id == second_user.id
            assert db.session.get(Shift, target_shift.id).user_id == test_user.id

    def test_approve_already_decided_fails(
        self, test_app, test_swap_request, admin_user
    ):
        with test_app.app_context():
            SwapService.approve_swap(test_swap_request, admin_user)
            error = SwapService.approve_swap(test_swap_request, admin_user)
            assert error is not None


class TestRejectSwap:
    def test_reject_sets_status_and_comment(
        self, test_app, test_swap_request, admin_user
    ):
        with test_app.app_context():
            error = SwapService.reject_swap(
                test_swap_request, admin_user, reason="Effectif insuffisant"
            )
            assert error is None
            assert test_swap_request.status == SwapRequest.REJECTED
            assert test_swap_request.admin_comment == "Effectif insuffisant"

            # Le shift n'a pas bougé
            unchanged_shift = db.session.get(Shift, test_swap_request.shift_id)
            assert unchanged_shift.user_id == test_swap_request.requester_id
