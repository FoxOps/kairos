"""Fixtures liées aux demandes d'échange de shifts (SwapRequest)."""

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
    """Shift à venir appartenant à test_user, proposable à l'échange."""
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
    """Demande d'échange en attente : test_user propose test_swap_shift à second_user."""
    swap_request = SwapRequest(
        requester_id=test_user.id,
        shift_id=test_swap_shift.id,
        target_user_id=second_user.id,
        status=SwapRequest.PENDING,
    )
    db.session.add(swap_request)
    db.session.commit()
    return swap_request
