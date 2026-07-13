"""Fixtures liées aux shifts et types de shift."""

from datetime import date, datetime

import pytest

from app import db
from app.models import Shift, ShiftType


@pytest.fixture
def test_shift_type(test_app):
    """Crée un type de shift de test."""
    shift_type = ShiftType(name="morning", label="Matin", start_hour=7, end_hour=15)
    db.session.add(shift_type)
    db.session.commit()
    return shift_type


@pytest.fixture
def afternoon_shift_type(test_app):
    """Crée un type de shift pour l'après-midi."""
    shift_type = ShiftType(
        name="Afternoon",
        label="PM",
        start_hour=14,
        end_hour=18,
    )
    db.session.add(shift_type)
    db.session.commit()
    return shift_type


@pytest.fixture
def test_shift(test_app, test_user, test_shift_type):
    """Crée un shift de test."""
    shift = Shift(
        date=date.today(),
        start_time=datetime.combine(date.today(), datetime.min.time()),
        end_time=datetime.combine(date.today(), datetime.max.time()),
        user_id=test_user.id,
        shift_type_id=test_shift_type.id,
    )
    db.session.add(shift)
    db.session.commit()
    return shift
