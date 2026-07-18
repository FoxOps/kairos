"""
OnCall automation utilities for Kairos.

This module provides automation functionality for on-call duties.
"""

from collections import defaultdict
from collections.abc import Iterable
from datetime import date, datetime, timedelta

from app.models import Group, Leave, OnCall, User


class AvailabilityIndex:
    """In-memory view of the existing on-calls/leaves for a set of
    users, built by ONE bulk query per source (OnCall, Leave) then
    updated locally via record_assignment() as assignments are made
    during a generation run.

    Replaces DB queries repeated per candidate/week (up to 3 per
    candidate tested: on-call conflict, leave conflict, legal spacing
    constraint) - for a 6-month generation with several candidates
    tested per week, that added up to 1500+ queries.
    record_assignment() is essential (not just the initial preload):
    without it, an on-call just assigned to a user earlier in the same
    generation run wouldn't be seen by the following weeks' checks for
    that same user - before this fix, SQLAlchemy's autoflush implicitly
    guaranteed that visibility on every query.
    """

    def __init__(self, user_ids: Iterable[int]):
        user_id_set = set(user_ids)
        self._oncall_intervals: dict[int, list[tuple[datetime, datetime]]] = (
            defaultdict(list)
        )
        self._last_oncall_end: dict[int, datetime] = {}
        self._leave_intervals: dict[int, list[tuple[date, date]]] = defaultdict(list)

        if not user_id_set:
            return

        for oncall in OnCall.query.filter(OnCall.user_id.in_(user_id_set)).all():
            self._oncall_intervals[oncall.user_id].append(
                (oncall.start_time, oncall.end_time)
            )
            current_last = self._last_oncall_end.get(oncall.user_id)
            if current_last is None or oncall.end_time > current_last:
                self._last_oncall_end[oncall.user_id] = oncall.end_time

        for leave in Leave.query.filter(Leave.user_id.in_(user_id_set)).all():
            self._leave_intervals[leave.user_id].append(
                (leave.start_date, leave.end_date)
            )

    def has_oncall_conflict(
        self, user_id: int, start_time: datetime, end_time: datetime
    ) -> bool:
        return any(
            existing_start < end_time and existing_end > start_time
            for existing_start, existing_end in self._oncall_intervals.get(user_id, [])
        )

    def has_leave_conflict(
        self, user_id: int, start_date: date, end_date: date
    ) -> bool:
        return any(
            leave_start <= end_date and leave_end >= start_date
            for leave_start, leave_end in self._leave_intervals.get(user_id, [])
        )

    def meets_spacing_constraint(self, user_id: int, start_time: datetime) -> bool:
        last_end = self._last_oncall_end.get(user_id)
        if last_end is None:
            return True
        gap_days = (start_time - last_end).days
        return gap_days / 7 >= 2

    def record_assignment(
        self, user_id: int, start_time: datetime, end_time: datetime
    ) -> None:
        self._oncall_intervals[user_id].append((start_time, end_time))
        current_last = self._last_oncall_end.get(user_id)
        if current_last is None or end_time > current_last:
            self._last_oncall_end[user_id] = end_time


