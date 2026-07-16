"""Fixtures for shift-swap requests (SwapRequest)."""

from datetime import date, datetime, timedelta

import pytest

from app import db
from app.models import Shift, SwapRequest


def _next_weekday(from_date: date) -> date:
    d = from_date
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


@pytest.fixture
def test_swap_shift(test_app, test_user, test_shift_type):
    """An upcoming shift owned by test_user, eligible to be offered for swap."""
    shift_date = _next_weekday(date.today() + timedelta(days=3))
    shift = Shift(
        date=shift_date,
        start_time=datetime.combine(shift_date, datetime.min.time()),
        end_time=datetime.combine(shift_date, datetime.max.time()),
        user_id=test_user.id,
        shift_type_id=test_shift_type.id,
    )
    db.session.add(shift)
    db.session.commit()
    return shift


@pytest.fixture
def test_swap_request(test_app, test_user, second_user, test_swap_shift):
    """A pending swap request: test_user offers test_swap_shift to
    second_user, still awaiting second_user's own confirmation."""
    swap_request = SwapRequest(
        requester_id=test_user.id,
        shift_id=test_swap_shift.id,
        target_user_id=second_user.id,
        status=SwapRequest.PENDING,
    )
    db.session.add(swap_request)
    db.session.commit()
    return swap_request


@pytest.fixture
def confirmed_swap_request(test_app, test_swap_request):
    """The same request as test_swap_request, but already confirmed by
    its target (AWAITING_ADMIN, no target_shift - one-way give-away) -
    for tests exercising the admin approve/reject/revert actions, which
    now only apply once the target has confirmed."""
    test_swap_request.status = SwapRequest.AWAITING_ADMIN
    db.session.commit()
    return test_swap_request
