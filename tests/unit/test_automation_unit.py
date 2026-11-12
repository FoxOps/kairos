"""
Unit tests for app/utils/automation/queries.py and the on-call solver's
search cap (app/utils/automation/planner/oncall_solver.py).
"""

from datetime import datetime, timedelta
from types import SimpleNamespace

from app import db
from app.models import Group
from app.utils.automation import queries
from app.utils.automation.planner import oncall_solver
from app.utils.automation.planner.oncall_solver import (
    AvailabilityIndex,
    _solve_max_filled_weeks,
)


class TestGetOnCallUsers:
    """Tests for queries.get_oncall_users."""

    def test_returns_list(self, test_app):
        """Test that get_oncall_users returns a list."""
        with test_app.app_context():
            users = queries.get_oncall_users()
            assert isinstance(users, list)

    def test_filters_by_oncall_group(self, test_app, test_group, test_user):
        """Test that get_oncall_users filters by is_part_of_oncall."""
        with test_app.app_context():
            # test_group has is_part_of_oncall=True by default
            # test_user belongs to test_group
            users = queries.get_oncall_users()
            # Check that test_user is in the list
            user_ids = [u.id for u in users]
            assert test_user.id in user_ids


class TestGetRotationOrder:
    """Tests for queries.get_rotation_order."""

    def test_returns_list(self, test_app):
        """Test that get_rotation_order returns a list."""
        with test_app.app_context():
            rotation = queries.get_rotation_order()
            assert isinstance(rotation, list)

    def test_empty_when_no_eligible_users(self, test_app):
        """Test that get_rotation_order returns an empty list with no eligible users."""
        with test_app.app_context():
            # Disable every group for on-calls
            Group.query.update({"is_part_of_oncall": False})
            db.session.commit()
            rotation = queries.get_rotation_order()
            assert rotation == []


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
        monkeypatch.setattr(oncall_solver, "_MAX_SEARCH_NODES", 3)

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
