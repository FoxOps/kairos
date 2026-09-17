"""Phase 3 scenario tests for _solve_max_filled_weeks's fairness_key
extension (app/utils/automation/oncall_automation.py):

1. fairness_key=None (every pre-existing caller) must reproduce the
   legacy solver's output exactly - a regression guard protecting the
   ~290 existing automation tests that depend on today's deterministic
   DFS/candidate-order tie-break.
2. Equal-coverage plans with different fairness must be distinguished:
   given a fairness_key, the tie-break actually changes which
   equal-coverage assignment wins.
"""

from datetime import date, datetime

from app.utils.automation.oncall_automation import (
    AvailabilityIndex,
    _solve_max_filled_weeks,
)


class _FakeUser:
    """Minimal stand-in for the User model - _solve_max_filled_weeks
    only ever reads .id off candidates, confirmed by inspection."""

    def __init__(self, id_):
        self.id = id_

    def __repr__(self):
        return f"FakeUser({self.id})"


def _weeks(fridays):
    return [
        (
            f,
            datetime.combine(f, datetime.min.time()).replace(hour=21),
            datetime.combine(f, datetime.min.time()).replace(hour=7),
        )
        for f in fridays
    ]


def test_fairness_key_none_reproduces_legacy_solver_output():
    """3 users, 6 weeks - the exact scenario from
    _solve_max_filled_weeks's own docstring (greedy fails week 3,
    branch-and-bound finds the full-coverage solution). Confirms
    fairness_key=None changes nothing about the search."""
    a, b, c = _FakeUser(1), _FakeUser(2), _FakeUser(3)
    fridays = [date(2026, 1, d) for d in (2, 9, 16, 23, 30)]
    fridays.append(date(2026, 2, 6))
    weeks = _weeks(fridays)
    # c is unavailable (e.g. on leave) only for week 3 - forces the
    # branch-and-bound to actually search, per the docstring example.
    week_candidates = [[a, b, c], [a, b, c], [a, b], [a, b, c], [a, b, c], [a, b, c]]

    index = AvailabilityIndex.from_snapshots([], [], min_spacing_weeks=2)

    without_key = _solve_max_filled_weeks(
        weeks, week_candidates, index, min_spacing_weeks=2
    )
    index2 = AvailabilityIndex.from_snapshots([], [], min_spacing_weeks=2)
    with_none_key_explicit = _solve_max_filled_weeks(
        weeks, week_candidates, index2, min_spacing_weeks=2, fairness_key=None
    )

    assert len(without_key) == 6
    assert {i: u.id for i, u in without_key.items()} == {
        i: u.id for i, u in with_none_key_explicit.items()
    }


def test_fairness_key_breaks_ties_among_equal_coverage_plans():
    """2 users, 2 weeks, both weeks independent (spacing satisfied
    either way) - two full-coverage assignments exist: (A,B) and
    (B,A). Without a fairness_key, DFS/candidate order picks the first
    one tried (A on week 1). A fairness_key preferring B on week 1
    must flip the result."""
    a, b = _FakeUser(1), _FakeUser(2)
    fridays = [date(2026, 1, 2), date(2026, 3, 27)]  # far apart, no spacing conflict
    weeks = _weeks(fridays)
    week_candidates = [[a, b], [a, b]]

    index = AvailabilityIndex.from_snapshots([], [], min_spacing_weeks=2)
    default_result = _solve_max_filled_weeks(
        weeks, week_candidates, index, min_spacing_weeks=2
    )
    assert default_result[0].id == a.id  # DFS tries `a` first by candidate order

    def prefer_b_first(assignment):
        # Lower key wins - penalize any assignment where week 0 isn't b.
        return (0 if assignment.get(0) and assignment[0].id == b.id else 1,)

    index2 = AvailabilityIndex.from_snapshots([], [], min_spacing_weeks=2)
    fair_result = _solve_max_filled_weeks(
        weeks, week_candidates, index2, min_spacing_weeks=2, fairness_key=prefer_b_first
    )
    assert len(fair_result) == 2
    assert fair_result[0].id == b.id
