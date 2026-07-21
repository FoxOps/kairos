"""
Tests for the on-call and shift automation module.
"""

from datetime import date, datetime, timedelta

from app import db
from app.models import Group, Leave, OnCall, User
from app.utils.automation import (
    AdvancedShiftAutomation,
    OnCallAutomation,
    get_automation_status,
)
from app.utils.automation.oncall_automation import AvailabilityIndex


class TestOnCallAutomation:
    """Tests for the on-call automation."""

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

            eligible_users = OnCallAutomation.get_eligible_users()
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

            rotation_order = OnCallAutomation.get_rotation_order()
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
            rotation_order = OnCallAutomation.get_rotation_order(custom_order)

            assert len(rotation_order) == 3
            assert rotation_order[0].id == second_user.id
            assert rotation_order[1].id == user3.id
            assert rotation_order[2].id == test_user.id

    def test_find_next_available_user(
        self, test_app, test_group, test_user, second_user
    ):
        """Test finding the next available user."""
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

            rotation_order = [test_user, second_user, user3]

            # Create an existing on-call for test_user
            start_time = datetime(2024, 1, 5, 21, 0)  # Friday, January 5, 2024 at 21h
            end_time = start_time + timedelta(days=7, hours=-14)

            oncall = OnCall(
                user_id=test_user.id, start_time=start_time, end_time=end_time
            )
            db.session.add(oncall)
            db.session.commit()

            # Find an available user for the same period
            index = AvailabilityIndex([test_user.id, second_user.id, user3.id])
            available_user = OnCallAutomation.find_next_available_user(
                rotation_order, start_time, end_time, index
            )

            # test_user isn't available, so second_user should be returned
            assert available_user is not None
            assert available_user.id == second_user.id

            # Clean up
            db.session.delete(oncall)
            db.session.commit()

    def test_generate_oncall_schedule_dry_run(
        self, test_app, test_group, test_user, second_user
    ):
        """Test generating on-calls in dry-run mode."""
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

            start_date = date(2024, 1, 5)  # Friday
            end_date = date(2024, 2, 23)  # 8 weeks later

            oncalls, messages, _unfilled = OnCallAutomation.generate_oncall_schedule(
                start_date, end_date, dry_run=True
            )

            # Should generate 7 or 8 on-calls depending on the exact end date
            assert len(oncalls) >= 7
            assert len(messages) > 0

            # Check that the on-calls are spaced one week apart
            for i in range(1, len(oncalls)):
                assert oncalls[i].start_time == oncalls[i - 1].start_time + timedelta(
                    days=7
                )

    def test_generate_oncall_schedule_summary_message_translates_to_english(
        self, test_app, test_group, test_user, second_user
    ):
        """Regression guard: OnCallAutomation's summary message used to
        be a raw French f-string, never wrapped in _(), so it ignored
        the acting admin's language preference entirely."""
        from flask_babel import force_locale

        with test_app.app_context(), force_locale("en"):
            start_date = date(2024, 1, 5)  # Friday
            end_date = date(2024, 1, 19)

            _oncalls, messages, _unfilled = OnCallAutomation.generate_oncall_schedule(
                start_date, end_date, dry_run=True
            )

            assert any("on-call" in msg.lower() for msg in messages)
            assert not any("astreinte" in msg.lower() for msg in messages)

    def test_generate_oncall_schedule_with_rotation(
        self, test_app, test_group, test_user, second_user
    ):
        """Test generation with a custom rotation order."""
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

            start_date = date(2024, 1, 5)  # Friday
            end_date = date(2024, 1, 19)  # 2 weeks later

            # Custom order: second_user, test_user, user3
            rotation_order = [second_user.id, test_user.id, user3.id]

            oncalls, messages, _unfilled = OnCallAutomation.generate_oncall_schedule(
                start_date, end_date, rotation_order, dry_run=True
            )

            # end_date inclusive: 3 Fridays (01/05, 01/12, 01/19).
            assert len(oncalls) == 3
            # The first on-call should be for second_user
            assert oncalls[0].user_id == second_user.id
            # The second on-call should be for test_user
            assert oncalls[1].user_id == test_user.id


class TestFullScheduleGeneration:
    """Tests for the full schedule generation."""

    def test_generate_full_schedule_dry_run(
        self, test_app, test_group, test_user, second_user, test_shift_type
    ):
        """Test the full generation in dry-run mode."""
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

            start_date = date(2024, 1, 5)  # Friday
            end_date = date(2024, 1, 19)  # 2 weeks later

            # AdvancedShiftAutomation.generate_full_schedule only
            # generates shifts (business days); on-calls are generated
            # separately by OnCallAutomation.generate_oncall_schedule.
            shifts, messages, _unfilled_shifts = (
                AdvancedShiftAutomation.generate_full_schedule(
                    start_date, end_date, dry_run=True
                )
            )

            assert len(shifts) > 0
            assert len(messages) > 0

            oncalls, oncall_messages, _unfilled = (
                OnCallAutomation.generate_oncall_schedule(
                    start_date, end_date, dry_run=True
                )
            )
            # end_date inclusive: 3 Fridays (01/05, 01/12, 01/19).
            assert len(oncalls) == 3

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


