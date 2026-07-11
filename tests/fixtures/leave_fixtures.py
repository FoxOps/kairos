"""Fixtures liées aux congés."""

from datetime import date, timedelta

import pytest

from app import db
from app.models import Leave


@pytest.fixture
def test_leave(test_app, test_user):
    """Crée un congé de test."""
    leave = Leave(
        user_id=test_user.id,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=5),
    )
    db.session.add(leave)
    db.session.commit()
    return leave
