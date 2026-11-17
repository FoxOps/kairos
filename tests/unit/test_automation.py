"""
Tests for the on-call solver primitives, the automation DB lookups and
the automation status page helpers. Legacy-engine generation tests
(generate_oncall_schedule/generate_full_schedule/fill_oncall_gaps/
capture_existing_assignments/...) were removed with that engine in
1.2.0 - the planner's own coverage lives in tests/unit/test_planner_*.py.
"""

from datetime import date, datetime, timedelta

from app import db
from app.models import OnCall, User
from app.services import AutomationAdminService
from app.utils.automation import get_automation_status, queries
from app.utils.automation.planner.oncall_solver import AvailabilityIndex


class TestAvailabilityIndex:
    def test_meets_spacing_constraint_checks_future_intervals_too(self, test_app):
        """meets_spacing_constraint()'s own docstring: a future on-call
        recorded for a user must also respect the spacing constraint,
        not just past ones - the "existing_start >= end_time" branch,
        distinct from the "already ended before this candidate" branch
        exercised elsewhere via the planner."""
        with test_app.app_context():
            index = AvailabilityIndex([], min_spacing_weeks=2)
            future_start = datetime(2024, 2, 1, 21, 0)
            future_end = future_start + timedelta(days=7, hours=-14)
            index.record_assignment(1, future_start, future_end)

            # Ends well before the recorded future interval starts, but
            # only 6 days apart - under the 2-week (14-day) minimum
            # spacing.
            candidate_start = datetime(2024, 1, 19, 21, 0)
            candidate_end = candidate_start + timedelta(days=7, hours=-14)

            assert (
                index.meets_spacing_constraint(1, candidate_start, candidate_end)
                is False
            )

    def test_meets_spacing_constraint_overlap_is_a_conflict_not_spacing(self, test_app):
        """An overlapping existing interval is has_oncall_conflict's own
        concern, not a spacing issue (see the method's own comment) -
        meets_spacing_constraint() must not report False for it."""
        with test_app.app_context():
            index = AvailabilityIndex([], min_spacing_weeks=2)
            existing_start = datetime(2024, 1, 5, 21, 0)
            existing_end = existing_start + timedelta(days=7, hours=-14)
            index.record_assignment(1, existing_start, existing_end)

            # Overlaps the existing interval directly.
            candidate_start = existing_start + timedelta(days=1)
            candidate_end = candidate_start + timedelta(days=7, hours=-14)

            assert (
                index.meets_spacing_constraint(1, candidate_start, candidate_end)
                is True
            )


class TestSolveMaxFilledWeeksSpacingOverlap:
    def test_overlapping_existing_interval_is_treated_as_a_conflict_not_spacing(
        self, test_app, test_user
    ):
        """_solve_max_filled_weeks()'s own local meets_spacing() has the
        same overlap-is-not-a-spacing-issue branch as
        AvailabilityIndex.meets_spacing_constraint() (see that method's
        docstring) - week_candidates are always pre-filtered upstream
        to exclude a user with a genuinely conflicting on-call for that
        exact week (see this function's own docstring), so this branch
        is only reachable by constructing the inputs directly rather
        than through the real planner pipeline."""
        from app.utils.automation.planner.oncall_solver import (
            AvailabilityIndex,
            _solve_max_filled_weeks,
        )

        with test_app.app_context():
            week_start = datetime(2024, 1, 5, 21, 0)
            week_end = week_start + timedelta(days=7, hours=-14)
            weeks = [(date(2024, 1, 5), week_start, week_end)]
            week_candidates = [[test_user]]

            index = AvailabilityIndex([])
            # Directly recorded so it overlaps this exact week's own
            # interval - real callers never reach this state, since
            # week_candidates would already exclude test_user for a
            # week their own on-call conflicts with.
            index.record_assignment(test_user.id, week_start, week_end)

            assignment = _solve_max_filled_weeks(weeks, week_candidates, index)
            assert assignment == {0: test_user}


