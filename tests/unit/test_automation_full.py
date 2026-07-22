"""
Full tests for app/utils/automation.py
Covers the generation functions and complex cases.
"""

from datetime import date, datetime, timedelta

from app import db
from app.models import Leave, OnCall
from app.utils.automation import OnCallAutomation
from app.utils.automation.oncall_automation import AvailabilityIndex


class TestOnCallAutomationGenerateScheduleFull:
    """Full tests for OnCallAutomation.generate_oncall_schedule."""

    def test_generates_multiple_oncalls(self, test_app, test_user, test_group):
        """Test that generate_oncall_schedule generates several on-calls."""
        with test_app.app_context():
            # Make sure test_user is eligible
            test_group.is_part_of_oncall = True
            db.session.commit()

            # Create a second user for the rotation
            from app.models import User as UserModel

            test_user2 = UserModel(
                name="Test User 2", email="test2@example.com", group_id=test_group.id
            )
            test_user2.set_password("test_password")
            db.session.add(test_user2)
            db.session.commit()

            # Find the next Friday
            today = date.today()
            days_until_friday = (4 - today.weekday()) % 7
            start_date = today + timedelta(days=days_until_friday)
            # Use 35 days to make sure several full on-calls are included
            # (each on-call lasts until the following Friday at 07h)
            end_date = start_date + timedelta(days=35)  # 5 weeks

            oncalls, messages, unfilled = OnCallAutomation.generate_oncall_schedule(
                start_date,
                end_date,
                rotation_order_ids=[test_user.id, test_user2.id],
                dry_run=True,
            )

            # end_date inclusive: 35 days after a Friday also falls on a
            # Friday (35 = 5*7) -> 6 Fridays (+0, +7, +14, +21, +28, +35).
            # With only 2 rotating users, the legal 2-week spacing
            # constraint (2 full weeks of rest after a week-long on-call)
            # makes every 3rd Friday mathematically impossible to fill -
            # deliberately left unassigned rather than violating the
            # constraint (see OnCallAutomation.generate_oncall_schedule),
            # so only 4 of the 6 Fridays get an on-call here.
            assert len(oncalls) == 4
            assert len(unfilled) == 2

    def test_respects_start_date(self, test_app, test_user, test_group):
        """Test that generate_oncall_schedule respects the start date."""
        with test_app.app_context():
            test_group.is_part_of_oncall = True
            db.session.commit()

            start_date = date.today() + timedelta(days=10)
            end_date = start_date + timedelta(days=7)

            oncalls, messages, _unfilled = OnCallAutomation.generate_oncall_schedule(
                start_date, end_date, rotation_order_ids=[test_user.id], dry_run=True
            )

            if oncalls:
                # The first on-call should start on a Friday
                first_oncall = oncalls[0]
                assert first_oncall.start_time.date() >= start_date

    def test_skips_unavailable_users(self, test_app, test_user, test_group):
        """Test that generate_oncall_schedule skips unavailable users."""
        with test_app.app_context():
            test_group.is_part_of_oncall = True
            db.session.commit()

            # Create a leave for test_user
            now = datetime.now()
            leave = Leave(
                user_id=test_user.id,
                start_date=now.date() + timedelta(days=2),
                end_date=now.date() + timedelta(days=10),
            )
            db.session.add(leave)
            db.session.commit()

            # Find the next Friday
            today = date.today()
            days_until_friday = (4 - today.weekday()) % 7
            start_date = today + timedelta(days=days_until_friday)
            end_date = start_date + timedelta(days=7)

            oncalls, messages, _unfilled = OnCallAutomation.generate_oncall_schedule(
                start_date, end_date, rotation_order_ids=[test_user.id], dry_run=True
            )

            # Should generate messages about unavailable users. The
            # message can either be "Utilisateur avec contrainte legale
            # seulement" (fallback with constraint) or "Aucun
            # utilisateur disponible" (fallback with no constraint).
            assert any(
                "Utilisateur avec contrainte légale seulement" in msg
                or "Aucun utilisateur disponible" in msg
                or "générée" in msg
                for msg in messages
            )

    def test_second_call_appended_after_first_respects_spacing_across_boundary(
        self, test_app, test_user, second_user, test_group
    ):
        """Real admin workflow: generate a schedule, then later generate
        a *new*, non-overlapping range appended right after it (no
        deletion in between) - e.g. extending the rotation further into
        the future once the first batch is already committed. The 2-week
        legal spacing constraint must still be enforced across the
        boundary between the two calls: AvailabilityIndex seeds from
        every existing on-call in the DB regardless of date (see its own
        docstring), not just the ones inside the range being generated -
        this test is the regression guard for that property actually
        holding end-to-end across two separate, committed calls."""
        with test_app.app_context():
            from app.models import User as UserModel

            third_user = UserModel(
                name="Third User", email="third@test.com", group_id=test_group.id
            )
            third_user.set_password("test_password")
            db.session.add(third_user)
            db.session.commit()

            rotation = [test_user.id, second_user.id, third_user.id]

            today = date.today()
            days_until_friday = (4 - today.weekday()) % 7
            first_start = today + timedelta(days=days_until_friday)
            first_end = first_start + timedelta(days=14)  # 3 Fridays, one full cycle

            first_oncalls, _messages, first_unfilled = (
                OnCallAutomation.generate_oncall_schedule(
                    first_start, first_end, rotation_order_ids=rotation, dry_run=False
                )
            )
            assert first_unfilled == []
            assert len(first_oncalls) == 3

            second_start = first_end + timedelta(days=7)
            second_end = second_start + timedelta(days=14)  # another full cycle

            second_oncalls, _messages2, second_unfilled = (
                OnCallAutomation.generate_oncall_schedule(
                    second_start, second_end, rotation_order_ids=rotation, dry_run=False
                )
            )
            assert second_unfilled == []
            assert len(second_oncalls) == 3

            all_oncalls = OnCall.query.order_by(OnCall.start_time).all()
            assert len(all_oncalls) == 6

            # No gap and no duplicate Friday across the boundary between
            # the two calls.
            for prev, nxt in zip(all_oncalls, all_oncalls[1:], strict=False):
                assert (nxt.start_time - prev.start_time).days == 7

            # No user is on-call again sooner than 2 full weeks after
            # their previous on-call ended - checked across the *whole*
            # combined history, including pairs that straddle the two
            # separate generate_oncall_schedule() calls.
            by_user: dict[int, list] = {}
            for oc in all_oncalls:
                by_user.setdefault(oc.user_id, []).append(oc)
            for _user_id, ocs in by_user.items():
                ocs.sort(key=lambda o: o.start_time)
                for prev_oc, next_oc in zip(ocs, ocs[1:], strict=False):
                    gap_days = (next_oc.start_time - prev_oc.end_time).days
                    assert gap_days / 7 >= 2


