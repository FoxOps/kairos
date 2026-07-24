"""
OnCall automation utilities for Kairos.

This module provides automation functionality for on-call duties.
"""

from collections import defaultdict
from collections.abc import Iterable
from datetime import date, datetime, timedelta

from flask_babel import gettext as _

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

    def __init__(self, user_ids: Iterable[int], min_spacing_weeks: int = 2):
        self._min_spacing_weeks = min_spacing_weeks
        user_id_set = set(user_ids)
        self._oncall_intervals: dict[int, list[tuple[datetime, datetime]]] = (
            defaultdict(list)
        )
        self._leave_intervals: dict[int, list[tuple[date, date]]] = defaultdict(list)

        if not user_id_set:
            return

        for oncall in OnCall.query.filter(OnCall.user_id.in_(user_id_set)).all():
            self._oncall_intervals[oncall.user_id].append(
                (oncall.start_time, oncall.end_time)
            )

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

    def meets_spacing_constraint(
        self, user_id: int, start_time: datetime, end_time: datetime
    ) -> bool:
        """`min_spacing_weeks`-minimum gap (see OnCallSpacingRule,
        default 2 weeks) to EVERY existing/assigned on-call for
        this user - chronologically before *or* after the prospective
        interval, not just "the single most recently created one".

        This matters because a rebalance (AdvancedShiftAutomation.
        rebalance_after_leave) regenerates only a ±30-day window around
        a leave while leaving on-calls *outside* that window untouched
        - including ones scheduled further in the future than the
        window itself. A version of this method that only tracked the
        latest on-call end time ever seen for a user (a single "last
        end" value) would treat a future on-call as if it were the most
        recent *past* one, computing a nonsensical negative gap that
        fails the constraint for every candidate on every week of the
        window - a real production incident (confirmed against a real
        deployment's data: 4 eligible users, zero live leave conflicts
        in the window, still 100% unfilled) - not just a theoretical
        edge case.
        """
        for existing_start, existing_end in self._oncall_intervals.get(user_id, []):
            if existing_end <= start_time:
                gap_days = (start_time - existing_end).days
            elif existing_start >= end_time:
                gap_days = (existing_start - end_time).days
            else:
                # Overlaps the prospective interval - a conflict
                # (has_oncall_conflict's concern), not a spacing issue.
                continue
            if gap_days / 7 < self._min_spacing_weeks:
                return False
        return True

    def record_assignment(
        self, user_id: int, start_time: datetime, end_time: datetime
    ) -> None:
        self._oncall_intervals[user_id].append((start_time, end_time))

    def get_intervals(self, user_id: int) -> list[tuple[datetime, datetime]]:
        """All on-calls (pre-existing in the DB, or recorded via
        record_assignment) known to this index for the user - used to
        seed the spacing-constraint search in _solve_max_filled_weeks()
        below."""
        return list(self._oncall_intervals.get(user_id, []))


# Hard cap on search nodes for _solve_max_filled_weeks() below - a safety
# valve against pathological inputs (many weeks, many candidates, few
# real conflicts so the branch-and-bound bound rarely prunes), not a
# limit expected to be hit in realistic use (few eligible users, and
# real conflicts are localized to a handful of weeks around a leave).
# If ever hit, the search still returns the best assignment found so
# far - deterministic, since candidate order and exploration order are
# both deterministic (no randomness), never worse than the previous
# pure-greedy algorithm.
_MAX_SEARCH_NODES = 200_000


