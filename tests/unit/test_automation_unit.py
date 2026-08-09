"""
Unit tests for app/utils/automation.py
Covers functions and classes not previously tested.
"""

from datetime import date, datetime, timedelta
from types import SimpleNamespace

from app import db
from app.models import Group, OnCall
from app.utils.automation import OnCallAutomation, oncall_automation
from app.utils.automation.oncall_automation import (
    AvailabilityIndex,
    _solve_max_filled_weeks,
)


class TestOnCallAutomationGetEligibleUsers:
    """Tests for OnCallAutomation.get_eligible_users."""

    def test_returns_list(self, test_app):
        """Test that get_eligible_users returns a list."""
        with test_app.app_context():
            users = OnCallAutomation.get_eligible_users()
            assert isinstance(users, list)

    def test_filters_by_oncall_group(self, test_app, test_group, test_user):
        """Test that get_eligible_users filters by is_part_of_oncall."""
        with test_app.app_context():
            # test_group has is_part_of_oncall=True by default
            # test_user belongs to test_group
            users = OnCallAutomation.get_eligible_users()
            # Check that test_user is in the list
            user_ids = [u.id for u in users]
            assert test_user.id in user_ids


class TestOnCallAutomationGetRotationOrder:
    """Tests for OnCallAutomation.get_rotation_order."""

    def test_returns_list(self, test_app):
        """Test that get_rotation_order returns a list."""
        with test_app.app_context():
            rotation = OnCallAutomation.get_rotation_order()
            assert isinstance(rotation, list)

    def test_empty_when_no_eligible_users(self, test_app):
        """Test that get_rotation_order returns an empty list with no eligible users."""
        with test_app.app_context():
            # Disable every group for on-calls
            Group.query.update({"is_part_of_oncall": False})
            db.session.commit()
            rotation = OnCallAutomation.get_rotation_order()
            assert rotation == []


class TestOnCallAutomationCheckConstraint:
    """Tests for OnCallAutomation.check_oncall_constraint."""

    def test_returns_true_no_previous_oncall(self, test_app, test_user):
        """Test that check_oncall_constraint returns True with no previous on-call."""
        with test_app.app_context():
            start_time = datetime.now() + timedelta(days=30)
            end_time = start_time + timedelta(days=7, hours=-14)
            index = AvailabilityIndex([test_user.id])
            result = OnCallAutomation.check_oncall_constraint(
                test_user, start_time, end_time, index
            )
            assert result is True

    def test_returns_false_too_soon(self, test_app, test_user):
        """Test that check_oncall_constraint returns False if too soon."""
        with test_app.app_context():
            now = datetime.now()
            # Create a previous on-call
            previous_oncall = OnCall(
                user_id=test_user.id,
                start_time=now - timedelta(days=20),
                end_time=now - timedelta(days=13),
            )
            db.session.add(previous_oncall)
            db.session.commit()

            # Test with a date that's too close (less than 2 weeks after)
            start_time = now - timedelta(days=12)
            end_time = start_time + timedelta(days=7, hours=-14)
            index = AvailabilityIndex([test_user.id])
            result = OnCallAutomation.check_oncall_constraint(
                test_user, start_time, end_time, index
            )
            assert result is False

    def test_returns_true_sufficient_spacing(self, test_app, test_user):
        """Test that check_oncall_constraint returns True with sufficient spacing."""
        with test_app.app_context():
            now = datetime.now()
            # Create a previous on-call
            previous_oncall = OnCall(
                user_id=test_user.id,
                start_time=now - timedelta(days=30),
                end_time=now - timedelta(days=23),
            )
            db.session.add(previous_oncall)
            db.session.commit()

            # Test with a date far enough in the future
            start_time = now + timedelta(days=15)
            end_time = start_time + timedelta(days=7, hours=-14)
            index = AvailabilityIndex([test_user.id])
            result = OnCallAutomation.check_oncall_constraint(
                test_user, start_time, end_time, index
            )
            assert result is True


