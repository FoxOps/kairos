"""On-call solver primitives used by oncall_planner.py: the in-memory
AvailabilityIndex and the branch-and-bound search maximizing filled
on-call weeks under the legal spacing constraint.

Moved here unchanged (apart from AvailabilityIndex becoming
snapshot-only) from the legacy app/utils/automation/oncall_automation.py
when the legacy engine was removed in 1.2.0 - no DB access in this
module."""

from collections import defaultdict
from collections.abc import Callable, Iterable, Sequence
from datetime import date, datetime
from typing import Protocol, TypeVar

from app.utils.automation.rules.predicates import oncall_violates_spacing


class _HasId(Protocol):
    """Structural type for _solve_max_filled_weeks()'s candidates - the
    function only ever reads `.id`, so it accepts the pure planner's
    `UserRef` dataclass (app/utils/automation/planner/types.py) or any
    other object with an id. Declared as a read-only
    property (not a plain attribute) so a frozen dataclass like
    `UserRef` - whose fields mypy treats as read-only - satisfies it;
    a plain mutable-attribute Protocol member would reject it."""

    @property
    def id(self) -> int: ...


_T = TypeVar("_T", bound=_HasId)


class AvailabilityIndex:
    """In-memory view of the existing on-calls/leaves for a set of
    users, built from snapshot data the planner's adapter layer loaded
    once (one bulk query per source) - never a DB query per
    candidate/week (up to 3 per candidate tested: on-call conflict,
    leave conflict, legal spacing constraint, 1500+ queries for a
    6-month run before this index existed). record_assignment() lets
    an on-call assigned earlier in the same run be seen by the
    following weeks' checks for that same user.
    """

    def __init__(
        self,
        oncall_snapshots: Iterable = (),
        leave_snapshots: Iterable = (),
        min_spacing_weeks: int = 2,
    ):
        """Snapshot objects only need .user_id/.start_time/.end_time
        (on-calls) or .user_id/.start_date/.end_date (leaves) - duck
        typed, so this module stays free of any DB/model import."""
        self._min_spacing_weeks = min_spacing_weeks
        self._oncall_intervals: dict[int, list[tuple[datetime, datetime]]] = (
            defaultdict(list)
        )
        self._leave_intervals: dict[int, list[tuple[date, date]]] = defaultdict(list)
        for oncall in oncall_snapshots:
            self._oncall_intervals[oncall.user_id].append(
                (oncall.start_time, oncall.end_time)
            )
        for leave in leave_snapshots:
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

        This matters because a leave rebalance
        (AutomationAdminService.rebalance_after_leave) regenerates only a ±30-day window around
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

    @classmethod
    def from_snapshots(
        cls,
        oncall_snapshots: Iterable,
        leave_snapshots: Iterable,
        min_spacing_weeks: int = 2,
    ) -> "AvailabilityIndex":
        return cls(oncall_snapshots, leave_snapshots, min_spacing_weeks)


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
    week_candidates: Sequence[Sequence[_T]],
    index: AvailabilityIndex,
    min_spacing_weeks: int = 2,
    fairness_key: Callable[[dict[int, _T]], tuple] | None = None,
) -> dict[int, _T]:
    """
    Branch-and-bound search that maximizes the number of on-call weeks
    that can be filled, respecting the legal spacing constraint (see
    OnCallSpacingRule, default 2 weeks).

    `fairness_key`, if given, breaks ties among plans that fill the same
    number of weeks - the default (None) preserves this function's
    original behavior exactly (best_assignment only replaced on strict
    improvement, so the first-found max-coverage plan wins ties by DFS/
    candidate order, byte-identical to every pre-existing caller). Only
    the automation planner (app/utils/automation/planner/) passes one,
    to prefer - among equal-coverage plans - the one closer to the
    published schedule / more balanced on-call counts / more faithful
    to rotation order (lower key wins, same semantics as Python's own
    `sorted(key=...)`).

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
    best_assignment: dict[int, _T] = {}
    current: dict[int, _T] = {}
    nodes_explored = 0

    def meets_spacing(user_id: int, start_time: datetime, end_time: datetime) -> bool:
        # Same predicate as the manual creation/move path (audit F03).
        return not any(
            oncall_violates_spacing(
                start_time, end_time, existing_start, existing_end, min_spacing_weeks
            )
            for existing_start, existing_end in intervals.get(user_id, [])
        )

    def recurse(week_index: int, filled_count: int) -> None:
        nonlocal nodes_explored, best_count, best_assignment

        if filled_count > best_count or (
            filled_count == best_count
            and fairness_key is not None
            and fairness_key(current) < fairness_key(best_assignment)
        ):
            best_count = filled_count
            best_assignment = dict(current)

        nodes_explored += 1
        if week_index == total_weeks or nodes_explored > _MAX_SEARCH_NODES:
            return

        weeks_remaining = total_weeks - week_index
        # Without a fairness_key, a branch that can only TIE the best
        # found so far (not beat it) is safe to prune - the first
        # max-coverage plan found already wins ties by DFS/candidate
        # order, so exploring another tying branch could never change
        # the result. With a fairness_key, that tying branch might
        # still win the tie-break - it must not be pruned away before
        # its fairness_key is ever compared, so the bound only prunes
        # branches that can't even reach a tie (strict `<`).
        cannot_improve = (
            filled_count + weeks_remaining < best_count
            if fairness_key is not None
            else filled_count + weeks_remaining <= best_count
        )
        if cannot_improve:
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
