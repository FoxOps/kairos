# ============================================================================
# ADVANCED SHIFT AUTOMATION (NEW BUSINESS RULES)
# ============================================================================

from datetime import date
from typing import TYPE_CHECKING

from flask_babel import gettext as _

if TYPE_CHECKING:
    # Models imported only for type annotations (as strings in this
    # file) - never at runtime, to avoid the circular import that the
    # deferred imports in each method already work around (see the
    # local `from app.models import ...` further below). Before this
    # block, these names weren't imported anywhere: harmless at runtime
    # (a quoted annotation is never evaluated), but broke any tool that
    # resolves them (mypy, typing.get_type_hints()).
    from app.models import Leave, OnCall, ShiftType, User

# Sentinel distinct from None: None is a valid value (no on-call that
# day) for oncall_today/oncall_user_last_week in determine_shift_for_user
# - a separate marker is needed to detect "argument not provided,
# compute it yourself" (historical behavior, preserved for callers who
# invoke the method in isolation).
_UNSET: "object" = object()


class AdvancedShiftAutomation:
    """
    Class managing advanced shift automation per the new business rules.

    Implemented rules:
    1. 1pm-9pm slot: Reserved for the on-call person IF they belong to a schedule group
    2. Slot rotation: If someone was on 1pm-9pm one week, they must be on 7am-3pm the following week
    3. Default slot: 9am-5pm for all other cases (several people can be on this slot)
    4. Leave case: If only 2 people are available, the person NOT on-call must be on 7am-3pm
    5. Legal constraint: No 2 consecutive on-calls - minimum 2 weeks without on-call between two on-calls
    """

    # Time slots
    SHIFT_07_15 = (7, 15)  # 7am-3pm
    SHIFT_09_17 = (9, 17)  # 9am-5pm
    SHIFT_13_21 = (13, 21)  # 1pm-9pm

    @staticmethod
    def get_shift_type_by_hours(start_hour: int, end_hour: int) -> "ShiftType":
        """Fetch or create a shift type based on the hours."""
        from app import db
        from app.models import ShiftType

        shift_type = ShiftType.query.filter_by(
            start_hour=start_hour, end_hour=end_hour
        ).first()
        if shift_type:
            return shift_type

        # Create a new shift type if needed
        name = f"{start_hour:02d}-{end_hour:02d}"
        label = f"{start_hour:02d}h-{end_hour:02d}h"

        new_shift_type = ShiftType(
            name=name, label=label, start_hour=start_hour, end_hour=end_hour
        )
        db.session.add(new_shift_type)
        db.session.flush()  # To get the ID
        return new_shift_type

    @staticmethod
    def get_users_in_schedule_groups() -> list:
        """Fetch users belonging to groups that can be added to the schedule."""
        from app.models import Group, User

        return User.query.join(Group).filter(Group.is_part_of_schedule.is_(True)).all()

    @staticmethod
    def get_available_users_for_date(date: "date") -> list:
        """Fetch users available for a given date (not on leave)."""
        from app import db
        from app.models import Leave

        eligible_users = AdvancedShiftAutomation.get_users_in_schedule_groups()

        if not eligible_users:
            return []

        # Optimization: fetch all eligible user_ids
        user_ids = [user.id for user in eligible_users]

        # Fetch all users on leave for this date in a single query
        users_on_leave = set()
        leave_conflicts = (
            db.session.query(Leave.user_id)
            .filter(
                Leave.user_id.in_(user_ids),
                Leave.start_date <= date,
                Leave.end_date >= date,
            )
            .all()
        )
        users_on_leave = {lc.user_id for lc in leave_conflicts}

        # Filter available users
        available_users = [
            user for user in eligible_users if user.id not in users_on_leave
        ]

        return available_users

    @staticmethod
    def get_oncall_for_date(date: "date") -> "OnCall | None":
        """Fetch the on-call (OnCall) covering the Monday-Friday shift
        week that `date` belongs to, for shift-assignment purposes only
        (see determine_shift_for_user()/handle_two_users_case() below -
        not a general "who is on call right now" lookup, see
        OnCall.is_active() for that). `date` must be a weekday
        (Monday-Friday) - the only callers in the real generation
        pipeline (generate_daily_shifts()) always skip weekends before
        reaching this method; the anchor computation below is only
        meaningful for Mon-Fri.

        Anchored to the Friday that starts this shift week (`date`'s
        Monday minus 3 days), not a naive interval overlap check: on the
        transition Friday itself two different on-calls genuinely
        overlap that calendar day (the one ending 7am that morning, and
        the new one starting 9pm that evening), and shift changes only
        happen on Monday, never on Friday - the person whose on-call is
        ENDING that Friday is still "this week's on-call" for shift
        purposes (1pm-9pm), while the person whose on-call is STARTING
        that evening isn't yet (they keep whatever they were already on
        the day before, until the following Monday). A plain interval
        overlap query can't distinguish the two and picks one of them
        arbitrarily via an unordered `.first()`."""
        from datetime import datetime, timedelta

        from app import db
        from app.models import OnCall

        week_monday = date - timedelta(days=date.weekday())
        anchor_friday = week_monday - timedelta(days=3)
        anchor_start = datetime.combine(anchor_friday, datetime.min.time()).replace(
            hour=21
        )

        # Optimization: use a query with JOIN to avoid lazy loading
        oncall = (
            db.session.query(OnCall)
            .options(db.joinedload(OnCall.user))
            .filter(OnCall.start_time == anchor_start)
            .first()
        )

        return oncall

    @staticmethod
    def get_oncall_user_for_date(date: "date") -> "User | None":
        """Fetch the on-call user for a given date."""
        oncall = AdvancedShiftAutomation.get_oncall_for_date(date)
        return oncall.user if oncall else None

    @staticmethod
    def determine_shift_for_user(
        user: "User",
        date: "date",
        oncall_today: "OnCall | None | object" = _UNSET,
        oncall_user_last_week: "User | None | object" = _UNSET,
    ) -> "tuple[int, int]":
        """
        Determine the shift slot for a user on a given date.

        Rules:
        1. If the user is "this week's on-call" (see get_oncall_for_date()
           - Monday through Friday, transition Friday included: the
           person whose on-call is ENDING that Friday, not the one
           starting that evening, since shift changes only happen on
           Monday) -> 1pm-9pm (if eligible)
        2. If the user was on-call the previous week (and not this week) -> 7am-3pm (rotation)
        3. Otherwise -> 9am-5pm (this is also what a user whose on-call
           starts on a transition Friday gets that day - same as the day
           before, since they're not "this week's on-call" for shift
           purposes until the following Monday)

        `oncall_today`/`oncall_user_last_week`: passed by the caller (a
        single query per day in generate_daily_shifts) instead of being
        queried once per user - they stay optional for callers that
        invoke this method in isolation (notably tests).
        """
        from datetime import timedelta
        from typing import cast

        # Rule 1: check whether the user is on-call this week - every
        # weekday of their on-call gets 1pm-9pm, Monday and Friday
        # included (an on-call runs Friday 9pm to the following Friday
        # 7am, so both transition Fridays are still on-call days).
        if oncall_today is _UNSET:
            oncall = AdvancedShiftAutomation.get_oncall_for_date(date)
        else:
            oncall = cast("OnCall | None", oncall_today)
        if oncall and oncall.user_id == user.id:
            from app import db
            from app.models import Group, User

            user_in_schedule = db.session.query(
                db.exists().where(
                    User.id == user.id,
                    User.group_id == Group.id,
                    Group.is_part_of_schedule.is_(True),
                )
            ).scalar()
            if user_in_schedule:
                return AdvancedShiftAutomation.SHIFT_13_21

        # Rule 2: check whether the user was on-call the previous week
        if oncall_user_last_week is _UNSET:
            previous_week_date = date - timedelta(days=7)
            previous_oncall_user = AdvancedShiftAutomation.get_oncall_user_for_date(
                previous_week_date
            )
        else:
            previous_oncall_user = cast("User | None", oncall_user_last_week)
        if previous_oncall_user and previous_oncall_user.id == user.id:
            return AdvancedShiftAutomation.SHIFT_07_15

        # Rule 3: default slot
        return AdvancedShiftAutomation.SHIFT_09_17

    @staticmethod
    def handle_two_users_case(available_users: list, date: "date") -> "dict":
        """
        Handle the special case where only 2 people are available. The
        on-call person is on 1pm-9pm, the other on 7am-3pm. No schedule-
        group check needed here: available_users is already derived from
        get_users_in_schedule_groups() (via get_available_users_for_date()),
        so the on-call person, if one of these 2, is necessarily already
        a schedule-group member.
        """
        if len(available_users) != 2:
            return {}

        oncall_user = AdvancedShiftAutomation.get_oncall_user_for_date(date)
        assignments = {}

        for user in available_users:
            if oncall_user and user.id == oncall_user.id:
                assignments[user] = AdvancedShiftAutomation.SHIFT_13_21
            else:
                assignments[user] = AdvancedShiftAutomation.SHIFT_07_15

        return assignments

    @staticmethod
    def generate_daily_shifts(
        date: "date", dry_run: bool = False, commit: bool = True
    ) -> "tuple[list, list]":
        """Generate the shifts for a day per the new business rules.

        `commit`: if False (used by rebalance_after_leave to make the
        whole rebalance atomic), changes are only flush()'d - visible in
        the current session but not persisted - and left for the caller
        to commit/rollback. Any exception during the flush is then not
        absorbed here: it propagates so the caller can undo the whole
        operation.
        """
        from datetime import datetime, timedelta

        from app import db
        from app.models import Shift

        messages = []
        generated_shifts = []

        if date.weekday() >= 5:
            return [], [
                _(
                    "⏭️ Pas de shift généré pour le %(date)s (week-end)",
                    date=date.strftime("%d/%m/%Y"),
                )
            ]

        available_users = AdvancedShiftAutomation.get_available_users_for_date(date)

        if not available_users:
            return [], [
                _(
                    "⚠️ Aucun utilisateur disponible pour le %(date)s",
                    date=date.strftime("%d/%m/%Y"),
                )
            ]

        # Rule 6: minimum headcount of 1 person. When only one person is
        # available (edge case, below the 2-person case handled below),
        # they're placed directly on 9am-5pm without going through
        # determine_shift_for_user/handle_two_users_case.
        if len(available_users) == 1:
            sole_user = available_users[0]
            start_hour, end_hour = AdvancedShiftAutomation.SHIFT_09_17
            shift_type = AdvancedShiftAutomation.get_shift_type_by_hours(
                start_hour, end_hour
            )
            start_time = datetime.combine(date, datetime.min.time()).replace(
                hour=start_hour
            )
            end_time = datetime.combine(date, datetime.min.time()).replace(
                hour=end_hour
            )
            shift = Shift(
                user_id=sole_user.id,
                shift_type_id=shift_type.id,
                start_time=start_time,
                end_time=end_time,
                date=date,
            )
            generated_shifts.append(shift)

            if not dry_run:
                db.session.add_all(generated_shifts)
                if commit:
                    try:
                        db.session.commit()
                    except Exception as e:
                        db.session.rollback()
                        messages.append(_("❌ Erreur : %(error)s", error=str(e)))
                        return [], messages
                else:
                    db.session.flush()

            messages.append(
                _(
                    "✅ 1 shift généré pour le %(date)s (effectif minimum : %(name)s)",
                    date=date.strftime("%d/%m/%Y"),
                    name=sole_user.name,
                )
            )
            return generated_shifts, messages

        # Special case: only 2 people available
        if len(available_users) == 2:
            assignments = AdvancedShiftAutomation.handle_two_users_case(
                available_users, date
            )
            if assignments:
                for user, (start_hour, end_hour) in assignments.items():
                    shift_type = AdvancedShiftAutomation.get_shift_type_by_hours(
                        start_hour, end_hour
                    )
                    start_time = datetime.combine(date, datetime.min.time()).replace(
                        hour=start_hour
                    )
                    end_time = datetime.combine(date, datetime.min.time()).replace(
                        hour=end_hour
                    )

                    shift = Shift(
                        user_id=user.id,
                        shift_type_id=shift_type.id,
                        start_time=start_time,
                        end_time=end_time,
                        date=date,
                    )
                    generated_shifts.append(shift)

                if not dry_run:
                    db.session.add_all(generated_shifts)
                    if commit:
                        try:
                            db.session.commit()
                        except Exception as e:
                            db.session.rollback()
                            messages.append(_("❌ Erreur : %(error)s", error=str(e)))
                            return [], messages
                    else:
                        db.session.flush()

                return generated_shifts, messages

        # Normal case: 3+ users
        # Optimization: use a set for available user_ids to avoid linear lookups
        available_user_ids = {user.id for user in available_users}
        schedule_users = AdvancedShiftAutomation.get_users_in_schedule_groups()

        # Fetched once for the day (instead of one OnCall query per user
        # in determine_shift_for_user - the day's on-call doesn't depend
        # on the user being iterated).
        oncall_today = AdvancedShiftAutomation.get_oncall_for_date(date)
        previous_week_date = date - timedelta(days=7)
        oncall_user_last_week = AdvancedShiftAutomation.get_oncall_user_for_date(
            previous_week_date
        )

        for user in schedule_users:
            if user.id not in available_user_ids:
                continue

            start_hour, end_hour = AdvancedShiftAutomation.determine_shift_for_user(
                user, date, oncall_today, oncall_user_last_week
            )
            shift_type = AdvancedShiftAutomation.get_shift_type_by_hours(
                start_hour, end_hour
            )
            start_time = datetime.combine(date, datetime.min.time()).replace(
                hour=start_hour
            )
            end_time = datetime.combine(date, datetime.min.time()).replace(
                hour=end_hour
            )

            shift = Shift(
                user_id=user.id,
                shift_type_id=shift_type.id,
                start_time=start_time,
                end_time=end_time,
                date=date,
            )
            generated_shifts.append(shift)

        if not dry_run and generated_shifts:
            db.session.add_all(generated_shifts)
            if commit:
                try:
                    db.session.commit()
                except Exception as e:
                    db.session.rollback()
                    messages.append(_("❌ Erreur : %(error)s", error=str(e)))
                    return [], messages
            else:
                db.session.flush()

        # Return a summary instead of detailed messages
        if generated_shifts:
            return generated_shifts, [
                _(
                    "✅ %(count)s shifts générés pour le %(date)s",
                    count=len(generated_shifts),
                    date=date.strftime("%d/%m/%Y"),
                )
            ]
        elif date.weekday() >= 5:
            return [], [
                _(
                    "⏭️ Pas de shift généré pour le %(date)s (week-end)",
                    date=date.strftime("%d/%m/%Y"),
                )
            ]
        else:
            return [], [
                _(
                    "⚠️ Aucun shift généré pour le %(date)s",
                    date=date.strftime("%d/%m/%Y"),
                )
            ]

    @staticmethod
    def generate_full_schedule(
        start_date: "date", end_date: "date", dry_run: bool = False
    ) -> "tuple[list, list]":
        """Generate the shifts for an entire period."""
        all_shifts = []
        days_with_shifts = 0
        days_skipped = 0
        from datetime import timedelta

        current_date = start_date
        while current_date <= end_date:
            shifts, messages = AdvancedShiftAutomation.generate_daily_shifts(
                current_date, dry_run=dry_run
            )
            all_shifts.extend(shifts)
            if shifts:
                days_with_shifts += 1
            else:
                days_skipped += 1
            current_date += timedelta(days=1)

        # Return a summary
        period_start = start_date.strftime("%d/%m/%Y")
        period_end = end_date.strftime("%d/%m/%Y")
        if dry_run:
            msg = _(
                "📋 Prévisualisation : %(count)s shifts seraient générés pour la période du %(start)s au %(end)s",
                count=len(all_shifts),
                start=period_start,
                end=period_end,
            )
        else:
            msg = _(
                "🎉 %(count)s shifts générés pour la période du %(start)s au %(end)s",
                count=len(all_shifts),
                start=period_start,
                end=period_end,
            )
        if days_skipped > 0:
            msg += " " + _(
                "(%(with_shifts)s jours avec shifts, %(skipped)s jours sans)",
                with_shifts=days_with_shifts,
                skipped=days_skipped,
            )
        return all_shifts, [msg]

    @staticmethod
    def rebalance_after_leave(
        leave: "Leave", dry_run: bool = False
    ) -> "tuple[list, list, list, list, list]":
        """
        Rebalance shifts and on-calls after a leave is added/modified.
        Called automatically when a leave is added. Leaves take
        priority: they remove and recompute overlapping shifts and
        on-calls.

        Per-day/per-section isolation when dry_run=False, not one
        all-or-nothing transaction: each day in the shift loop below,
        and the on-call regeneration section, run inside their own
        SAVEPOINT (db.session.begin_nested()). An error on one day (a
        unique-constraint race, an unexpected exception) rolls back only
        that day's SAVEPOINT - already-flushed changes for every other
        day/section stay intact - and is recorded in failed_shift_dates
        (or failed_oncall_period for the on-call section) instead of
        aborting the whole ±30-day window. A single final commit()
        persists everything that succeeded. Only a failure in the setup
        step before the loop (finding/deleting the leave's own
        overlapping on-calls) still rolls back and re-raises: nothing
        has been generated yet at that point, so there's nothing to
        preserve. This replaces an earlier version where any single
        day's failure discarded every other day already regenerated in
        the same window - see the "shift generation leaves empty every
        week around a leave" bug report.

        Returns (regenerated_shifts, messages, unfilled_oncall_dates,
        failed_shift_dates, failed_oncall_period). unfilled_oncall_dates
        is passed through from OnCallAutomation.generate_oncall_schedule()
        (Friday dates left unassigned because no user respects the legal
        spacing constraint - not an error, a business rule already
        handled gracefully with no retry needed). failed_shift_dates
        lists days whose shift regeneration actually raised and was
        rolled back to its pre-attempt state. failed_oncall_period is
        `[period_start, period_end]` if the on-call regeneration section
        itself raised (empty list otherwise) - at most one such period
        per call, since there's only one on-call regeneration section.
        All three are meant for the caller to notify admins once this
        method's own commit has actually succeeded.
        """
        from datetime import datetime, timedelta

        from app import db
        from app.models import OnCall, Shift
        from app.utils.automation import OnCallAutomation

        messages = []
        regenerated_shifts = []
        regenerated_oncalls = []
        unfilled_oncall_dates: list = []
        failed_shift_dates: list = []
        failed_oncall_period: list = []

        try:
            # Find the on-call period to recompute
            # On-calls span from Friday 9pm to the following Friday 7am
            # We need to find all Fridays that have overlapping on-calls
            oncall_periods_to_regenerate = set()

            # Find on-calls overlapping the leave
            overlapping_oncalls = OnCall.query.filter(
                OnCall.user_id == leave.user_id,
                OnCall.start_time
                < datetime.combine(
                    leave.end_date + timedelta(days=1), datetime.min.time()
                ),
                OnCall.end_time
                > datetime.combine(leave.start_date, datetime.min.time()),
            ).all()

            for oncall in overlapping_oncalls:
                # Find the starting Friday of this on-call
                friday_start = oncall.start_time.date()
                oncall_periods_to_regenerate.add(friday_start)

            # Delete the overlapping on-calls
            if overlapping_oncalls and not dry_run:
                for oncall in overlapping_oncalls:
                    db.session.delete(oncall)
                db.session.flush()
                messages.append(
                    _(
                        "🗑️ %(count)s astreintes supprimées pour l'utilisateur %(user_id)s",
                        count=len(overlapping_oncalls),
                        user_id=leave.user_id,
                    )
                )

            # Determine the full period to recompute
            # If on-calls were deleted, we need to recompute shifts for the whole affected period
            shift_period_start = leave.start_date
            shift_period_end = leave.end_date

            if oncall_periods_to_regenerate:
                # Find the period to cover: from the first Friday before
                # the leave to the last Friday after the leave ends + 30
                # days (to cover the whole on-call)

                # Find the first Friday before or during the leave
                first_friday = leave.start_date
                while first_friday.weekday() != 4:  # 4 = Friday
                    first_friday -= timedelta(days=1)

                # Find the last Friday after or during the leave
                last_friday = leave.end_date
                while last_friday.weekday() != 4:
                    last_friday += timedelta(days=1)

                # Extend the period to cover complete on-calls
                shift_period_start = first_friday - timedelta(
                    days=30
                )  # Take 30 days before
                shift_period_end = last_friday + timedelta(
                    days=30
                )  # Take 30 days after

            # Delete and regenerate shifts for the whole affected period.
            # dry_run never writes to the session, so there's nothing to
            # isolate - only the not-dry_run branch needs a per-day
            # SAVEPOINT.
            current_date = shift_period_start
            while current_date <= shift_period_end:
                if current_date.weekday() < 5:  # Monday to Friday only
                    if dry_run:
                        existing_shifts = Shift.query.filter_by(date=current_date).all()
                        if existing_shifts:
                            messages.append(
                                _(
                                    "🗑️ %(count)s shifts supprimés pour le %(date)s",
                                    count=len(existing_shifts),
                                    date=current_date.strftime("%d/%m/%Y"),
                                )
                            )
                        shifts, date_messages = (
                            AdvancedShiftAutomation.generate_daily_shifts(
                                current_date, dry_run=True, commit=False
                            )
                        )
                        regenerated_shifts.extend(shifts)
                        messages.extend(date_messages)
                    else:
                        # A failure on this specific day (e.g. a
                        # unique-constraint race) must not discard every
                        # other day already regenerated in this ±30-day
                        # window - only this day's SAVEPOINT rolls back,
                        # leaving that day's schedule exactly as it was
                        # before the attempt. The loop then continues
                        # instead of aborting the whole rebalance.
                        try:
                            with db.session.begin_nested():
                                existing_shifts = Shift.query.filter_by(
                                    date=current_date
                                ).all()
                                if existing_shifts:
                                    for shift in existing_shifts:
                                        db.session.delete(shift)
                                    db.session.flush()
                                    messages.append(
                                        _(
                                            "🗑️ %(count)s shifts supprimés pour le %(date)s",
                                            count=len(existing_shifts),
                                            date=current_date.strftime("%d/%m/%Y"),
                                        )
                                    )

                                shifts, date_messages = (
                                    AdvancedShiftAutomation.generate_daily_shifts(
                                        current_date, dry_run=False, commit=False
                                    )
                                )
                                regenerated_shifts.extend(shifts)
                                messages.extend(date_messages)
                        except Exception as e:
                            failed_shift_dates.append(current_date)
                            messages.append(
                                _(
                                    "❌ Échec de la régénération du %(date)s : "
                                    "%(error)s - ce jour n'a pas été modifié, "
                                    "action manuelle nécessaire",
                                    date=current_date.strftime("%d/%m/%Y"),
                                    error=str(e),
                                )
                            )
                current_date += timedelta(days=1)

            # Regenerate on-calls for the affected period
            # If on-calls were deleted, we need to recompute them
            if oncall_periods_to_regenerate and not dry_run:
                # Use the same period as for shifts
                from app.models import AutomationConfig
                from app.repositories.oncall_repository import OnCallRepository

                # Isolated in its own SAVEPOINT for the same reason as
                # each shift day above: an error here (e.g. a bug in
                # generate_oncall_schedule) must not discard the shift
                # days already regenerated by the loop above them.
                try:
                    with db.session.begin_nested():
                        # The deletion above only targets the leave's
                        # own on-calls (leave.user_id); the period to
                        # regenerate is padded by ±30 days and can
                        # therefore overlap OTHER users' on-calls, which
                        # were never deleted. Since
                        # generate_oncall_schedule always creates new
                        # on-calls without checking what already
                        # exists, the whole slot had to be cleared
                        # before regenerating, otherwise
                        # duplicate/overlapping on-calls would appear on
                        # the adjacent Fridays.
                        other_oncalls_deleted = (
                            OnCallRepository.delete_overlapping_range(
                                shift_period_start, shift_period_end
                            )
                        )
                        if other_oncalls_deleted:
                            db.session.flush()
                            messages.append(
                                _(
                                    "🗑️ %(count)s astreinte(s) supplémentaire(s) "
                                    "supprimée(s) dans la période étendue avant régénération",
                                    count=other_oncalls_deleted,
                                )
                            )

                        oncalls, oncall_messages, oncall_unfilled_dates = (
                            OnCallAutomation.generate_oncall_schedule(
                                shift_period_start,
                                shift_period_end,
                                rotation_order_ids=AutomationConfig.get_rotation_order(),
                                dry_run=False,
                                commit=False,
                            )
                        )
                        regenerated_oncalls.extend(oncalls)
                        messages.extend(oncall_messages)
                        unfilled_oncall_dates.extend(oncall_unfilled_dates)
                        messages.append(
                            _(
                                "🔄 %(count)s astreintes régénérées pour la période %(start)s - %(end)s",
                                count=len(oncalls),
                                start=shift_period_start.strftime("%d/%m/%Y"),
                                end=shift_period_end.strftime("%d/%m/%Y"),
                            )
                        )
                except Exception as e:
                    failed_oncall_period = [shift_period_start, shift_period_end]
                    messages.append(
                        _(
                            "❌ Échec de la régénération des astreintes pour la "
                            "période %(start)s - %(end)s : %(error)s - les "
                            "astreintes de cette période n'ont pas été "
                            "modifiées, action manuelle nécessaire",
                            start=shift_period_start.strftime("%d/%m/%Y"),
                            end=shift_period_end.strftime("%d/%m/%Y"),
                            error=str(e),
                        )
                    )

            if not dry_run:
                db.session.commit()
        except Exception:
            # Only reached by a failure in the setup step above (finding/
            # deleting the leave's own overlapping on-calls) - nothing
            # has been generated yet at that point, so a full rollback
            # loses nothing. Propagated as-is - LeaveService.
            # _rebalance_after_leave already catches and logs it.
            db.session.rollback()
            raise

        return (
            regenerated_shifts,
            messages,
            unfilled_oncall_dates,
            failed_shift_dates,
            failed_oncall_period,
        )