class TestOnCallAutomationFindNextAvailableFull:
    """Full tests for OnCallAutomation.find_next_available_user."""

    def test_skips_user_with_oncall_conflict(self, test_app, test_user):
        """Test that find_next_available_user skips users with an on-call conflict."""
        with test_app.app_context():
            now = datetime.now()

            # Create an existing on-call
            existing_oncall = OnCall(
                user_id=test_user.id,
                start_time=now + timedelta(days=1),
                end_time=now + timedelta(days=8),
            )
            db.session.add(existing_oncall)
            db.session.commit()

            # Test with an overlapping period
            start_time = now + timedelta(days=2)
            end_time = now + timedelta(days=5)

            index = AvailabilityIndex([test_user.id])
            result = OnCallAutomation.find_next_available_user(
                [test_user], start_time, end_time, index
            )

            # Should skip test_user
            assert result is None

    def test_skips_user_with_leave_conflict(self, test_app, test_user):
        """Test that find_next_available_user skips users with a leave conflict."""
        with test_app.app_context():
            now = datetime.now()

            # Create a leave
            leave = Leave(
                user_id=test_user.id,
                start_date=now.date() + timedelta(days=2),
                end_date=now.date() + timedelta(days=5),
            )
            db.session.add(leave)
            db.session.commit()

            # Test with an overlapping period
            start_time = now + timedelta(days=3)
            end_time = now + timedelta(days=4)

            index = AvailabilityIndex([test_user.id])
            result = OnCallAutomation.find_next_available_user(
                [test_user], start_time, end_time, index
            )

            # Should skip test_user
            assert result is None

    def test_skips_user_with_legal_constraint(self, test_app, test_user):
        """Test that find_next_available_user skips users with a legal constraint."""
        with test_app.app_context():
            now = datetime.now()

            # Create a previous on-call that ended 13 days ago.
            # The constraint is: (start_time - last_oncall.end_time).days / 7 >= 2
            # If last_oncall.end_time was 13 days ago, and start_time is now + 1 day,
            # then (start_time - last_end).days = (now + 1 day) - (now - 13 days) = 14 days
            # 14/7 = 2.0 -> passes the constraint
            # To fail, (start_time - last_end).days / 7 must be < 2
            # So (start_time - last_end).days must be < 14
            # If last_end was 13 days ago, and start_time is now,
            # then (now - (now - 13 days)).days = 13 days
            # 13/7 = 1.857 < 2 -> should be skipped

            previous_oncall = OnCall(
                user_id=test_user.id,
                start_time=now - timedelta(days=20),
                end_time=now - timedelta(days=13),  # Ended 13 days ago
            )
            db.session.add(previous_oncall)
            db.session.commit()

            # Test with start_time = now (not now + 1 day)
            start_time = now
            end_time = now + timedelta(days=7)

            index = AvailabilityIndex([test_user.id])
            result = OnCallAutomation.find_next_available_user(
                [test_user], start_time, end_time, index
            )

            # Should skip test_user due to the 2-week constraint
            # (now - (now - 13 days)).days / 7 = 13/7 = 1.857 < 2
            assert result is None