def _solve_max_filled_weeks(
    weeks: list[tuple[date, datetime, datetime]],
    week_candidates: list[list[User]],
    index: AvailabilityIndex,
    min_spacing_weeks: int = 2,
) -> dict[int, User]:
    """
    Branch-and-bound search that maximizes the number of on-call weeks
    that can be filled, respecting the legal spacing constraint (see
    OnCallSpacingRule, default 2 weeks).

    Why this exists: a plain greedy pass (try the first available
    candidate for week 1, then week 2, ...) can commit to a locally-fine
    choice that turns out to block a *later* week from ever being
    filled, even though a different (still valid, still non-repeating)
    assignment of the earlier weeks would have left that later week
    fillable too. Concretely: 3 users A/B/C, C on leave only during
    week 3, weeks 1-6 otherwise conflict-free. Greedy assigns A→week1,
    B→week2, and now nobody is free for week3 (A and B were both just
    used, C is on leave) - week3 is greedily reported unfillable even
    though A→week1, C→week2, B→week3, A→week4, C→week5, B→week6 fills
    every single week. This search finds that second assignment instead
    of settling for the first one that merely avoids raising an error.

    week_candidates[i] must already be pre-filtered for the *static*
    per-week constraints (existing on-call / leave conflicts) - this
    function only searches the *dynamic* constraint (2-week spacing
    against other weeks being decided in the same run), since that's
    the only constraint that actually interacts across weeks.

    Explores "assign candidate" branches (in each week's rotation-order
    preference) before the "leave this week unfilled" branch, so a
    full or near-full solution is typically found almost immediately -
    after that, the branch-and-bound bound (filled_so_far +
    weeks_remaining <= best_found) prunes nearly everything else quickly.

    Returns: {week_index: User} for the best (most weeks filled)
    assignment found within the node budget.
    """
    total_weeks = len(weeks)

    # Every user's known on-calls (pre-existing in the DB, anywhere in
    # time - not just inside this window) - seeded once, then appended
    # to/popped from as the search tries and backtracks assignments.
    # Checking against the *full* interval list (both chronologically
    # before and after a candidate week), not a single "last end"
    # value, is what makes this correct when on-calls exist *after*
    # this window too (see AvailabilityIndex.meets_spacing_constraint's
    # docstring for why that distinction is essential here).
    intervals: dict[int, list[tuple[datetime, datetime]]] = {}
    for candidates in week_candidates:
        for user in candidates:
            if user.id not in intervals:
                intervals[user.id] = index.get_intervals(user.id)

    best_count = 0
    best_assignment: dict[int, User] = {}
    current: dict[int, User] = {}
    nodes_explored = 0

    def meets_spacing(user_id: int, start_time: datetime, end_time: datetime) -> bool:
        for existing_start, existing_end in intervals.get(user_id, []):
            if existing_end <= start_time:
                gap_days = (start_time - existing_end).days
            elif existing_start >= end_time:
                gap_days = (existing_start - end_time).days
            else:
                continue
            if gap_days / 7 < min_spacing_weeks:
                return False
        return True

    def recurse(week_index: int, filled_count: int) -> None:
        nonlocal nodes_explored, best_count, best_assignment

        if filled_count > best_count:
            best_count = filled_count
            best_assignment = dict(current)

        nodes_explored += 1
        if week_index == total_weeks or nodes_explored > _MAX_SEARCH_NODES:
            return

        weeks_remaining = total_weeks - week_index
        if filled_count + weeks_remaining <= best_count:
            # No assignment of the remaining weeks could beat the best
            # found so far, even filling every single one of them.
            return

        _friday, start_time, end_time = weeks[week_index]
        for user in week_candidates[week_index]:
            if not meets_spacing(user.id, start_time, end_time):
                continue

            intervals[user.id].append((start_time, end_time))
            current[week_index] = user

            recurse(week_index + 1, filled_count + 1)

            del current[week_index]
            intervals[user.id].pop()

        # Try leaving this week unfilled too - explored last so the
        # depth-first search finds a full/near-full solution first,
        # making the bound above effective from early on.
        recurse(week_index + 1, filled_count)

    recurse(0, 0)
    return best_assignment


def _fridays_in_range(start_date: date, end_date: date) -> list[date]:
    """Every on-call anchor weekday (see OnCallAnchorRule, default
    Friday) from the first one on/after start_date through end_date,
    inclusive. Keeps the "fridays" name for the default-configuration
    case this module was originally written for; the actual weekday
    used is whatever OnCallAnchorRule resolves to."""
    from app.utils.automation.rules import OnCallAnchorRule

    anchor_weekday = OnCallAnchorRule.resolve()["weekday"]
    days_ahead = (anchor_weekday - start_date.weekday()) % 7
    current_friday = start_date + timedelta(days=days_ahead)
    fridays = []
    while current_friday <= end_date:
        fridays.append(current_friday)
        current_friday += timedelta(days=7)
    return fridays