class TestEdgeCases:
    """Tests for edge cases."""

    def test_generate_oncall_no_eligible_users(self, test_app):
        """Test generating on-calls with no eligible users."""
        with test_app.app_context():
            # Create a group without is_part_of_oncall
            group = Group(
                name="No OnCall", is_part_of_schedule=True, is_part_of_oncall=False
            )
            db.session.add(group)
            db.session.commit()

            start_date = date(2024, 1, 5)
            end_date = date(2024, 1, 19)

            oncalls, messages, _unfilled = OnCallAutomation.generate_oncall_schedule(
                start_date, end_date, dry_run=True
            )

            assert len(oncalls) == 0
            assert any("Aucun utilisateur éligible" in msg for msg in messages)

    def test_generate_oncall_with_leave_conflict(
        self, test_app, test_group, test_user, second_user
    ):
        """Test generating on-calls with a leave conflict."""
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

            # Create a leave for test_user
            leave = Leave(
                user_id=test_user.id,
                start_date=date(2024, 1, 5),
                end_date=date(2024, 1, 12),
            )
            db.session.add(leave)
            db.session.commit()

            start_date = date(2024, 1, 5)  # Friday
            # Bounded to the end of the leave (not 2 weeks after like the
            # other tests): beyond that, test_user legitimately becomes
            # assignable again once their leave ends - this test
            # specifically checks the exclusion DURING the leave, not
            # beyond it.
            end_date = date(2024, 1, 12)

            oncalls, messages, _unfilled = OnCallAutomation.generate_oncall_schedule(
                start_date, end_date, dry_run=True
            )

            # end_date inclusive: 2 Fridays (01/05, 01/12), both covered
            # by test_user's leave.
            assert len(oncalls) == 2
            assert all(oncall.user_id != test_user.id for oncall in oncalls)

            # Clean up
            db.session.delete(leave)
            db.session.commit()


class TestOnCallMaxFillSearch:
    """Regression tests for the bug report: a plain greedy left-to-right
    pass can leave a week empty even though a different (still legal)
    assignment of the *other* weeks would have kept it fillable -
    generate_oncall_schedule() must only leave a week empty once no
    permutation of the period's assignments can fill it (see
    _solve_max_filled_weeks() in oncall_automation.py)."""

    def test_fills_a_week_that_greedy_would_leave_empty(
        self, test_app, test_group, test_user, second_user
    ):
        """3 users A/B/C, rotation order [A, B, C]. C is on leave only
        during week 3 (2024-01-19), every other week is conflict-free
        for everyone. The old greedy algorithm assigns A->week1,
        B->week2 (both the first available candidate in rotation
        order), leaving nobody free for week3 (A and B were both just
        used, C is on leave) - a real gap even though A->week1,
        C->week2, B->week3, A->week4, C->week5, B->week6 fills every
        single week and is just as legal. This asserts all 6 weeks get
        filled, not 5."""
        with test_app.app_context():
            user_c = User(
                name="Third User",
                email="third@test.com",
                password_hash="third123",
                is_admin=False,
                group_id=test_group.id,
            )
            db.session.add(user_c)
            db.session.commit()

            # A single day strictly inside week 3's on-call span
            # (Jan 19 21h -> Jan 26 07h) that doesn't touch the
            # Jan 19/Jan 26 boundary dates shared with weeks 2 and 4 -
            # blocks user_c for week 3 only.
            leave = Leave(
                user_id=user_c.id,
                start_date=date(2024, 1, 22),
                end_date=date(2024, 1, 22),
            )
            db.session.add(leave)
            db.session.commit()

            start_date = date(2024, 1, 5)  # Friday (week 1)
            end_date = date(2024, 2, 9)  # Friday (week 6)
            rotation_order = [test_user.id, second_user.id, user_c.id]

            oncalls, messages, unfilled_dates = (
                OnCallAutomation.generate_oncall_schedule(
                    start_date, end_date, rotation_order, dry_run=True
                )
            )

            assert unfilled_dates == []
            assert len(oncalls) == 6
            # user_c must never have been assigned week 3 itself.
            week3_oncall = next(
                o for o in oncalls if o.start_time.date() == date(2024, 1, 19)
            )
            assert week3_oncall.user_id != user_c.id
            assert not any("Aucune astreinte générée" in msg for msg in messages)

    def test_genuinely_unfillable_week_stays_empty(
        self, test_app, test_group, test_user, second_user
    ):
        """With only 2 rotating users, the 2-week legal spacing means
        each user can be reused only every 3rd week at best - so at
        most 2 out of every 3 weeks can ever be filled, regardless of
        which permutation is tried. The search must still report a gap
        here (not paper over a genuine impossibility)."""
        with test_app.app_context():
            start_date = date(2024, 1, 5)  # Friday
            end_date = date(2024, 1, 26)  # 4 Fridays, 2 users
            rotation_order = [test_user.id, second_user.id]

            oncalls, _messages, unfilled_dates = (
                OnCallAutomation.generate_oncall_schedule(
                    start_date, end_date, rotation_order, dry_run=True
                )
            )

            assert len(unfilled_dates) >= 1
            assert len(oncalls) + len(unfilled_dates) == 4


