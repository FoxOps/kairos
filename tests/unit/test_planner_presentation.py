"""plan_messages() must aggregate - one flash message per (kind, shift
type)/rule_type with a count and date range, never one per individual
day. Real production bug: a multi-month generation run with a
recurring gap flooded the admin with one flash toast per occurrence
(sometimes hundreds) - see AdvancedShiftAutomation.generate_full_schedule()'s
own docstring for the equivalent fix already applied to the legacy
engine; this module (phase 6+ new planner) had never had it."""

from datetime import date, datetime, timezone

from app import db
from app.models import ShiftType
from app.utils.automation.planner.presentation import plan_messages
from app.utils.automation.planner.types import (
    FairnessMetrics,
    RuleViolation,
    SchedulePlan,
    UnfilledRequirement,
)


def _plan(unfilled=(), violations=()):
    return SchedulePlan(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        generated_at=datetime.now(timezone.utc),
        oncalls=(),
        shifts=(),
        unfilled=unfilled,
        violations=violations,
        fairness=FairnessMetrics(),
        diff=(),
        safe_to_apply=True,
    )


def test_repeated_mandatory_gaps_for_the_same_shift_type_produce_one_message(
    test_app,
):
    shift_type = ShiftType(name="oncall", label="13h-21h", start_hour=13, end_hour=21)
    db.session.add(shift_type)
    db.session.commit()

    unfilled = tuple(
        UnfilledRequirement(
            kind="mandatory_shift",
            date=date(2026, 1, d),
            group_id=None,
            reason_code="mandatory_shift_type_unfilled",
            detail=str(shift_type.id),
        )
        for d in (2, 9, 16, 23, 30)
    )

    oncall_messages, oncall_unfilled, shift_messages, shift_unfilled = plan_messages(
        _plan(unfilled=unfilled)
    )

    assert oncall_messages == []
    assert oncall_unfilled == []
    assert len(shift_messages) == 1
    assert "5" in shift_messages[0]
    assert "13h-21h" in shift_messages[0]
    assert "02/01/2026" in shift_messages[0]
    assert "30/01/2026" in shift_messages[0]
    assert shift_unfilled == list(u.date for u in unfilled)


def test_different_shift_types_produce_separate_messages(test_app):
    mandatory_type = ShiftType(
        name="oncall", label="13h-21h", start_hour=13, end_hour=21
    )
    staffing_type = ShiftType(
        name="rotation", label="07h-15h", start_hour=7, end_hour=15
    )
    db.session.add_all([mandatory_type, staffing_type])
    db.session.commit()

    unfilled = (
        UnfilledRequirement(
            kind="mandatory_shift",
            date=date(2026, 1, 2),
            group_id=None,
            reason_code="mandatory_shift_type_unfilled",
            detail=str(mandatory_type.id),
        ),
        UnfilledRequirement(
            kind="staffing_min",
            date=date(2026, 1, 2),
            group_id=None,
            reason_code="staffing_min_not_met",
            detail=str(staffing_type.id),
        ),
    )

    _, _, shift_messages, _ = plan_messages(_plan(unfilled=unfilled))

    assert len(shift_messages) == 2
    assert any("[ALERT]" in m and "13h-21h" in m for m in shift_messages)
    assert any("[WARN]" in m and "07h-15h" in m for m in shift_messages)


def test_repeated_oncall_week_gaps_produce_one_warning_message(test_app):
    unfilled = tuple(
        UnfilledRequirement(
            kind="oncall_week",
            date=date(2026, 1, d),
            group_id=None,
            reason_code="no_eligible_user",
        )
        for d in (2, 9, 16)
    )

    oncall_messages, oncall_unfilled, shift_messages, _ = plan_messages(
        _plan(unfilled=unfilled)
    )

    assert len(oncall_messages) == 1
    assert "[WARN]" in oncall_messages[0]
    assert "3" in oncall_messages[0]
    assert shift_messages == []
    assert oncall_unfilled == list(u.date for u in unfilled)


def test_repeated_rest_after_oncall_violations_produce_one_message(test_app):
    violations = tuple(
        RuleViolation(
            severity="warning",
            rule_type="rest_after_oncall",
            group_id=None,
            date=date(2026, 1, d),
            user_id=1,
            message="rest_after_oncall violated - user excluded from this day",
        )
        for d in (2, 9)
    )

    _, _, shift_messages, shift_unfilled = plan_messages(_plan(violations=violations))

    assert len(shift_messages) == 1
    assert "[WARN]" in shift_messages[0]
    assert "2" in shift_messages[0]
    assert shift_unfilled == []


def test_locked_but_no_published_assignment_is_never_surfaced(test_app):
    unfilled = (
        UnfilledRequirement(
            kind="staffing_min",
            date=date(2026, 1, 2),
            group_id=None,
            reason_code="locked_but_no_published_assignment",
        ),
    )

    oncall_messages, oncall_unfilled, shift_messages, shift_unfilled = plan_messages(
        _plan(unfilled=unfilled)
    )

    assert oncall_messages == oncall_unfilled == shift_messages == shift_unfilled == []
