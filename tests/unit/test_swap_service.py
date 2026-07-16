"""
Tests for SwapService: the business rules for shift swaps between users
(create, target confirmation/decline, cancel, admin approve/reject/revert).
"""

from datetime import datetime, timedelta
from unittest.mock import patch

from app import db
from app.models import AuditLog, Leave, Shift, SwapRequest
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
            assert swap_request.target_shift_id is None

    def test_request_swap_triggers_apprise_notification(
        self, test_app, test_user, second_user, test_swap_shift
    ):
        with test_app.app_context():
            with patch(
                "app.services.swap_service.AppriseNotificationService.notify"
            ) as mock_notify:
                SwapService.request_swap(test_user, test_swap_shift, second_user)

            mock_notify.assert_called_once()
            assert mock_notify.call_args[0][0] == "swap"

    def test_request_swap_writes_audit_log_entry(
        self, test_app, test_user, second_user, test_swap_shift
    ):
        with test_app.app_context():
            swap_request, _error = SwapService.request_swap(
                test_user, test_swap_shift, second_user
            )

            entry = AuditLog.query.filter_by(action="swap.request").first()
            assert entry is not None
            assert entry.resource_id == swap_request.id
            assert entry.actor_id == test_user.id

    def test_request_swap_not_owner(
        self, test_app, test_user, second_user, test_swap_shift
    ):
        """second_user tries to offer a shift that isn't theirs."""
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
        """A pending request already exists for this shift (test_swap_request fixture)."""
        with test_app.app_context():
            swap_request, error = SwapService.request_swap(
                test_user, test_swap_shift, second_user
            )
            assert swap_request is None
            assert "déjà en attente" in error

    def test_request_swap_duplicate_awaiting_admin(
        self,
        test_app,
        test_user,
        second_user,
        test_swap_shift,
        confirmed_swap_request,
    ):
        """A request already confirmed by its target (AWAITING_ADMIN) for
        this shift also blocks a brand new request - not just PENDING."""
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