class TestFillOnCallGaps:
    """Tests for OnCallAutomation.fill_oncall_gaps() - the "combler les
    trous d'astreintes seulement" mode used by the "Rafraîchir" admin
    action: unlike generate_oncall_schedule(), it must never touch a
    Friday that already has an on-call (even a manually-assigned one),
    only create ones for Fridays that have none."""

    def test_leaves_existing_oncalls_untouched(
        self, test_app, test_group, test_user, second_user
    ):
        with test_app.app_context():
            user3 = User(
                name="Third User",
                email="third@test.com",
                password_hash="third123",
                is_admin=False,
                group_id=test_group.id,
            )
            db.session.add(user3)
            db.session.commit()

            rotation_order = [test_user.id, second_user.id, user3.id]

            # A manually-assigned on-call for week 1, deliberately
            # *not* the user rotation would have picked.
            week1_friday = date(2024, 1, 5)
            start_time = datetime.combine(week1_friday, datetime.min.time()).replace(
                hour=21
            )
            end_time = start_time + timedelta(days=7, hours=-14)
            manual_oncall = OnCall(
                user_id=user3.id, start_time=start_time, end_time=end_time
            )
            db.session.add(manual_oncall)
            db.session.commit()

            oncalls, _messages, unfilled_dates = OnCallAutomation.fill_oncall_gaps(
                date(2024, 1, 5), date(2024, 1, 19), rotation_order, dry_run=False
            )

            assert unfilled_dates == []
            # Only weeks 2 and 3 were actually missing - week 1 must
            # not appear among the newly created on-calls.
            assert {o.start_time.date() for o in oncalls} == {
                date(2024, 1, 12),
                date(2024, 1, 19),
            }
            # The manual assignment for week 1 is untouched.
            still_there = OnCall.query.filter_by(id=manual_oncall.id).first()
            assert still_there is not None
            assert still_there.user_id == user3.id

    def test_no_op_when_nothing_missing(
        self, test_app, test_group, test_user, second_user
    ):
        with test_app.app_context():
            rotation_order = [test_user.id, second_user.id]
            OnCallAutomation.generate_oncall_schedule(
                date(2024, 1, 5),
                date(2024, 1, 12),
                rotation_order,
                dry_run=False,
            )
            count_before = OnCall.query.count()

            oncalls, messages, unfilled_dates = OnCallAutomation.fill_oncall_gaps(
                date(2024, 1, 5), date(2024, 1, 12), rotation_order, dry_run=False
            )

            assert oncalls == []
            assert unfilled_dates == []
            assert OnCall.query.count() == count_before
            assert any("Aucune astreinte manquante" in msg for msg in messages)


class TestDetectOnCallGaps:
    """Tests for OnCallAutomation.detect_oncall_gaps() - proactively
    surfaces real gaps (missing Fridays strictly between the earliest
    and latest existing on-call) so the admin doesn't have to guess
    which date range to widen the automation page's Période fields to
    (a real point of confusion: the page's default dates start at
    today, so a gap further in the past is invisible unless the admin
    already knows to look for it)."""

    def test_no_gaps_returns_empty(self, test_app, test_group, test_user, second_user):
        """3 users, no conflicts: a clean round-robin fills every week,
        leaving nothing for detect_oncall_gaps to find. (Only 2 users
        would leave some weeks legitimately unfillable - see
        TestOnCallMaxFillSearch - which isn't the "gap" scenario this
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

            OnCallAutomation.generate_oncall_schedule(
                date(2024, 1, 5), date(2024, 1, 26), rotation_order, dry_run=False
            )
            assert OnCallAutomation.detect_oncall_gaps() == []

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

            gaps = OnCallAutomation.detect_oncall_gaps()
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

            assert OnCallAutomation.detect_oncall_gaps() == []

    def test_empty_when_no_oncalls_at_all(self, test_app):
        with test_app.app_context():
            assert OnCallAutomation.detect_oncall_gaps() == []