class TestOnCallQueries:
    """queries.get_oncall_users()/get_rotation_order()."""

    def test_get_eligible_users(self, test_app, test_group, test_user, second_user):
        """Test fetching the users eligible for on-calls."""
        with test_app.app_context():
            # Create a third user in the same group
            user3 = User(
                name="Third User",
                email="third@test.com",
                password_hash="third123",
                is_admin=False,
                group_id=test_group.id,
            )
            db.session.add(user3)
            db.session.commit()

            eligible_users = queries.get_oncall_users()
            # Every user in the group is eligible (is_part_of_oncall=True)
            assert len(eligible_users) == 3
            assert all(user.group.is_part_of_oncall for user in eligible_users)

    def test_get_rotation_order_default(
        self, test_app, test_group, test_user, second_user
    ):
        """Test the default rotation order (alphabetical)."""
        with test_app.app_context():
            # Create a third user
            user3 = User(
                name="Zebra User",  # Z to be last alphabetically
                email="zebra@test.com",
                password_hash="zebra123",
                is_admin=False,
                group_id=test_group.id,
            )
            db.session.add(user3)
            db.session.commit()

            rotation_order = queries.get_rotation_order()
            assert len(rotation_order) == 3
            # Check that the order is alphabetical
            # Note: Admin User starts with 'A', Second User with 'S', Zebra User with 'Z'
            names = [u.name for u in rotation_order]
            assert names == sorted(names)

    def test_get_rotation_order_custom(
        self, test_app, test_group, test_user, second_user
    ):
        """Test a custom rotation order."""
        with test_app.app_context():
            # Create a third user
            user3 = User(
                name="Third User",
                email="third@test.com",
                password_hash="third123",
                is_admin=False,
                group_id=test_group.id,
            )
            db.session.add(user3)
            db.session.commit()

            # Custom order: second_user, user3, test_user
            custom_order = [second_user.id, user3.id, test_user.id]
            rotation_order = queries.get_rotation_order(custom_order)

            assert len(rotation_order) == 3
            assert rotation_order[0].id == second_user.id
            assert rotation_order[1].id == user3.id
            assert rotation_order[2].id == test_user.id


class TestAutomationStatus:
    """get_automation_status()."""

    def test_get_automation_status(self, test_app, test_group, test_user, second_user):
        """Test fetching the automation status."""
        with test_app.app_context():
            # Create a third user
            user3 = User(
                name="Third User",
                email="third@test.com",
                password_hash="third123",
                is_admin=False,
                group_id=test_group.id,
            )
            db.session.add(user3)
            db.session.commit()

            status = get_automation_status()

            assert "oncall_count" in status
            assert "shift_count" in status
            assert "oncall_eligible_users" in status
            assert "shift_eligible_users" in status
            assert "next_available_oncall_date" in status

            # Check the values
            assert status["oncall_eligible_users"] == 3
            assert status["shift_eligible_users"] == 3

    def test_next_available_oncall_date_skips_already_covered_weeks(
        self, test_app, test_user
    ):
        """The very next anchor date already has an on-call - the search
        must keep walking forward a week at a time (status.py's own
        while-loop continuation branch) instead of returning an already-
        covered date."""
        with test_app.app_context():
            from datetime import date, datetime, timedelta

            today = date.today()
            next_friday = today
            while next_friday.weekday() != 4:
                next_friday += timedelta(days=1)

            start = datetime.combine(next_friday, datetime.min.time()).replace(hour=21)
            end = start + timedelta(days=7, hours=-14)
            oncall = OnCall(user_id=test_user.id, start_time=start, end_time=end)
            db.session.add(oncall)
            db.session.commit()

            status = get_automation_status()

            assert status["next_available_oncall_date"] != next_friday.strftime(
                "%Y-%m-%d"
            )
            assert status["next_available_oncall_date"] == (
                next_friday + timedelta(days=7)
            ).strftime("%Y-%m-%d")

    def test_next_available_oncall_date_advances_to_configured_anchor_weekday(
        self, test_app, test_group, test_user
    ):
        """status.py's own while-loop that walks `current_date` forward
        until it lands on the configured anchor weekday - only actually
        iterates when today isn't already that weekday, so a group
        anchor deliberately different from today's own weekday is used
        here instead of depending on which day the suite happens to
        run on."""
        from app.models import AutomationRule

        with test_app.app_context():
            today = date.today()
            not_today_weekday = (today.weekday() + 1) % 7
            AutomationRule.set(
                "oncall_anchor",
                {"weekday": not_today_weekday, "start_hour": 21, "end_hour": 7},
                group=test_group,
            )

            status = get_automation_status(group=test_group)

            next_date = datetime.strptime(
                status["next_available_oncall_date"], "%Y-%m-%d"
            ).date()
            assert next_date.weekday() == not_today_weekday
            assert next_date >= today