class OnCallAutomation:
    """
    Class managing on-call automation.

    Features:
    - Automatic on-call generation with rotation
    - Handling replacements on conflict
    - Rotation order configuration
    """

    @staticmethod
    def get_eligible_users() -> list[User]:
        """
        Fetch the list of users eligible for on-call duty.
        A user is eligible if they belong to a group that participates
        in on-call rotation.
        """
        return (
            User.query.join(Group)
            .filter(Group.is_part_of_oncall.is_(True))
            .order_by(User.name)
            .all()
        )

    @staticmethod
    def get_rotation_order(rotation_order_ids: list[int] | None = None) -> list[User]:
        """
        Fetch the users' rotation order.

        Args:
            rotation_order_ids: Optional list of user IDs in the desired
                              order. If None, uses alphabetical order.

        Returns:
            List of users in rotation order.
        """
        eligible_users = OnCallAutomation.get_eligible_users()

        if not eligible_users:
            return []

        # If a custom order is provided
        if rotation_order_ids:
            # Build an id -> user map for quick access
            user_map = {user.id: user for user in eligible_users}

            # Build the list in the specified order
            ordered_users = []
            for user_id in rotation_order_ids:
                if user_id in user_map:
                    ordered_users.append(user_map[user_id])

            # Add the remaining users (not in rotation_order_ids)
            remaining_users = [
                u for u in eligible_users if u.id not in rotation_order_ids
            ]
            ordered_users.extend(remaining_users)

            return ordered_users

        # Otherwise, return in alphabetical order
        return eligible_users

    @staticmethod
    def check_oncall_constraint(
        user: User, start_time: datetime, index: AvailabilityIndex
    ) -> bool:
        """
        Check the legal minimum spacing constraint (2 weeks) between two
        consecutive on-calls for the same user.

        Args:
            user: User to check
            start_time: Start of the prospective new on-call
            index: In-memory view of existing on-calls/leaves (see
                AvailabilityIndex) - avoids a DB query per call.

        Returns:
            True if there's no previous on-call or the spacing is sufficient.
        """
        return index.meets_spacing_constraint(user.id, start_time)

    @staticmethod
    def find_next_available_user(
        users: list[User],
        start_time: datetime,
        end_time: datetime,
        index: AvailabilityIndex,
    ) -> User | None:
        """
        Find the first available user in the list for the given period
        (no leave, no overlapping on-call, legal constraint satisfied).

        Args:
            users: Ordered list of candidate users
            start_time: Start of the on-call period
            end_time: End of the on-call period
            index: In-memory view of existing on-calls/leaves (see
                AvailabilityIndex) - avoids a DB query per candidate tested.

        Returns:
            The first available user, or None if none is available.
        """
        for user in users:
            if index.has_oncall_conflict(user.id, start_time, end_time):
                continue

            if index.has_leave_conflict(user.id, start_time.date(), end_time.date()):
                continue

            if not OnCallAutomation.check_oncall_constraint(user, start_time, index):
                continue

            return user

        return None

    @staticmethod
    def generate_oncall_schedule(
        start_date,
        end_date,
        rotation_order_ids: list[int] | None = None,
        dry_run: bool = True,
        commit: bool = True,
    ):
        """
        Generate an on-call schedule for a given period.

        On-calls start on Friday at 9pm and end the following Friday at
        7am. Users are assigned according to the rotation order,
        respecting leaves, existing on-calls, and the minimum 2-week
        legal spacing. If no user satisfies all three rules, that week is
        deliberately left unassigned rather than assigning someone in
        violation of the legal spacing constraint - the caller is
        responsible for notifying admins (see unfilled_dates in the
        return value) so the gap can be filled manually.

        Args:
            start_date: Start date
            end_date: End date
            rotation_order_ids: Custom rotation order
            dry_run: If True, doesn't save anything to the database
            commit: If False (used by rebalance_after_leave to make the
                whole rebalance atomic), flush() instead of commit() -
                lets the caller decide when to commit/rollback.

        Returns:
            Tuple: (list of generated on-calls (OnCall objects), log
            messages, list of Friday dates left unassigned because no
            user satisfied the legal spacing constraint - only notify
            admins about these once the caller's own commit has actually
            succeeded, never before).
        """
        from app import db

        eligible_users = OnCallAutomation.get_eligible_users()
        if not eligible_users:
            return [], ["Aucun utilisateur éligible pour les astreintes."], []

        rotation_order = OnCallAutomation.get_rotation_order(rotation_order_ids)
        if not rotation_order:
            return [], ["Impossible de déterminer l'ordre de rotation."], []

        # One bulk query per source (OnCall, Leave) instead of several
        # queries per candidate tested each week - see AvailabilityIndex.
        index = AvailabilityIndex(user.id for user in eligible_users)

        days_ahead = (4 - start_date.weekday()) % 7
        current_friday = start_date + timedelta(days=days_ahead)

        oncalls = []
        messages = []
        unfilled_dates = []
        rotation_index = 0

        # end_date inclusive, like AdvancedShiftAutomation.generate_full_schedule
        # (`current_date <= end_date`) - both receive the same period
        # from admin_automation_routes.py::automation_full, they must
        # treat end_date the same way. Before: `<` ignored the week
        # whose Friday landed exactly on end_date.
        while current_friday <= end_date:
            start_time = datetime.combine(current_friday, datetime.min.time()).replace(
                hour=21
            )
            end_time = start_time + timedelta(days=7, hours=-14)

            ordered_candidates = (
                rotation_order[rotation_index:] + rotation_order[:rotation_index]
            )
            assigned_user = OnCallAutomation.find_next_available_user(
                ordered_candidates, start_time, end_time, index
            )

            if assigned_user is None:
                # Deliberately left unassigned - no fallback that ignores
                # the legal 2-week spacing constraint. The caller is
                # responsible for notifying admins once its own commit
                # has succeeded (see unfilled_dates in the return value).
                messages.append(
                    f"⚠️ Aucune astreinte générée pour le {current_friday.strftime('%d/%m/%Y')} "
                    "(aucun utilisateur ne respecte le délai légal de 2 semaines entre deux "
                    "astreintes) - assignation manuelle nécessaire."
                )
                unfilled_dates.append(current_friday)
                current_friday += timedelta(days=7)
                continue

            oncall = OnCall(
                user_id=assigned_user.id,
                start_time=start_time,
                end_time=end_time,
            )
            oncalls.append(oncall)
            if not dry_run:
                db.session.add(oncall)
            # Essential even in dry_run: the following weeks of this same
            # generation run must see this assignment to respect the
            # legal spacing and avoid duplicates.
            index.record_assignment(assigned_user.id, start_time, end_time)

            rotation_index = (rotation_order.index(assigned_user) + 1) % len(
                rotation_order
            )
            current_friday += timedelta(days=7)

        if not dry_run and oncalls:
            if commit:
                db.session.commit()
            else:
                db.session.flush()

        # ✅ prefix: matches AdvancedShiftAutomation's own summary
        # messages (e.g. "✅ N shifts générés pour le ...") - without a
        # recognized emoji, _classify_automation_message() in
        # admin_automation_routes.py falls through to the caller's
        # default_category ("danger" for on-call messages), which
        # rendered this line as a red flash despite being a plain
        # success summary.
        messages.append(f"✅ {len(oncalls)} astreintes générées.")
        return oncalls, messages, unfilled_dates