def _covering_friday(start_date: date) -> date:
    """The Friday anchor of the on-call week straddling `start_date`
    (Fri 21:00 -> the following Friday 07:00), if one actually exists
    in the database - otherwise `start_date` itself, unchanged.

    A delete-then-regenerate pair (OnCallRepository.
    delete_overlapping_range() followed by generate_oncall_schedule())
    must operate on the exact same set of weeks, or the delete silently
    drops a week the regenerate never re-creates. delete_overlapping_range()
    uses a true datetime overlap check (OnCall.end_time > start_date at
    00:00), while _fridays_in_range() above only considers Fridays
    on/after start_date at *date* granularity - the Friday immediately
    before start_date always still overlaps (its on-call ends 07:00 on
    the morning of the day 7 days later, which is after midnight of
    that day), even when start_date itself already falls on a Friday.
    Passing this function's result instead of the raw start_date to
    generate_oncall_schedule() (for the same delete-then-regenerate
    call) closes that gap - see the "astreinte supprimée par un
    rééquilibrage mais jamais régénérée" investigation for a confirmed
    real-world instance (two consecutive weeks silently lost after a
    leave-triggered rebalance).

    Deliberately queries the DB rather than just computing "one week
    back" unconditionally: unconditionally backdating would ask the
    solver to also fill whatever Friday sits one week before
    start_date even when nothing was ever assigned or deleted there,
    consuming a candidate's 2-week spacing budget for a week nobody
    asked about and blocking the *actual* requested weeks from getting
    their expected fallback assignment - a real regression caught by
    tests/integration/test_admin_automation.py::
    test_regenerate_mode_replaces_assignment_with_a_real_conflict."""
    start_midnight = datetime.combine(start_date, datetime.min.time())
    straddling = (
        OnCall.query.filter(
            OnCall.start_time < start_midnight,
            OnCall.end_time > start_midnight,
        )
        .order_by(OnCall.start_time.desc())
        .first()
    )
    return straddling.start_time.date() if straddling else start_date


def _generate_for_fridays(
    fridays: list[date],
    rotation_order: list[User],
    index: AvailabilityIndex,
    dry_run: bool,
    commit: bool,
    preferred_assignments: dict[date, int] | None = None,
) -> tuple[list[OnCall], list[str], list[date]]:
    """Shared by generate_oncall_schedule() (every Friday in a period)
    and fill_oncall_gaps() (only the Fridays missing an on-call) - runs
    the branch-and-bound search (_solve_max_filled_weeks) over exactly
    the given Fridays and creates OnCall objects for whichever ones it
    manages to fill.

    preferred_assignments (optional): {friday: user_id} of who was
    on-call for that Friday *before* the caller wiped the window -
    when given, that user is tried first for that week instead of
    blindly replaying the rotation order, so a week that already had a
    valid assignment keeps it rather than being needlessly reshuffled.
    Passed by AdvancedShiftAutomation.rebalance_after_leave() and the
    "Rafraîchir > Régénérer entièrement" action only (see
    OnCallAutomation.capture_existing_assignments()) - every other
    caller leaves this None, exactly today's behavior. Still subject to
    the same conflict filtering as any other candidate below (a
    preferred user with a real conflict - e.g. it's their own leave
    week - is filtered out like anyone else, no special-casing)."""
    from app import db
    from app.utils.automation.rules import OnCallAnchorRule, OnCallSpacingRule

    anchor = OnCallAnchorRule.resolve()
    min_spacing_weeks = OnCallSpacingRule.resolve()["min_spacing_weeks"]

    weeks: list[tuple[date, datetime, datetime]] = []
    for friday in fridays:
        start_time = datetime.combine(friday, datetime.min.time()).replace(
            hour=anchor["start_hour"]
        )
        end_time = datetime.combine(
            friday + timedelta(days=7), datetime.min.time()
        ).replace(hour=anchor["end_hour"])
        weeks.append((friday, start_time, end_time))

    # Per-week candidates, pre-filtered for the *static* constraints
    # (existing on-call / leave conflicts - independent of what gets
    # assigned to other weeks in this run). Each week's preference
    # order rotates the base rotation order by its own index, the same
    # simple round-robin baseline a plain greedy pass produces when
    # nothing forces a deviation from it - the search below only
    # deviates from this preference when required to fill a week that
    # would otherwise stay empty. If preferred_assignments names a
    # (still-eligible) user for this week, they're moved to the front
    # of that baseline instead, minimizing how much of an
    # already-working schedule gets reshuffled on each rebalance.
    rotation_by_id = {user.id: user for user in rotation_order}
    week_candidates: list[list[User]] = []
    for week_index, (friday, start_time, end_time) in enumerate(weeks):
        offset = week_index % len(rotation_order)
        preferred_order = rotation_order[offset:] + rotation_order[:offset]

        preferred_user_id = (
            preferred_assignments.get(friday) if preferred_assignments else None
        )
        preferred_user = rotation_by_id.get(preferred_user_id)  # type: ignore[arg-type]
        if preferred_user is not None:
            preferred_order = [preferred_user] + [
                user for user in preferred_order if user.id != preferred_user_id
            ]

        week_candidates.append(
            [
                user
                for user in preferred_order
                if not index.has_oncall_conflict(user.id, start_time, end_time)
                and not index.has_leave_conflict(
                    user.id, start_time.date(), end_time.date()
                )
            ]
        )

    assignment = _solve_max_filled_weeks(
        weeks, week_candidates, index, min_spacing_weeks=min_spacing_weeks
    )

    oncalls = []
    messages = []
    unfilled_dates = []

    for week_index, (friday, start_time, end_time) in enumerate(weeks):
        assigned_user = assignment.get(week_index)

        if assigned_user is None:
            # Deliberately left unassigned - no fallback that ignores
            # the legal spacing constraint (see OnCallSpacingRule), and
            # only after the search above confirmed no permutation of
            # this period's assignments could fill it either. The
            # caller is responsible for notifying admins once its own
            # commit has actually succeeded (see unfilled_dates below).
            messages.append(
                _(
                    "[WARN] Aucune astreinte générée pour le %(date)s "
                    "(aucun utilisateur ne respecte le délai légal de %(weeks)s "
                    "semaines entre deux astreintes) - assignation manuelle "
                    "nécessaire.",
                    date=friday.strftime("%d/%m/%Y"),
                    weeks=min_spacing_weeks,
                )
            )
            unfilled_dates.append(friday)
            continue

        oncall = OnCall(
            user_id=assigned_user.id,
            start_time=start_time,
            end_time=end_time,
        )
        oncalls.append(oncall)
        if not dry_run:
            db.session.add(oncall)
        # Essential even in dry_run: subsequent readers of `index`
        # within the same generation run see this assignment.
        index.record_assignment(assigned_user.id, start_time, end_time)

    if not dry_run and oncalls:
        if commit:
            db.session.commit()
        else:
            db.session.flush()

    messages.append(_("[OK] %(count)s astreintes générées.", count=len(oncalls)))
    return oncalls, messages, unfilled_dates


