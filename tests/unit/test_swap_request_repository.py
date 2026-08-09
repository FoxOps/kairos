"""Tests for app/repositories/swap_request_repository.py::_preload_related's
target_shift_id branch - every other branch here is already exercised
indirectly through tests/integration/test_swap_routes.py, but none of
those scenarios set target_shift_id (a reciprocal shift offered back
by the target), so that one bulk-load branch stays uncovered otherwise.
"""

from datetime import date, datetime, timedelta

from app import db
from app.models import Shift
from app.repositories.swap_request_repository import SwapRequestRepository


class TestPreloadRelatedTargetShift:
    def test_list_for_user_preloads_target_shift(
        self, test_app, test_swap_request, second_user, test_shift_type
    ):
        with test_app.app_context():
            shift_date = date.today() + timedelta(days=10)
            target_shift = Shift(
                date=shift_date,
                start_time=datetime.combine(shift_date, datetime.min.time()),
                end_time=datetime.combine(shift_date, datetime.max.time()),
                user_id=second_user.id,
                shift_type_id=test_shift_type.id,
            )
            db.session.add(target_shift)
            db.session.commit()

            test_swap_request.target_shift_id = target_shift.id
            db.session.commit()

            results = SwapRequestRepository.list_for_user(
                test_swap_request.requester_id
            )

            reloaded = next(sr for sr in results if sr.id == test_swap_request.id)
            assert reloaded.target_shift.id == target_shift.id
