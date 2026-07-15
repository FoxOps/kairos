"""On-call-related fixtures."""

from datetime import datetime, timedelta

import pytest

from app import db
from app.models import OnCall


@pytest.fixture
def test_oncall(test_app, test_user):
    """Create a test on-call."""
    oncall = OnCall(
        user_id=test_user.id,
        start_time=datetime.now(),
        end_time=datetime.now() + timedelta(days=7),
    )
    db.session.add(oncall)
    db.session.commit()
    return oncall