class OnCallAutomation:
    """
    Class managing on-call automation.

    Features:
    - Automatic on-call generation with rotation
    - Handling replacements on conflict
    - Rotation order configuration
    """

    @staticmethod
    def get_eligible_users(group: Group | None = None) -> list[User]:
        """
        Fetch the list of users eligible for on-call duty.
        A user is eligible if they belong to a group that participates
        in on-call rotation. `group`: when given, restricts eligibility
        to that single Group's members instead of pooling every
        on-call-eligible group - used by the "per_group" scheduling
        mode (SettingsService.get_scheduling_mode()) to run each
        group's own independent rotation. None (the default) preserves
        today's pooled behavior."""
        query = User.query.join(Group).filter(Group.is_part_of_oncall.is_(True))
        if group is not None:
            query = query.filter(User.group_id == group.id)
        return query.order_by(User.name).all()

    @staticmethod
    def detect_oncall_gaps() -> list[date]:
        """
        Fridays with no on-call at all, strictly *between* the earliest
        and latest existing on-call in the database - i.e. real gaps in
        an otherwise-generated schedule, not "not generated yet" future
        weeks (which aren't a bug, just scheduling that hasn't happened
        yet).

        Exists to proactively surface gaps on the automation pages
        instead of relying on an admin correctly guessing which date
        range to widen the "Période" fields to in order to reach them -
        a real point of confusion: an admin ran "Combler les trous
        d'astreintes" with the page's default dates (which start at
        today, not in the past) and concluded the feature "did nothing"
        because the actual gap predated the range they'd left selected.
        """
        first_oncall = OnCall.query.order_by(OnCall.start_time.asc()).first()
        last_oncall = OnCall.query.order_by(OnCall.start_time.desc()).first()
        if not first_oncall or not last_oncall:
            return []

        covered = {oncall.start_time.date() for oncall in OnCall.query.all()}

        gaps = []
        current_friday = first_oncall.start_time.date() + timedelta(days=7)
        last_friday = last_oncall.start_time.date()
        while current_friday < last_friday:
            if current_friday not in covered:
                gaps.append(current_friday)
            current_friday += timedelta(days=7)
        return gaps

    @staticmethod
    def align_regeneration_start(start_date: date) -> date:
        """Public wrapper around _covering_friday() (see its docstring)
        for callers outside this module that pair OnCallRepository.
        delete_overlapping_range(start_date, ...) with
        generate_oncall_schedule(start_date, ...) - pass this method's
        result as the regeneration call's start_date instead of the raw
        one, so it re-creates the same week the delete call actually
        wiped. Only the generate side needs realigning; the delete call
        already reaches this Friday on its own (true datetime overlap),
        it's generate's date-level Friday search that falls short."""
        return _covering_friday(start_date)

    @staticmethod
    def get_rotation_order(
        rotation_order_ids: list[int] | None = None, group: Group | None = None
    ) -> list[User]:
        """
        Fetch the users' rotation order.

        Args:
            rotation_order_ids: Optional list of user IDs in the desired
                              order. If None, uses alphabetical order.
            group: When given, restricts to that Group's eligible
                users (see get_eligible_users()) - rotation_order_ids
                entries for users outside the group are silently
                dropped, same as any other ineligible id.

        Returns:
            List of users in rotation order.
        """
        eligible_users = OnCallAutomation.get_eligible_users(group=group)

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
        user: User, start_time: datetime, end_time: datetime, index: AvailabilityIndex
    ) -> bool:
        """
        Check the legal minimum spacing constraint (2 weeks) between two
        consecutive on-calls for the same user.

        Args:
            user: User to check
            start_time: Start of the prospective new on-call
            end_time: End of the prospective new on-call
            index: In-memory view of existing on-calls/leaves (see
                AvailabilityIndex) - avoids a DB query per call.

        Returns:
            True if there's no conflicting on-call or the spacing is
            sufficient on both sides (before *and* after).
        """
        return index.meets_spacing_constraint(user.id, start_time, end_time)

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

            if not OnCallAutomation.check_oncall_constraint(
                user, start_time, end_time, index
            ):
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
        preferred_assignments: dict[date, int] | None = None,
        group: Group | None = None,
    ):
        """
        Generate an on-call schedule for a given period.

        On-calls start on Friday at 9pm and end the following Friday at
        7am. Users are assigned respecting leaves, existing on-calls,
        and the minimum 2-week legal spacing - but not via a single
        greedy left-to-right pass. A plain greedy pass can commit to a
        locally-fine choice for one week that turns out to block a
        *later* week from ever being filled, even though a different
        (still legal) assignment of the earlier weeks would have kept
        that later week fillable too - see
        _solve_max_filled_weeks()'s docstring for a concrete example.
        This method instead runs a branch-and-bound search
        (_solve_max_filled_weeks) that tries every relevant permutation
        of assignments (bounded by a node budget for pathological
        inputs, see _MAX_SEARCH_NODES) to find the assignment that
        leaves the *fewest* weeks empty - a week is only ever left
        unassigned once no permutation of the whole period's
        assignments can fill it, never merely because the first
        left-to-right attempt happened not to.

        Args:
            start_date: Start date
            end_date: End date
            rotation_order_ids: Custom rotation order
            dry_run: If True, doesn't save anything to the database
            commit: If False (used by rebalance_after_leave to make the
                whole rebalance atomic), flush() instead of commit() -
                lets the caller decide when to commit/rollback.
            preferred_assignments: see _generate_for_fridays()'s
                docstring - only rebalance_after_leave() and the
                "Rafraîchir > Régénérer entièrement" action pass this,
                every other caller leaves it None.
            group: When given, restricts eligibility/rotation order to
                that Group only (see get_eligible_users()) - used by
                "per_group" scheduling mode to run each group's own
                independent weekly rotation. Since on-calls carry no
                group of their own, calling this once per group for
                the same date range is how multiple groups end up with
                concurrent on-calls for the same Friday, one each -
                the intended per_group behavior, not a conflict.

        Returns:
            Tuple: (list of generated on-calls (OnCall objects), log
            messages, list of Friday dates left unassigned because no
            permutation of the period's assignments could satisfy the
            legal spacing constraint for that week - only notify admins
            about these once the caller's own commit has actually
            succeeded, never before).
        """
        eligible_users = OnCallAutomation.get_eligible_users(group=group)
        if not eligible_users:
            return [], [_("Aucun utilisateur éligible pour les astreintes.")], []

        rotation_order = OnCallAutomation.get_rotation_order(
            rotation_order_ids, group=group
        )
        if not rotation_order:
            return [], [_("Impossible de déterminer l'ordre de rotation.")], []

        # One bulk query per source (OnCall, Leave) instead of several
        # queries per candidate tested each week - see AvailabilityIndex.
        from app.utils.automation.rules import OnCallSpacingRule

        index = AvailabilityIndex(
            (user.id for user in eligible_users),
            min_spacing_weeks=OnCallSpacingRule.resolve()["min_spacing_weeks"],
        )

        # end_date inclusive, like AdvancedShiftAutomation.generate_full_schedule
        # (`current_date <= end_date`) - both receive the same period
        # from admin_automation_routes.py::automation_full, they must
        # treat end_date the same way. Before: `<` ignored the week
        # whose Friday landed exactly on end_date.
        fridays = _fridays_in_range(start_date, end_date)

        return _generate_for_fridays(
            fridays,
            rotation_order,
            index,
            dry_run=dry_run,
            commit=commit,
            preferred_assignments=preferred_assignments,
        )

    @staticmethod
    def capture_existing_assignments(start_date, end_date) -> dict[date, int]:
        """{friday: user_id} of on-calls already overlapping
        [start_date, end_date] (same overlap definition as
        OnCallRepository.list_overlapping_range()/delete_overlapping_range()
        - reused here, not reimplemented) - must be called *before* the
        caller wipes that range, otherwise the information is already
        gone. Used to feed generate_oncall_schedule()'s
        preferred_assignments so a rebalance/regenerate prefers keeping
        a week's existing occupant over blindly replaying the rotation
        order - see _generate_for_fridays()'s docstring.

        Deliberately does **not** take a user id to exclude (e.g. a
        leave rebalance's own leave.user_id): a user going on leave
        only conflicts with *their own* specific week(s) -
        has_leave_conflict() in _generate_for_fridays() already filters
        that out precisely, without touching this dict. Pre-excluding
        that user's id here would strip *every* week they're on in the
        window, including ones with no actual conflict - directly
        working against the "minimal perturbation" goal for those other
        weeks (confirmed while building this: a 4-user, 2-month window
        with the leave user also validly on-call twice more later in
        that same window lost both of those unrelated preferences to a
        blanket exclude)."""
        from app.repositories.oncall_repository import OnCallRepository

        oncalls = OnCallRepository.list_overlapping_range(start_date, end_date)
        return {oncall.start_time.date(): oncall.user_id for oncall in oncalls}

    @staticmethod
    def fill_oncall_gaps(
        start_date,
        end_date,
        rotation_order_ids: list[int] | None = None,
        dry_run: bool = True,
        commit: bool = True,
    ):
        """
        Like generate_oncall_schedule(), but only ever *creates*
        on-calls for Fridays in the period that don't already have one
        - existing on-calls (even manually edited, or previously
        generated) are left completely untouched, never deleted or
        reassigned. Used by the "Rafraîchir" action's "combler les
        trous d'astreintes seulement" mode - unlike generate_oncall_
        schedule() (which is meant to be used after clearing the
        period first), this is for filling gaps in an otherwise-already
        -planned schedule without disturbing what's already there.

        Returns the same 3-tuple shape as generate_oncall_schedule():
        (list of newly created OnCall objects, messages,
        list of Friday dates still left unassigned).
        """
        eligible_users = OnCallAutomation.get_eligible_users()
        if not eligible_users:
            return [], [_("Aucun utilisateur éligible pour les astreintes.")], []

        rotation_order = OnCallAutomation.get_rotation_order(rotation_order_ids)
        if not rotation_order:
            return [], [_("Impossible de déterminer l'ordre de rotation.")], []

        from app.utils.automation.rules import OnCallSpacingRule

        index = AvailabilityIndex(
            (user.id for user in eligible_users),
            min_spacing_weeks=OnCallSpacingRule.resolve()["min_spacing_weeks"],
        )

        # AvailabilityIndex doesn't expose "which Fridays already have
        # *someone* assigned" (its intervals are keyed per user, not
        # per slot) - a direct query is simplest and correct here.
        from app.models import OnCall as OnCallModel

        already_covered = {
            oncall.start_time.date()
            for oncall in OnCallModel.query.filter(
                OnCallModel.start_time
                >= datetime.combine(start_date, datetime.min.time()),
                OnCallModel.start_time
                <= datetime.combine(end_date, datetime.max.time()),
            ).all()
        }

        missing_fridays = [
            friday
            for friday in _fridays_in_range(start_date, end_date)
            if friday not in already_covered
        ]

        if not missing_fridays:
            return [], [_("[OK] Aucune astreinte manquante sur cette période.")], []

        return _generate_for_fridays(
            missing_fridays, rotation_order, index, dry_run=dry_run, commit=commit
        )