class TestDetectOnCallGaps:
    """Tests for queries.detect_oncall_gaps() - proactively
    surfaces real gaps (missing Fridays strictly between the earliest
    and latest existing on-call) so the admin doesn't have to guess
    which date range to widen the automation page's Période fields to
    (a real point of confusion: the page's default dates start at
    today, so a gap further in the past is invisible unless the admin
    already knows to look for it)."""

    def test_no_gaps_returns_empty(self, test_app, test_group, test_user, second_user):
        """3 users, no conflicts: a clean round-robin fills every week,
        leaving nothing for detect_oncall_gaps to find. (Only 2 users
        would leave some weeks legitimately unfillable - which isn't the
        "gap" scenario this
        test is about.)"""
        with test_app.app_context():
            user3 = User(
                name="Third",
                email="third-gaps@test.com",
                password_hash="x",
                is_admin=False,
                group_id=test_group.id,
            )
            db.session.add(user3)
            db.session.commit()
            rotation_order = [test_user.id, second_user.id, user3.id]

            AutomationAdminService.generate_full(
                date(2024, 1, 5), date(2024, 1, 26), rotation_order, dry_run=False
            )
            assert queries.detect_oncall_gaps() == []

    def test_detects_missing_week_between_two_existing_oncalls(
        self, test_app, test_group, test_user, second_user
    ):
        with test_app.app_context():
            user3 = User(
                name="Third",
                email="third-gaps2@test.com",
                password_hash="x",
                is_admin=False,
                group_id=test_group.id,
            )
            db.session.add(user3)
            db.session.commit()

            week1 = date(2024, 1, 5)
            week3 = date(2024, 1, 19)
            for friday, user_id in [(week1, test_user.id), (week3, second_user.id)]:
                start_time = datetime.combine(friday, datetime.min.time()).replace(
                    hour=21
                )
                end_time = start_time + timedelta(days=7, hours=-14)
                db.session.add(
                    OnCall(user_id=user_id, start_time=start_time, end_time=end_time)
                )
            db.session.commit()

            gaps = queries.detect_oncall_gaps()
            assert gaps == [date(2024, 1, 12)]

    def test_does_not_flag_future_ungenerated_weeks(
        self, test_app, test_group, test_user
    ):
        """A single existing on-call (or none at all) has no "interior"
        - nothing after it is a gap, it's just not generated yet."""
        with test_app.app_context():
            start_time = datetime.combine(
                date(2024, 1, 5), datetime.min.time()
            ).replace(hour=21)
            end_time = start_time + timedelta(days=7, hours=-14)
            db.session.add(
                OnCall(user_id=test_user.id, start_time=start_time, end_time=end_time)
            )
            db.session.commit()

            assert queries.detect_oncall_gaps() == []

    def test_empty_when_no_oncalls_at_all(self, test_app):
        with test_app.app_context():
            assert queries.detect_oncall_gaps() == []