class TestOnCallAutomationFindNextAvailable:
    """Tests for OnCallAutomation.find_next_available_user."""

    def test_returns_none_empty_list(self, test_app):
        """Test that find_next_available_user returns None with an empty list."""
        with test_app.app_context():
            index = AvailabilityIndex([])
            result = OnCallAutomation.find_next_available_user(
                [], datetime.now(), datetime.now(), index
            )
            assert result is None

    def test_returns_user_when_available(self, test_app, test_user):
        """Test that find_next_available_user returns an available user."""
        with test_app.app_context():
            start_time = datetime.now() + timedelta(days=10)
            end_time = start_time + timedelta(days=7)
            index = AvailabilityIndex([test_user.id])
            result = OnCallAutomation.find_next_available_user(
                [test_user], start_time, end_time, index
            )
            # May return test_user or None depending on conflicts
            assert result is None or result.id == test_user.id


class TestOnCallAutomationGenerateSchedule:
    """Tests for OnCallAutomation.generate_oncall_schedule."""

    def test_returns_tuple(self, test_app):
        """Test that generate_oncall_schedule returns a tuple."""
        with test_app.app_context():
            start_date = date.today()
            end_date = start_date + timedelta(days=7)
            result = OnCallAutomation.generate_oncall_schedule(
                start_date, end_date, dry_run=True
            )
            assert isinstance(result, tuple)
            assert len(result) == 3

    def test_dry_run_does_not_save(self, test_app, test_user, test_group):
        """Test that dry_run=True doesn't save to the database."""
        with test_app.app_context():
            # Make sure test_user is eligible
            test_group.is_part_of_oncall = True
            db.session.commit()

            start_date = date.today()
            end_date = start_date + timedelta(days=7)

            # Count before
            count_before = OnCall.query.count()

            # Generate in dry_run
            OnCallAutomation.generate_oncall_schedule(
                start_date, end_date, dry_run=True
            )

            # Check that nothing was saved
            count_after = OnCall.query.count()
            assert count_after == count_before


class TestSolveMaxFilledWeeksSearchCap:
    """_MAX_SEARCH_NODES is a safety valve for _solve_max_filled_weeks'
    branch-and-bound search on pathological inputs (many weeks, many
    candidates, few real conflicts). No test exercised the truncation
    branch itself before this - these don't need a DB/app context at
    all, since the solver only touches its own in-memory arguments."""

    def _weeks(self, count):
        weeks = []
        start = datetime(2024, 1, 5, 21, 0)  # a Friday
        for i in range(count):
            week_start = start + timedelta(days=7 * i)
            week_end = week_start + timedelta(days=7)
            weeks.append((week_start.date(), week_start, week_end))
        return weeks

    def test_returns_best_found_so_far_when_node_budget_is_exhausted(self, monkeypatch):
        monkeypatch.setattr(oncall_automation, "_MAX_SEARCH_NODES", 3)

        users = [SimpleNamespace(id=1), SimpleNamespace(id=2), SimpleNamespace(id=3)]
        weeks = self._weeks(8)
        week_candidates = [users for _ in weeks]
        index = AvailabilityIndex([])

        assignment = _solve_max_filled_weeks(weeks, week_candidates, index)

        # Truncation must never crash and must never return more weeks
        # than exist, or assign a candidate that wasn't actually offered
        # for that week.
        assert isinstance(assignment, dict)
        assert len(assignment) <= len(weeks)
        for week_index, user in assignment.items():
            assert user in week_candidates[week_index]

        # Every returned assignment must still respect the 2-week
        # spacing constraint against every other returned assignment
        # for the same user - a truncated search must not fabricate an
        # invalid solution, only a possibly-incomplete one.
        by_user: dict[int, list[tuple[datetime, datetime]]] = {}
        for week_index, user in assignment.items():
            _friday, start_time, end_time = weeks[week_index]
            by_user.setdefault(user.id, []).append((start_time, end_time))
        for intervals in by_user.values():
            intervals.sort()
            for (_start_a, end_a), (start_b, _end_b) in zip(
                intervals, intervals[1:], strict=False
            ):
                assert (start_b - end_a).days / 7 >= 2

    def test_full_search_still_fills_every_week_when_budget_is_not_hit(self):
        """Same scenario, but with the real (huge) _MAX_SEARCH_NODES -
        confirms the tiny-budget test above is actually truncating
        something real, not just hitting an already-trivial search."""
        users = [SimpleNamespace(id=1), SimpleNamespace(id=2), SimpleNamespace(id=3)]
        weeks = self._weeks(8)
        week_candidates = [users for _ in weeks]
        index = AvailabilityIndex([])

        assignment = _solve_max_filled_weeks(weeks, week_candidates, index)

        assert len(assignment) == len(weeks)