class TestConfirmSwap:
    def test_confirm_one_way_moves_to_awaiting_admin(
        self, test_app, test_swap_request, second_user
    ):
        with test_app.app_context():
            error = SwapService.confirm_swap(test_swap_request, second_user)
            assert error is None
            assert test_swap_request.status == SwapRequest.AWAITING_ADMIN
            assert test_swap_request.target_shift_id is None

    def test_confirm_reciprocal_sets_target_shift(
        self,
        test_app,
        test_swap_request,
        second_user,
        test_swap_shift,
        test_shift_type,
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

            error = SwapService.confirm_swap(
                test_swap_request, second_user, target_shift
            )
            assert error is None
            assert test_swap_request.status == SwapRequest.AWAITING_ADMIN
            assert test_swap_request.target_shift_id == target_shift.id

    def test_confirm_writes_audit_log_entry(
        self, test_app, test_swap_request, second_user
    ):
        with test_app.app_context():
            SwapService.confirm_swap(test_swap_request, second_user)

            entry = AuditLog.query.filter_by(action="swap.confirm").first()
            assert entry is not None
            assert entry.actor_id == second_user.id

    def test_confirm_by_wrong_user_denied(
        self, test_app, test_swap_request, admin_user
    ):
        """admin_user is neither the requester nor the target."""
        with test_app.app_context():
            error = SwapService.confirm_swap(test_swap_request, admin_user)
            assert error is not None
            assert test_swap_request.status == SwapRequest.PENDING

    def test_confirm_already_confirmed_fails(
        self, test_app, confirmed_swap_request, second_user
    ):
        with test_app.app_context():
            error = SwapService.confirm_swap(confirmed_swap_request, second_user)
            assert error is not None

    def test_confirm_shift_taken_since_request_fails(
        self, test_app, test_swap_request, second_user, test_swap_shift, test_shift_type
    ):
        """second_user already has another shift on that date by the time
        they confirm - re-validated at confirmation time, not just at
        request time."""
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

            error = SwapService.confirm_swap(test_swap_request, second_user)
            assert error is not None
            assert test_swap_request.status == SwapRequest.PENDING


class TestTargetRejectSwap:
    def test_target_reject_sets_status_and_comment(
        self, test_app, test_swap_request, second_user
    ):
        with test_app.app_context():
            error = SwapService.target_reject_swap(
                test_swap_request, second_user, reason="Pas disponible"
            )
            assert error is None
            assert test_swap_request.status == SwapRequest.REJECTED
            assert test_swap_request.admin_comment == "Pas disponible"
            assert test_swap_request.reviewed_by_id == second_user.id

    def test_target_reject_by_wrong_user_denied(
        self, test_app, test_swap_request, admin_user
    ):
        with test_app.app_context():
            error = SwapService.target_reject_swap(test_swap_request, admin_user)
            assert error is not None
            assert test_swap_request.status == SwapRequest.PENDING

    def test_target_reject_after_confirmation_fails(
        self, test_app, confirmed_swap_request, second_user
    ):
        """Once AWAITING_ADMIN, the target can no longer decline - only
        cancel_swap (requester) or the admin's own reject_swap apply."""
        with test_app.app_context():
            error = SwapService.target_reject_swap(confirmed_swap_request, second_user)
            assert error is not None


class TestCancelSwap:
    def test_cancel_by_requester_while_pending(
        self, test_app, test_swap_request, test_user
    ):
        with test_app.app_context():
            error = SwapService.cancel_swap(test_swap_request, test_user)
            assert error is None
            assert test_swap_request.status == SwapRequest.CANCELLED

    def test_cancel_by_requester_while_awaiting_admin(
        self, test_app, confirmed_swap_request, test_user
    ):
        with test_app.app_context():
            error = SwapService.cancel_swap(confirmed_swap_request, test_user)
            assert error is None
            assert confirmed_swap_request.status == SwapRequest.CANCELLED

    def test_cancel_by_unrelated_user_denied(
        self, test_app, test_swap_request, second_user
    ):
        """second_user is the target, not the requester, and isn't admin."""
        with test_app.app_context():
            error = SwapService.cancel_swap(test_swap_request, second_user)
            assert error is not None
            assert test_swap_request.status == SwapRequest.PENDING

    def test_cancel_already_decided_fails(
        self, test_app, confirmed_swap_request, test_user, admin_user
    ):
        with test_app.app_context():
            SwapService.approve_swap(confirmed_swap_request, admin_user)
            error = SwapService.cancel_swap(confirmed_swap_request, test_user)
            assert error is not None


class TestApproveSwap:
    def test_approve_requires_awaiting_admin(
        self, test_app, test_swap_request, admin_user
    ):
        """A PENDING request (target hasn't confirmed yet) can't be
        approved directly."""
        with test_app.app_context():
            error = SwapService.approve_swap(test_swap_request, admin_user)
            assert error is not None
            assert test_swap_request.status == SwapRequest.PENDING

    def test_approve_reassigns_shift(
        self,
        test_app,
        confirmed_swap_request,
        admin_user,
        second_user,
        test_swap_shift,
    ):
        with test_app.app_context():
            error = SwapService.approve_swap(confirmed_swap_request, admin_user)
            assert error is None
            assert confirmed_swap_request.status == SwapRequest.APPROVED
            assert confirmed_swap_request.reviewed_by_id == admin_user.id

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
                test_user, test_swap_shift, second_user
            )
            assert error is None
            error = SwapService.confirm_swap(swap_request, second_user, target_shift)
            assert error is None

            error = SwapService.approve_swap(swap_request, admin_user)
            assert error is None

            assert db.session.get(Shift, test_swap_shift.id).user_id == second_user.id
            assert db.session.get(Shift, target_shift.id).user_id == test_user.id

    def test_approve_already_decided_fails(
        self, test_app, confirmed_swap_request, admin_user
    ):
        with test_app.app_context():
            SwapService.approve_swap(confirmed_swap_request, admin_user)
            error = SwapService.approve_swap(confirmed_swap_request, admin_user)
            assert error is not None


class TestRejectSwap:
    def test_reject_requires_awaiting_admin(
        self, test_app, test_swap_request, admin_user
    ):
        with test_app.app_context():
            error = SwapService.reject_swap(test_swap_request, admin_user)
            assert error is not None
            assert test_swap_request.status == SwapRequest.PENDING

    def test_reject_sets_status_and_comment(
        self, test_app, confirmed_swap_request, admin_user
    ):
        with test_app.app_context():
            error = SwapService.reject_swap(
                confirmed_swap_request, admin_user, reason="Effectif insuffisant"
            )
            assert error is None
            assert confirmed_swap_request.status == SwapRequest.REJECTED
            assert confirmed_swap_request.admin_comment == "Effectif insuffisant"

            # The shift hasn't moved
            unchanged_shift = db.session.get(Shift, confirmed_swap_request.shift_id)
            assert unchanged_shift.user_id == confirmed_swap_request.requester_id


