"""AutomationAdminService.rebalance_after_leave() - the automatic
leave-triggered rebalance. Engine-agnostic behavior tests moved from the
former tests/unit/test_advanced_shift_automation.py when the legacy
engine was removed (1.2.0); dry-run-only and legacy-internal tests were
dropped with it. New-engine-specific coverage lives in
tests/integration/test_leave_rebalance_new_engine.py."""

from datetime import date, datetime, timedelta

import pytest
from werkzeug.security import generate_password_hash

from app import db
from app.models import AutomationConfig, Group, Leave, OnCall, Shift, User
from app.services import AutomationAdminService


class TestRebalanceAfterLeave:
    """Tests for rebalancing after adding a leave."""

    def test_rebalance_after_leave_does_not_duplicate_adjacent_oncalls(
        self, test_app, test_group, test_user, second_user
    ):
        """Regression test: the period regenerated after a leave is
        extended by ±30 days (padding) around the affected Fridays, and
        can therefore include on-calls for OTHER Fridays already
        assigned to other users. The old code only removed the leave
        owner's own on-calls (leave.user_id) before regenerating across
        the whole extended period, creating duplicate on-calls on
        adjacent Fridays unrelated to the leave."""
        with test_app.app_context():
            user3 = User(
                name="Third User",
                email="third@test.com",
                password_hash=generate_password_hash("third-password"),
                is_admin=False,
                group_id=test_group.id,
            )
            db.session.add(user3)
            db.session.commit()

            friday_before = date(2023, 12, 1)
            friday_leave = date(2023, 12, 8)
            friday_after = date(2023, 12, 15)

            def make_oncall(user_id, friday):
                start = datetime.combine(friday, datetime.min.time()).replace(hour=21)
                end = start + timedelta(days=7, hours=-14)
                return OnCall(user_id=user_id, start_time=start, end_time=end)

            db.session.add(make_oncall(test_user.id, friday_before))
            db.session.add(make_oncall(second_user.id, friday_leave))
            db.session.add(make_oncall(user3.id, friday_after))
            db.session.commit()

            # second_user goes on leave during their own on-call week
            leave = Leave(
                user_id=second_user.id,
                start_date=date(2023, 12, 10),
                end_date=date(2023, 12, 11),
            )
            db.session.add(leave)
            db.session.commit()

            AutomationAdminService.rebalance_after_leave(leave)

            for friday in (friday_before, friday_leave, friday_after):
                day_start = datetime.combine(friday, datetime.min.time())
                count = OnCall.query.filter(
                    OnCall.start_time == day_start.replace(hour=21)
                ).count()
                assert count == 1, (
                    f"{count} on-calls found for Friday {friday} "
                    "(expected duplicate absent with the fix)"
                )

    def test_rebalance_after_leave_deletes_existing_shifts(
        self, test_app, test_group, test_user, test_shift_type
    ):
        """Existing shifts of the user on leave actually get deleted on a
        rebalanced day."""
        with test_app.app_context():
            leave_date = date(2023, 12, 15)
            existing_shift = Shift(
                date=leave_date,
                start_time=datetime.combine(leave_date, datetime.min.time()).replace(
                    hour=7
                ),
                end_time=datetime.combine(leave_date, datetime.min.time()).replace(
                    hour=15
                ),
                user_id=test_user.id,
                shift_type_id=test_shift_type.id,
            )
            db.session.add(existing_shift)
            leave = Leave(
                user_id=test_user.id, start_date=leave_date, end_date=leave_date
            )
            db.session.add(leave)
            db.session.commit()
            existing_shift_id = existing_shift.id

            AutomationAdminService.rebalance_after_leave(leave)
            assert db.session.get(Shift, existing_shift_id) is None

    def test_rebalance_after_leave_does_not_lock_out_window_on_future_oncalls(
        self, test_app, test_group, test_user, second_user
    ):
        """Regression test for a real production incident: rebalance_
        after_leave() only regenerates a ±30-day window around the
        leave, leaving on-calls *outside* that window (including ones
        further in the future than the window itself) untouched. A
        version of AvailabilityIndex/meets_spacing_constraint that only
        tracked "the single most recently created on-call" per user
        (rather than checking every known interval, both before and
        after) would treat one of those future on-calls as if it were
        the immediately preceding one - computing a nonsensical
        negative gap that failed the 2-week spacing check for every
        candidate on every week of the whole window, even with zero
        real leave conflicts. Confirmed against a real deployment's
        data (4 eligible users, one mid-window leave) before this fix:
        100% of the window (12/12 weeks) came back unfilled."""
        with test_app.app_context():
            user3 = User(
                name="Third User",
                email="third@test.com",
                password_hash="third123",
                is_admin=False,
                group_id=test_group.id,
            )
            user4 = User(
                name="Fourth User",
                email="fourth@test.com",
                password_hash="fourth123",
                is_admin=False,
                group_id=test_group.id,
            )
            db.session.add_all([user3, user4])
            db.session.commit()

            rotation_order = [test_user.id, second_user.id, user3.id, user4.id]
            AutomationConfig.set_rotation_order(rotation_order)

            # A clean, conflict-free schedule already exists across a
            # wide span - crucially including on-calls *after* the leave
            # below's ±30-day rebalance window, left untouched by it.
            AutomationAdminService.generate_full(
                date(2023, 11, 3), date(2024, 5, 31), rotation_order, dry_run=False
            )

            # Leave roughly in the middle of that schedule - its own
            # ±30-day rebalance window won't reach the tail end of the
            # existing future on-calls, which is exactly the scenario
            # that exposed the bug (on-calls existing *after* the
            # window, not just before it).
            leave = Leave(
                user_id=test_user.id,
                start_date=date(2024, 1, 3),
                end_date=date(2024, 1, 18),
            )
            db.session.add(leave)
            db.session.commit()

            (
                _shifts,
                _messages,
                unfilled_oncall_dates,
                _failed,
                _failed_oncall,
                _unfilled_shifts,
            ) = AutomationAdminService.rebalance_after_leave(leave)

            assert unfilled_oncall_dates == []

    def test_rebalance_after_leave_preserves_unaffected_weeks(
        self, test_app, test_group, test_user, second_user
    ):
        """Real user report: automatic rebalances after a leave
        reshuffled weeks that had nothing to do with the leave, slowly
        drifting the rotation over many successive leaves. The
        rebalance's on-call regeneration now prefers keeping each
        week's existing occupant (captured before the window is wiped)
        over blindly replaying the rotation order.

        With ample rotation slack (6 users here), replacing the single
        leave-affected week's occupant doesn't force a legal-spacing
        cascade onto any other week (unlike a tight 3-4 user pool,
        where the replacement candidate's own nearby slot can collide -
        a real, expected reshuffle in that case, not a bug - see
        TestOnCallMaxFillSearch for that scenario). So here every other
        week in the window must come out exactly as it went in."""
        with test_app.app_context():
            extra_users = []
            for i in range(4):
                u = User(
                    name=f"Extra User {i}",
                    email=f"extra{i}@test.com",
                    password_hash="extra123",
                    is_admin=False,
                    group_id=test_group.id,
                )
                db.session.add(u)
                extra_users.append(u)
            db.session.commit()

            rotation_order = [test_user.id, second_user.id] + [
                u.id for u in extra_users
            ]
            AutomationConfig.set_rotation_order(rotation_order)

            AutomationAdminService.generate_full(
                date(2023, 11, 3), date(2024, 3, 1), rotation_order, dry_run=False
            )

            before = {
                oc.start_time.date(): oc.user_id
                for oc in OnCall.query.filter(
                    OnCall.start_time >= datetime(2023, 12, 1),
                    OnCall.start_time <= datetime(2024, 2, 1),
                ).all()
            }

            leave = Leave(
                user_id=test_user.id,
                start_date=date(2024, 1, 3),
                end_date=date(2024, 1, 5),
            )
            db.session.add(leave)
            db.session.commit()

            AutomationAdminService.rebalance_after_leave(leave)

            after = {
                oc.start_time.date(): oc.user_id
                for oc in OnCall.query.filter(
                    OnCall.start_time >= datetime(2023, 12, 1),
                    OnCall.start_time <= datetime(2024, 2, 1),
                ).all()
            }

            # Every week except the one whose occupant went on leave
            # must be completely unchanged. The leave (Jan 3-5, a
            # Wed-Fri) overlaps the on-call that *started* the
            # previous Friday (Dec 29 21h -> Jan 5 07h), not the
            # calendar week the leave dates themselves fall in.
            leave_week = date(2023, 12, 29)
            unchanged_weeks = {d: u for d, u in before.items() if d != leave_week}
            for friday, user_id in unchanged_weeks.items():
                assert after.get(friday) == user_id, (
                    f"week {friday} changed from {user_id} to "
                    f"{after.get(friday)} despite no conflict"
                )

    def test_rebalance_after_leave_commits_once_on_success(
        self, test_app, test_group, test_user, second_user
    ):
        """A successful rebalance must actually persist
        the regenerated on-calls and shifts (a single final commit, no
        lost intermediate commits)."""
        with test_app.app_context():
            friday = date(2023, 12, 15)
            start_time = datetime.combine(friday, datetime.min.time()).replace(hour=21)
            end_time = start_time + timedelta(days=7, hours=-14)
            oncall = OnCall(
                user_id=test_user.id, start_time=start_time, end_time=end_time
            )
            db.session.add(oncall)

            leave = Leave(
                user_id=test_user.id,
                start_date=date(2023, 12, 16),
                end_date=date(2023, 12, 18),
            )
            db.session.add(leave)
            db.session.commit()

            (
                regenerated_shifts,
                messages,
                _unfilled,
                _failed,
                _failed_oncall,
                _unfilled_shifts,
            ) = AutomationAdminService.rebalance_after_leave(leave)

            # test_user's old on-call for this period was indeed deleted
            # and that deletion persisted (not just flush()'d then lost
            # for lack of a commit). Checked on (user, start_time) rather
            # than id: SQLite may reuse a deleted rowid for the new
            # on-call regenerated on the same date.
            assert (
                OnCall.query.filter_by(
                    user_id=test_user.id, start_time=start_time
                ).first()
                is None
            )
            # The returned regenerated shifts must also exist in the database.
            assert len(regenerated_shifts) > 0
            # (presentation namespaces, not ORM rows - see
            # plan_shift_namespaces())
            for shift in regenerated_shifts:
                assert (
                    Shift.query.filter_by(
                        user_id=shift.user.id, date=shift.date
                    ).first()
                    is not None
                )

    def test_rebalance_after_leave_crossing_year_boundary(
        self, test_app, test_group, test_user, second_user
    ):
        """No test previously exercised the ±30-day padding window
        (see this method's own docstring) crossing a calendar year
        boundary - a plausible spot for a latent date-arithmetic bug
        (e.g. any code computing "next year" or formatting dates as
        strings instead of using plain date/timedelta math). A leave
        during the last on-call week of December pads the regeneration
        window on both sides by 30 days, reaching back into November
        and forward into February of the following year."""
        with test_app.app_context():
            # A 3rd user is required: with only 2 rotating users, the
            # default 2-week minimum on-call spacing constraint makes
            # every other consecutive Friday unfillable regardless of
            # the year-boundary question this test targets (confirmed
            # by first running this test with just test_user/
            # second_user: 3 Fridays came back unfilled with a
            # "délai légal non respecté" warning, an expected
            # consequence of too few users, not a bug).
            user3 = User(
                name="Third User Boundary",
                email="third-boundary@test.com",
                password_hash=generate_password_hash("third-password"),
                is_admin=False,
                group_id=test_group.id,
            )
            db.session.add(user3)
            db.session.commit()

            # Last Friday of 2023, on-call spans the year boundary
            # itself (Fri 29/12/2023 21:00 -> Fri 05/01/2024 07:00).
            friday = date(2023, 12, 29)
            start_time = datetime.combine(friday, datetime.min.time()).replace(hour=21)
            end_time = start_time + timedelta(days=7, hours=-14)
            oncall = OnCall(
                user_id=test_user.id, start_time=start_time, end_time=end_time
            )
            db.session.add(oncall)

            # Leave falls inside that on-call week, in January of the
            # new year.
            leave = Leave(
                user_id=test_user.id,
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 2),
            )
            db.session.add(leave)
            db.session.commit()

            (
                regenerated_shifts,
                messages,
                _unfilled,
                failed_shift_dates,
                failed_oncall_period,
                _unfilled_shifts,
            ) = AutomationAdminService.rebalance_after_leave(leave)

            # No day/section in the padded window (roughly late
            # November 2023 through early February 2024) failed.
            assert failed_shift_dates == []
            assert failed_oncall_period == []

            # The old on-call spanning the boundary was replaced by a
            # freshly regenerated one for the same Friday, still
            # correctly dated in 2023 (not shifted a year by mistake).
            regenerated_oncall = OnCall.query.filter(
                OnCall.start_time == start_time
            ).first()
            assert regenerated_oncall is not None
            assert regenerated_oncall.start_time.year == 2023
            assert regenerated_oncall.end_time.year == 2024

            # Shifts were regenerated into January AND February of the
            # new year, both with the correct year - not silently
            # dropped or misdated at the boundary.
            shift_years = {shift.date.year for shift in regenerated_shifts}
            assert 2023 in shift_years
            assert 2024 in shift_years
            february_shifts = [
                shift for shift in regenerated_shifts if shift.date.month == 2
            ]
            assert february_shifts, (
                "the +30 day padding past the last Friday (05/01/2024) "
                "should reach into February 2024"
            )

    def test_rebalance_after_leave_per_group_mode_does_not_lose_other_groups_oncall(
        self, test_app, test_group, test_user
    ):
        """Regression test: under oncall_scheduling_mode="per_group",
        concurrent on-calls (one per group, for the same Friday) are
        expected and valid. A leave for a group-A user rebalancing
        group A's own window must not wipe a concurrent group-B
        on-call that happens to fall in the same ±30-day window and
        then fail to restore it (the regeneration, correctly scoped to
        group A only, has no way to recreate group B's on-call). Both
        rows here have no group_id snapshot (manual creation) - the
        planner adapter used to key both by (friday, None), so group B's
        row overwrote group A's and was then deleted as "removed"
        (1.2.0, see planner/adapters.py::_oncall_scope)."""
        from app.services import SettingsService

        SettingsService.set_oncall_scheduling_mode("per_group")

        group_b = Group(name="Rebalance Group B", is_part_of_oncall=True)
        db.session.add(group_b)
        db.session.commit()
        user_b = User(
            name="Group B User",
            email="group-b-rebalance@test.com",
            password_hash=generate_password_hash("password123"),
            is_admin=False,
            group_id=group_b.id,
        )
        db.session.add(user_b)
        db.session.commit()

        friday = date(2023, 12, 15)
        start_time = datetime.combine(friday, datetime.min.time()).replace(hour=21)
        end_time = start_time + timedelta(days=7, hours=-14)

        group_a_oncall = OnCall(
            user_id=test_user.id, start_time=start_time, end_time=end_time
        )
        group_b_oncall = OnCall(
            user_id=user_b.id, start_time=start_time, end_time=end_time
        )
        db.session.add_all([group_a_oncall, group_b_oncall])
        db.session.commit()
        group_b_oncall_id = group_b_oncall.id

        leave = Leave(
            user_id=test_user.id,
            start_date=date(2023, 12, 16),
            end_date=date(2023, 12, 18),
        )
        db.session.add(leave)
        db.session.commit()

        AutomationAdminService.rebalance_after_leave(leave)

        # Group B's on-call must survive completely untouched - same
        # row, same user, same times - even though group A's own
        # on-call for that same Friday was correctly regenerated.
        survivor = db.session.get(OnCall, group_b_oncall_id)
        assert survivor is not None
        assert survivor.user_id == user_b.id
        assert survivor.start_time == start_time
        assert survivor.end_time == end_time

    def test_rebalance_after_leave_per_group_mode_honors_group_rule_override(
        self, test_app, test_group, test_user, second_user
    ):
        """The leave-owner's own Group's rule overrides (e.g. a
        custom on-call anchor weekday) must actually be resolved
        during the rebalance, not the org-wide default - mirrors the
        same per-group rule-value gating already covered for
        check_shift_rule_violations()/check_oncall_rule_violations()."""
        from app.models import AutomationRule
        from app.services import SettingsService

        SettingsService.set_oncall_scheduling_mode("per_group")

        user3 = User(
            name="Third User Rebalance Group",
            email="third-rebalance-group@test.com",
            password_hash=generate_password_hash("third-password"),
            is_admin=False,
            group_id=test_group.id,
        )
        db.session.add(user3)
        db.session.commit()

        # test_group's own override: on-call weeks start on Thursday
        # (weekday=3), not the org-wide default Friday (weekday=4).
        AutomationRule.set(
            "oncall_anchor",
            {"weekday": 3, "start_hour": 21, "end_hour": 7},
            group=test_group,
        )

        thursday = date(2023, 12, 14)
        start_time = datetime.combine(thursday, datetime.min.time()).replace(hour=21)
        end_time = start_time + timedelta(days=7, hours=-14)
        db.session.add(
            OnCall(user_id=test_user.id, start_time=start_time, end_time=end_time)
        )
        db.session.commit()

        leave = Leave(
            user_id=test_user.id,
            start_date=date(2023, 12, 15),
            end_date=date(2023, 12, 16),
        )
        db.session.add(leave)
        db.session.commit()

        AutomationAdminService.rebalance_after_leave(leave)

        # The regenerated on-calls in this window must still start on
        # Thursday (the group's own override), not fall back to the
        # org-wide Friday default.
        regenerated = OnCall.query.filter(
            OnCall.start_time >= datetime.combine(thursday, datetime.min.time())
        ).all()
        assert regenerated
        assert all(oc.start_time.weekday() == 3 for oc in regenerated)

    def test_rebalance_after_leave_setup_failure_rolls_back_and_reraises(
        self, test_app, test_group, test_user, monkeypatch
    ):
        """A failure in the setup step (before the per-day loop even
        starts) - nothing has been generated yet, so this is a full
        rollback + re-raise, not the per-day isolation used once the
        loop is under way (see this method's own docstring)."""
        leave = Leave(
            user_id=test_user.id,
            start_date=date(2023, 12, 15),
            end_date=date(2023, 12, 15),
        )
        db.session.add(leave)
        db.session.commit()

        from app.services import SettingsService

        monkeypatch.setattr(
            SettingsService,
            "get_shift_scheduling_mode",
            lambda: (_ for _ in ()).throw(RuntimeError("boom")),
        )

        with pytest.raises(RuntimeError):
            AutomationAdminService.rebalance_after_leave(leave)