class TestRevertSwap:
    def test_revert_reassigns_shift_back(
        self, test_app, confirmed_swap_request, admin_user, test_user, second_user
    ):
        with test_app.app_context():
            SwapService.approve_swap(confirmed_swap_request, admin_user)

            error = SwapService.revert_swap(confirmed_swap_request, admin_user)
            assert error is None
            assert confirmed_swap_request.status == SwapRequest.REVERTED

            reverted_shift = db.session.get(Shift, confirmed_swap_request.shift_id)
            assert reverted_shift.user_id == test_user.id

    def test_revert_reciprocal_swap(
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
                test_user, test_swap_shift, second_user
            )
            assert error is None
            SwapService.confirm_swap(swap_request, second_user, target_shift)
            SwapService.approve_swap(swap_request, admin_user)

            error = SwapService.revert_swap(swap_request, admin_user)
            assert error is None
            assert db.session.get(Shift, test_swap_shift.id).user_id == test_user.id
            assert db.session.get(Shift, target_shift.id).user_id == second_user.id

    def test_revert_not_approved_fails(
        self, test_app, confirmed_swap_request, admin_user
    ):
        with test_app.app_context():
            error = SwapService.revert_swap(confirmed_swap_request, admin_user)
            assert error is not None

    def test_revert_twice_fails(
        self, test_app, confirmed_swap_request, admin_user, test_user
    ):
        with test_app.app_context():
            SwapService.approve_swap(confirmed_swap_request, admin_user)
            SwapService.revert_swap(confirmed_swap_request, admin_user)
            error = SwapService.revert_swap(confirmed_swap_request, admin_user)
            assert error is not None

    def test_revert_shift_reassigned_since_fails(
        self, test_app, confirmed_swap_request, admin_user, test_user
    ):
        with test_app.app_context():
            SwapService.approve_swap(confirmed_swap_request, admin_user)

            shift = db.session.get(Shift, confirmed_swap_request.shift_id)
            shift.user_id = test_user.id  # someone already reassigned the shift
            db.session.commit()

            error = SwapService.revert_swap(confirmed_swap_request, admin_user)
            assert error is not None
            assert confirmed_swap_request.status == SwapRequest.APPROVED


class TestPurgeSwaps:
    """Note: the "already resolved" status is set directly on the object
    (not via reject_swap/approve_swap) to isolate the purge logic from
    the status-transition logic, already covered by TestRejectSwap/
    TestApproveSwap/TestRevertSwap.

    Deliberately no `with test_app.app_context():` here, unlike the rest
    of this file: `test_app` already has an active context for the
    entire test (see tests/conftest.py). Nesting a second one makes
    `db.session` resolve to a different SQLAlchemy session than the one
    the fixtures use (confirmed via "Object ... is already attached to
    session 'N' (this is 'M')") - the fixture objects (`test_swap_request`)
    then stay invisible to commits made inside the nested block. Harmless
    for tests that only check the in-memory Python attribute (the rest of
    this file), but silently wrong as soon as you check the actually
    persisted state (`SwapRequest.query.count()` after a bulk DELETE,
    here). The real app isn't affected: each HTTP request has its own
    context, never nested (see test_swap_routes.py::TestAdminSwapRoutes/
    TestUserPurgeSwaps, the same behavior covered via real requests)."""

    def test_purge_resolved_for_user_deletes_non_pending(
        self, test_app, test_swap_request, test_user
    ):
        test_swap_request.status = SwapRequest.REJECTED
        db.session.commit()

        count = SwapService.purge_resolved_for_user(test_user)
        assert count == 1
        assert SwapRequest.query.count() == 0

    def test_purge_resolved_for_user_keeps_pending(
        self, test_app, test_swap_request, test_user
    ):
        count = SwapService.purge_resolved_for_user(test_user)
        assert count == 0
        assert SwapRequest.query.count() == 1

    def test_purge_resolved_for_user_keeps_awaiting_admin(
        self, test_app, confirmed_swap_request, test_user
    ):
        count = SwapService.purge_resolved_for_user(test_user)
        assert count == 0
        assert SwapRequest.query.count() == 1

    def test_purge_resolved_for_user_ignores_others(
        self, test_app, test_swap_request, admin_user
    ):
        """admin_user is neither the requester nor the target of
        test_swap_request - a third party unrelated to the request must
        not be able to purge it."""
        test_swap_request.status = SwapRequest.REJECTED
        db.session.commit()

        count = SwapService.purge_resolved_for_user(admin_user)
        assert count == 0
        assert SwapRequest.query.count() == 1

    def test_purge_all_resolved_deletes_any_user(self, test_app, test_swap_request):
        test_swap_request.status = SwapRequest.REJECTED
        db.session.commit()

        count = SwapService.purge_all_resolved()
        assert count == 1
        assert SwapRequest.query.count() == 0

    def test_purge_all_resolved_keeps_pending(self, test_app, test_swap_request):
        count = SwapService.purge_all_resolved()
        assert count == 0
        assert SwapRequest.query.count() == 1
