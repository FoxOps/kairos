"""Regression tests for the 1.2.0 audit (report/1.2.0/AUDIT_REPORT_1.2.0.md).

Started as the auditor's synthetic proofs (each asserting an observed
defect); every defect assertion was inverted into the intended behavior
as its fix landed - see report/1.2.0/AUDIT_FIXES_1.2.0.md for the
finding -> fix -> test mapping. Tests named after a fix that was already
verified at revision B kept their original positive assertion.
"""

from dataclasses import replace
from datetime import date, datetime

import pytest

from app import db
from app.models import AutomationRule, Group, Leave, OnCall, Shift, ShiftType, User
from app.services.automation_admin_service import AutomationAdminService as Admin
from app.services.oncall_service import OnCallService
from app.services.settings_service import SettingsService
from app.services.shift_service import ShiftService
from app.utils.automation import queries
from app.utils.automation.planner import build_planning_request, plan_schedule
from app.utils.automation.planner.fairness import compute_fairness_metrics
from app.utils.automation.planner.oncall_planner import plan_oncalls_for_scope
from app.utils.automation.planner.shift_planner import plan_shifts_for_scope
from app.utils.automation.planner.types import LeaveSpan, UserRef
from tests.unit.test_planner_oncall_scenarios import BASE_RULES


def seed():
    g = Group(name="Synthetic", is_part_of_oncall=True, is_part_of_schedule=True)
    db.session.add(g)
    db.session.flush()
    users = [
        User(name=f"Synthetic {i}", email=f"u{i}@example.invalid", group_id=g.id)
        for i in range(4)
    ]
    db.session.add_all(users)
    db.session.commit()
    return g, users


def oc(users, start=date(2026, 1, 2), end=date(2026, 1, 23), **kw):
    args = {
        "start_date": start,
        "end_date": end,
        "group_id": None,
        "rotation_order": users,
        "rotation_anchor_epoch": start,
        "existing_oncalls": (),
        "existing_leaves": (),
        "locked": frozenset(),
        "published": {},
        "rules": BASE_RULES,
    }
    args.update(kw)
    return plan_oncalls_for_scope(**args)


def shifts(users, day=date(2026, 1, 5), **kw):
    args = {
        "start_date": day,
        "end_date": day,
        "group_id": None,
        "oncall_group_ids": (None,),
        "eligible_users": users,
        "proposed_oncalls": {},
        "existing_oncalls": (),
        "existing_leaves": (),
        "locked": frozenset(),
        "published": {},
        "rotation_order": users,
        "rotation_anchor_epoch": date(2026, 1, 2),
        "rules": BASE_RULES,
    }
    args.update(kw)
    return plan_shifts_for_scope(**args)


def test_f03_manual_oncall_enforces_spacing_with_explicit_reason(test_app):
    _, us = seed()
    a, e = OnCallService.add_oncall(us[0], date(2026, 1, 2))
    assert a and not e
    b, e = OnCallService.add_oncall(us[0], date(2026, 1, 9))
    assert b is None and "Espacement minimum de 2 semaine(s)" in e
    # Three weeks later respects the default 2-week spacing.
    c, e = OnCallService.add_oncall(us[0], date(2026, 1, 23))
    assert c and not e


def test_f03_manual_oncall_move_enforces_spacing(test_app):
    _, us = seed()
    a, _e = OnCallService.add_oncall(us[0], date(2026, 1, 2))
    b, _e = OnCallService.add_oncall(us[0], date(2026, 1, 23))
    row, e = OnCallService.api_update(
        b.id, datetime(2026, 1, 9, 21), datetime(2026, 1, 16, 7)
    )
    assert row is None and "Espacement minimum" in e


def test_f13_unchecked_rotation_user_is_excluded(test_app):
    _, us = seed()
    order = [
        u.id
        for u in queries.get_rotation_order(
            [u.id for u in us[:3]], excluded_ids=[us[3].id]
        )
    ]
    assert us[3].id not in order


def test_f13_new_user_not_in_saved_order_still_included(test_app):
    _, us = seed()
    order = [
        u.id
        for u in queries.get_rotation_order([u.id for u in us[:3]], excluded_ids=[])
    ]
    assert order[-1] == us[3].id


def test_f13_form_exclusion_persisted_and_planned(test_app):
    from types import SimpleNamespace

    from app.models import AutomationConfig

    _, us = seed()
    form = {f"rotation_order_{u.id}": str(i) for i, u in enumerate(us, 1)}
    form.update({f"include_{u.id}": "1" for u in us[:3]})
    assert Admin.parse_rotation_exclusions_from_form(
        SimpleNamespace(keys=form.keys, get=form.get, items=form.items)
    ) == [us[3].id]
    ids = [u.id for u in us[:3]]
    Admin.generate_full(
        date(2026, 1, 2), date(2026, 3, 27), ids, False, excluded_ids=[us[3].id]
    )
    assert AutomationConfig.get_rotation_excluded() == [us[3].id]
    assert OnCall.query.filter_by(user_id=us[3].id).count() == 0
    assert OnCall.query.count() > 0


def test_f04_locked_week_constrains_spacing_solver():
    u = (UserRef(1, "Synthetic", None),)
    f = oc(
        u,
        end=date(2026, 1, 9),
        locked=frozenset({(date(2026, 1, 2), None)}),
        published={(date(2026, 1, 2), None): 1},
    )
    # The sole user holds the locked week: the next one can't go to them.
    assert [o.user_id for o in f.proposed] == [1]
    assert [(x.date, x.reason_code) for x in f.unfilled] == [
        (date(2026, 1, 9), "no_candidate_meets_spacing")
    ]


def test_f06_overlap_block_enforced_by_planner():
    u = (UserRef(1, "Synthetic", None),)
    f = shifts(
        u,
        proposed_oncalls={(date(2026, 1, 2), None): 1},
        rules=replace(BASE_RULES, oncall_shift_overlap_block=True),
    )
    assert not f.proposed
    assert [v.rule_type for v in f.violations] == ["oncall_shift_overlap"]


def test_f06_overlap_block_off_keeps_coexistence():
    u = (UserRef(1, "Synthetic", None),)
    f = shifts(u, proposed_oncalls={(date(2026, 1, 2), None): 1})
    assert (
        len(f.proposed) == 1
        and f.proposed[0].role_slot == "oncall"
        and not f.violations
    )


def test_empty_population_has_no_work_requirement():
    f = shifts(())
    assert not f.proposed and not f.unfilled and not f.violations


def test_f17_fairness_includes_zero_assignment_users():
    users = tuple(UserRef(i, f"U{i}", None) for i in range(1, 5))
    f = oc(users, end=date(2026, 1, 2))
    m = compute_fairness_metrics(f.proposed, (), eligible_oncall_user_ids=[1, 2, 3, 4])
    assert len(m.oncall_count_by_user) == 4
    assert sorted(m.oncall_count_by_user.values()) == [0, 0, 0, 1]
    assert m.oncall_count_stddev > 0


def test_f11_nonfriday_anchor_current_holder_gets_oncall_role():
    # Wednesday 7 Jan begins an on-call; Thursday 8 Jan is inside it.
    u = (UserRef(1, "Synthetic", None),)
    f = shifts(
        u,
        day=date(2026, 1, 8),
        proposed_oncalls={(date(2026, 1, 7), None): 1},
        rules=replace(BASE_RULES, oncall_anchor_weekday=2),
    )
    assert f.proposed[0].role_slot == "oncall"


def test_f11_proposed_oncall_real_end_used_for_rest():
    # The on-call phase proposed an interval ending at 12:00 (its own
    # scope's override), not the shift scope's 07:00: a 13:00 shift on
    # that day only gets 1h rest.
    u = (UserRef(1, "Synthetic", None),)
    f = shifts(
        u,
        day=date(2026, 1, 9),
        proposed_oncalls={(date(2026, 1, 2), None): 1},
        proposed_oncall_intervals={
            (date(2026, 1, 2), None): (
                datetime(2026, 1, 2, 21),
                datetime(2026, 1, 9, 12),
            )
        },
        rules=replace(
            BASE_RULES,
            rest_after_oncall_hours=2,
            staffing_limits={100: 0},
            default_slot_hours=(13, 21),
        ),
    )
    assert not f.proposed
    assert f.violations[0].rule_type == "rest_after_oncall"


def test_f12_shift_time_edits_visible_to_diff_and_repaired(test_app):
    _, us = seed()
    Admin.generate_full(date(2026, 1, 2), date(2026, 1, 9), [u.id for u in us], False)
    row = Shift.query.filter_by(date=date(2026, 1, 5)).first()
    row.start_time = row.start_time.replace(hour=2)
    db.session.commit()
    req = build_planning_request(date(2026, 1, 2), date(2026, 1, 9))
    plan = plan_schedule(req)
    proposed = next(
        s for s in plan.shifts if s.user_id == row.user_id and s.date == row.date
    )
    assert proposed.change_type == "updated"
    from app.services.automation_apply_service import AutomationApplyService

    result = AutomationApplyService.apply_plan(plan)
    assert result.success and result.shifts_updated == 1
    assert db.session.get(Shift, row.id).start_time == proposed.start_time


def test_f14_preview_does_not_mutate_rotation_config(test_app):
    from app.models import AutomationConfig

    _, us = seed()
    before_epoch = AutomationConfig.get_rotation_epoch()
    preview = Admin.generate_full(
        date(2026, 1, 2), date(2026, 1, 9), [u.id for u in reversed(us)], True
    )
    assert AutomationConfig.get_rotation_epoch() == before_epoch
    assert AutomationConfig.get_rotation_order() == []
    assert OnCall.query.count() == 0
    # ...but the preview itself used the form's order: first pick = us[3].
    assert preview.oncalls[0].user.id == us[3].id


def test_f14_save_failure_aborts_generation(test_app, monkeypatch):
    _, us = seed()
    monkeypatch.setattr(
        Admin, "save_rotation_order", staticmethod(lambda *a, **k: "boom")
    )
    with pytest.raises(RuntimeError):
        Admin.generate_full(
            date(2026, 1, 2), date(2026, 1, 9), [u.id for u in us], False
        )
    assert OnCall.query.count() == 0


def test_ineligible_groups_existing_rows_preserved(test_app):
    g, us = seed()
    g.is_part_of_schedule = False
    g.is_part_of_oncall = False
    t = ShiftType(name="synthetic", label="Synthetic", start_hour=9, end_hour=17)
    db.session.add(t)
    db.session.flush()
    db.session.add(
        Shift(
            user_id=us[0].id,
            group_id=g.id,
            shift_type_id=t.id,
            date=date(2026, 1, 5),
            start_time=datetime(2026, 1, 5, 9),
            end_time=datetime(2026, 1, 5, 17),
        )
    )
    db.session.commit()
    SettingsService.set_shift_scheduling_mode("per_group")
    SettingsService.set_oncall_scheduling_mode("per_group")
    plan = plan_schedule(build_planning_request(date(2026, 1, 2), date(2026, 1, 9)))
    assert not any(e.kind == "shift" and e.change_type == "removed" for e in plan.diff)
    assert plan.safe_to_apply


def test_f09_oncall_end_before_start_rejected(test_app):
    _, us = seed()
    row, e = OnCallService.add_oncall(us[0], date(2026, 1, 2))
    assert row
    updated, e = OnCallService.api_update(
        row.id, datetime(2026, 1, 2, 21), datetime(2026, 1, 1, 7)
    )
    assert updated is None and "postérieure" in e


def test_f09_oncall_resize_off_weekly_end_rejected(test_app):
    _, us = seed()
    row, e = OnCallService.add_oncall(us[0], date(2026, 1, 2))
    updated, e = OnCallService.api_update(
        row.id, datetime(2026, 1, 2, 21), datetime(2026, 1, 5, 7)
    )
    assert updated is None and "fin hebdomadaire" in e


def test_f04_fill_gaps_does_not_doublebook_published_holder(test_app):
    _, us = seed()
    row, e = OnCallService.add_oncall(us[0], date(2026, 1, 2))
    assert row
    # Force other candidates unavailable for the second week.
    for u in us[1:]:
        db.session.add(
            Leave(user_id=u.id, start_date=date(2026, 1, 9), end_date=date(2026, 1, 16))
        )
    db.session.commit()
    Admin.refresh_shifts(date(2026, 1, 2), date(2026, 1, 9), "fill_gaps")
    assert OnCall.query.filter_by(user_id=us[0].id).count() == 1


def test_f09_shift_create_checks_actual_hours(test_app):
    _, us = seed()
    t = ShiftType(name="synthetic", label="Synthetic", start_hour=13, end_hour=21)
    db.session.add(t)
    db.session.add(
        OnCall(
            user_id=us[0].id,
            group_id=us[0].group_id,
            start_time=datetime(2025, 12, 26, 21),
            end_time=datetime(2026, 1, 2, 7),
        )
    )
    db.session.commit()
    AutomationRule.set("rest_after_oncall", {"min_rest_hours": 5})
    row, e = ShiftService.api_create(
        us[0], t, datetime(2026, 1, 2, 8), datetime(2026, 1, 2, 16)
    )
    # Actual 1h rest is checked, not the type's nominal 13:00 (6h).
    assert row is None and "reposer" in e


def test_f09_shift_end_before_start_rejected(test_app):
    _, us = seed()
    t = ShiftType(name="synthetic", label="Synthetic", start_hour=9, end_hour=17)
    db.session.add(t)
    db.session.commit()
    row, e = ShiftService.api_create(
        us[0], t, datetime(2026, 1, 5, 17), datetime(2026, 1, 5, 9)
    )
    assert row is None and "postérieure" in e


def _oidc_sync(claims):
    from app.auth.oidc_auth import OIDCAuthLib
    from app.auth.user_manager import UserManager

    data = OIDCAuthLib().extract_user_info_from_token({}, claims)
    return UserManager().sync_user_from_oidc(data)


def test_f02_unverified_email_does_not_link_local_admin(test_app):
    _, us = seed()
    us[0].is_admin = True
    db.session.commit()
    claims = {
        "email": us[0].email,
        "name": "Synthetic claimant",
        "sub": "different-identity",
        "email_verified": False,
    }
    assert _oidc_sync(claims) is None
    assert db.session.get(User, us[0].id).oidc_subject is None


def test_f02_unverified_string_claim_also_refused(test_app):
    _, us = seed()
    assert (
        _oidc_sync({"email": us[0].email, "sub": "x", "email_verified": "false"})
        is None
    )


def test_f02_trust_flag_allows_linking_unverified(test_app, monkeypatch):
    from config_oidc import OIDCConfig

    monkeypatch.setattr(OIDCConfig, "TRUST_UNVERIFIED_EMAIL", True)
    _, us = seed()
    user = _oidc_sync({"email": us[0].email, "sub": "kc-1", "email_verified": False})
    assert user.id == us[0].id and user.oidc_subject == "kc-1"


def test_f02_verified_email_binds_then_matches_by_subject(test_app):
    _, us = seed()
    user = _oidc_sync({"email": us[0].email, "sub": "kc-1", "email_verified": True})
    assert user.id == us[0].id and user.oidc_subject == "kc-1"
    # Bound accounts are matched by subject - email_verified no longer matters.
    again = _oidc_sync({"email": us[0].email, "sub": "kc-1", "email_verified": False})
    assert again.id == us[0].id


def test_f02_bound_account_refuses_other_subject(test_app):
    _, us = seed()
    _oidc_sync({"email": us[0].email, "sub": "kc-1"})
    assert (
        _oidc_sync({"email": us[0].email, "sub": "attacker", "email_verified": True})
        is None
    )


def test_f02_new_user_with_unverified_email_is_created(test_app):
    seed()
    user = _oidc_sync(
        {"email": "brand-new@example.invalid", "sub": "kc-new", "email_verified": False}
    )
    assert user is not None and not user.is_admin and user.oidc_subject == "kc-new"


def test_f02_missing_subject_refused(test_app):
    seed()
    assert _oidc_sync({"email": "nosub@example.invalid"}) is None


def _same_day_swap(us, **shift_kwargs):
    from app.models import SwapRequest

    t = ShiftType(name="synthetic", label="Synthetic", start_hour=9, end_hour=17)
    db.session.add(t)
    db.session.flush()
    rows = [
        Shift(
            user_id=u.id,
            group_id=u.group_id,
            shift_type_id=t.id,
            date=date(2026, 1, 5),
            start_time=datetime(2026, 1, 5, 9),
            end_time=datetime(2026, 1, 5, 17),
            **shift_kwargs,
        )
        for u in us[:2]
    ]
    db.session.add_all(rows)
    db.session.flush()
    req = SwapRequest(
        requester_id=us[0].id,
        target_user_id=us[1].id,
        shift_id=rows[0].id,
        target_shift_id=rows[1].id,
        status=SwapRequest.AWAITING_ADMIN,
    )
    db.session.add(req)
    db.session.commit()
    return rows, req


def test_f15_same_day_swap_approves_and_reverts(test_app):
    from app.services.swap_service import SwapService

    _, us = seed()
    rows, req = _same_day_swap(us)
    assert SwapService.approve_swap(req, us[2]) is None
    assert db.session.get(Shift, rows[0].id).user_id == us[1].id
    assert db.session.get(Shift, rows[1].id).user_id == us[0].id
    assert db.session.get(Shift, rows[0].id).date == date(2026, 1, 5)
    assert SwapService.revert_swap(req, us[2]) is None
    assert db.session.get(Shift, rows[0].id).user_id == us[0].id


def test_f15_swap_updates_group_snapshot_to_new_owner(test_app):
    from app.services.swap_service import SwapService

    g, us = seed()
    other = Group(name="Other", is_part_of_oncall=True, is_part_of_schedule=True)
    db.session.add(other)
    db.session.flush()
    us[1].group_id = other.id
    db.session.commit()
    rows, req = _same_day_swap(us)
    assert SwapService.approve_swap(req, us[2]) is None
    assert db.session.get(Shift, rows[0].id).group_id == other.id
    assert db.session.get(Shift, rows[1].id).group_id == g.id


def test_f15_swap_refuses_locked_shift(test_app):
    from app.services.swap_service import SwapService

    _, us = seed()
    rows, req = _same_day_swap(us, locked=True)
    error = SwapService.approve_swap(req, us[2])
    assert error and "verrouillé" in error


def test_f15_swap_enforces_rest_after_oncall(test_app):
    from app.services.swap_service import SwapService

    _, us = seed()
    db.session.add(
        OnCall(
            user_id=us[1].id,
            group_id=us[1].group_id,
            start_time=datetime(2025, 12, 29, 21),
            end_time=datetime(2026, 1, 5, 7),
        )
    )
    db.session.commit()
    AutomationRule.set("rest_after_oncall", {"min_rest_hours": 11})
    rows, req = _same_day_swap(us)
    error = SwapService.approve_swap(req, us[2])
    assert error and "reposer" in error


def test_f16_single_day_leave_ics_spans_the_whole_day(test_app):
    _, us = seed()
    from icalendar import Calendar

    from app.utils.export.ics_exporter import export_to_ics

    row = Leave(
        user_id=us[0].id, start_date=date(2026, 1, 5), end_date=date(2026, 1, 7)
    )
    db.session.add(row)
    db.session.commit()
    event = Calendar.from_ical(export_to_ics([row])).walk("VEVENT")[0]
    assert event.decoded("dtstart") == date(2026, 1, 5)
    assert event.decoded("dtend") == date(2026, 1, 8)


def test_f18_fresh_migrations_match_model_metadata(test_app):
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext
    from flask_migrate import upgrade

    db.drop_all()
    upgrade(directory="migrations")
    with db.engine.connect() as connection:
        diffs = compare_metadata(MigrationContext.configure(connection), db.metadata)
    assert diffs == []


def test_f07_second_plan_of_same_window_refused_as_stale(test_app):
    g, us = seed()
    g.is_part_of_schedule = False
    db.session.commit()
    from app.services.automation_apply_service import AutomationApplyService

    req = build_planning_request(date(2026, 1, 2), date(2026, 1, 2))
    first = plan_schedule(req)
    second = plan_schedule(build_planning_request(date(2026, 1, 2), date(2026, 1, 2)))
    assert AutomationApplyService.apply_plan(first).success
    result = AutomationApplyService.apply_plan(second)
    assert not result.success and result.stale
    assert OnCall.query.count() == 1


def test_f07_new_leave_between_plan_and_apply_refuses_plan(test_app):
    _, us = seed()
    from app.services.automation_apply_service import AutomationApplyService

    plan = plan_schedule(build_planning_request(date(2026, 1, 2), date(2026, 1, 2)))
    uid = plan.oncalls[0].user_id
    db.session.add(
        Leave(user_id=uid, start_date=date(2026, 1, 3), end_date=date(2026, 1, 4))
    )
    db.session.commit()
    result = AutomationApplyService.apply_plan(plan)
    assert not result.success and result.stale
    assert OnCall.query.filter_by(user_id=uid).count() == 0


def test_f01_sso_only_mode_rejects_password_post_with_error_parameter(
    test_app, client, monkeypatch
):
    _, us = seed()
    us[0].set_password("Synthetic-Only-Password-719!")
    db.session.commit()
    from config_oidc import OIDCConfig

    monkeypatch.setattr(OIDCConfig, "ENABLED", True)
    monkeypatch.setattr(OIDCConfig, "DISABLE_BASIC_AUTH", True)
    r = client.post(
        "/login?oidc_error=1",
        data={"email": us[0].email, "password": "Synthetic-Only-Password-719!"},
    )
    assert r.status_code == 302
    with client.session_transaction() as session:
        assert session.get("_user_id") is None


def test_f01_sso_only_error_page_has_no_password_form(test_app, client, monkeypatch):
    from config_oidc import OIDCConfig

    monkeypatch.setattr(OIDCConfig, "ENABLED", True)
    monkeypatch.setattr(OIDCConfig, "DISABLE_BASIC_AUTH", True)
    r = client.get("/login?oidc_error=1")
    assert r.status_code == 200 and b'name="password"' not in r.data


def test_preview_apply_use_same_staffing_rules(test_app):
    _, us = seed()
    from app.utils.automation.rules.shift_slots import (
        ROTATION_KEY,
        get_shift_type_for_role,
    )

    t = get_shift_type_for_role(ROTATION_KEY)
    AutomationRule.set("staffing_limits", {str(t.id): 0})
    preview = Admin.generate_full(
        date(2026, 1, 5), date(2026, 1, 5), [u.id for u in us], True
    )
    expected = sorted((s.user.id, s.shift_type.id, s.date) for s in preview.shifts)
    Admin.generate_full(date(2026, 1, 5), date(2026, 1, 5), [u.id for u in us], False)
    assert (
        sorted((s.user_id, s.shift_type_id, s.date) for s in Shift.query.all())
        == expected
    )
    assert not Shift.query.filter_by(shift_type_id=t.id).count()


def test_all_eligible_users_on_leave_reported():
    u = (UserRef(1, "Synthetic", None),)
    f = shifts(u, existing_leaves=(LeaveSpan(1, date(2026, 1, 5), date(2026, 1, 5)),))
    assert not f.proposed
    assert len(f.unfilled) == 1 and f.unfilled[0].kind == "no_available_user"


def test_f19_fallback_default_is_rest_checked():
    from app.utils.automation.planner.types import OnCallSnapshot

    # Monday-anchor on-call ended Monday 5 Jan 07:00; Tuesday 6 Jan the
    # former holder is "last week's" -> rotation 13:00 (30h rest, OK),
    # but rotation is capped at 0 -> default 09:00 = 26h < 28h.
    u = (UserRef(1, "Synthetic", None),)
    past = OnCallSnapshot(1, None, datetime(2025, 12, 29, 21), datetime(2026, 1, 5, 7))
    rules = replace(
        BASE_RULES,
        oncall_anchor_weekday=0,
        rotation_slot_hours=(13, 21),
        rest_after_oncall_hours=28,
        staffing_limits={200: 0},
    )
    f = shifts(u, day=date(2026, 1, 6), existing_oncalls=(past,), rules=rules)
    assert not f.proposed
    assert [v.rule_type for v in f.violations] == ["rest_after_oncall"]


def test_f19_oncall_role_fallback_loses_rest_exemption():
    u = (UserRef(1, "Synthetic", None),)
    f = shifts(
        u,
        day=date(2026, 1, 9),
        proposed_oncalls={(date(2026, 1, 2), None): 1},
        rules=replace(BASE_RULES, rest_after_oncall_hours=11, staffing_limits={100: 0}),
    )
    assert not f.proposed
    assert [v.rule_type for v in f.violations] == ["rest_after_oncall"]


def test_f19_oncall_role_keeps_exemption_when_not_downgraded():
    u = (UserRef(1, "Synthetic", None),)
    f = shifts(
        u,
        day=date(2026, 1, 9),
        proposed_oncalls={(date(2026, 1, 2), None): 1},
        rules=replace(BASE_RULES, rest_after_oncall_hours=11),
    )
    assert f.proposed[0].role_slot == "oncall" and not f.violations


def test_f10_rest_exclusion_rotation_coverage_repaired():
    from app.utils.automation.planner.types import OnCallSnapshot

    # Former holder picked for 07:00 rotation on Tuesday 6 Jan has 24h
    # rest < 25h: excluded. B, otherwise on 09-17, takes rotation.
    u = (UserRef(1, "Synthetic A", None), UserRef(2, "Synthetic B", None))
    past = OnCallSnapshot(1, None, datetime(2025, 12, 29, 21), datetime(2026, 1, 5, 7))
    f = shifts(
        u,
        day=date(2026, 1, 6),
        existing_oncalls=(past,),
        rules=replace(BASE_RULES, oncall_anchor_weekday=0, rest_after_oncall_hours=25),
    )
    assert [(s.user_id, s.role_slot) for s in f.proposed] == [(2, "rotation")]
    assert f.violations and not f.unfilled


def test_f10_rotation_uncovered_reported_when_no_replacement():
    from app.utils.automation.planner.types import OnCallSnapshot

    u = (UserRef(1, "Synthetic A", None),)
    past = OnCallSnapshot(1, None, datetime(2025, 12, 29, 21), datetime(2026, 1, 5, 7))
    f = shifts(
        u,
        day=date(2026, 1, 6),
        existing_oncalls=(past,),
        rules=replace(BASE_RULES, oncall_anchor_weekday=0, rest_after_oncall_hours=25),
    )
    assert not f.proposed
    assert [(x.kind, x.reason_code) for x in f.unfilled] == [
        ("role_uncovered", "rotation_uncovered")
    ]


def test_f11_monday_anchor_transition_day_belongs_to_departing_holder():
    from app.utils.automation.planner.types import OnCallSnapshot

    u = (UserRef(1, "Synthetic A", None),)
    past = OnCallSnapshot(1, None, datetime(2025, 12, 29, 21), datetime(2026, 1, 5, 7))
    f = shifts(
        u,
        existing_oncalls=(past,),
        rules=replace(BASE_RULES, oncall_anchor_weekday=0, rest_after_oncall_hours=25),
    )
    assert f.proposed[0].role_slot == "oncall" and not f.violations


def test_f20_locked_shift_reserves_staffing_capacity():
    from app.utils.automation.planner.types import OnCallSnapshot

    u = (UserRef(1, "Synthetic A", None), UserRef(2, "Synthetic B", None))
    f = shifts(
        u,
        locked=frozenset({(date(2026, 1, 5), 2)}),
        published={(date(2026, 1, 5), 2): 200},
        existing_oncalls=(
            OnCallSnapshot(
                1, None, datetime(2025, 12, 26, 21), datetime(2026, 1, 2, 7)
            ),
        ),
        rules=replace(BASE_RULES, staffing_limits={200: 1}),
    )
    assert sum(s.shift_type_id == 200 for s in f.proposed) == 1
    assert {s.user_id: s.role_slot for s in f.proposed} == {2: "rotation", 1: "default"}


def test_f20_locked_shift_keeps_real_interval():
    u = (UserRef(2, "Synthetic B", None),)
    f = shifts(
        u,
        locked=frozenset({(date(2026, 1, 5), 2)}),
        published={(date(2026, 1, 5), 2): 200},
        published_intervals={
            (date(2026, 1, 5), 2): (datetime(2026, 1, 5, 6), datetime(2026, 1, 5, 14))
        },
    )
    assert f.proposed[0].start_time == datetime(2026, 1, 5, 6)
    assert f.proposed[0].change_type == "unchanged"


def test_f21_leave_rebalance_reports_unsafe_apply(test_app):
    _, us = seed()
    Admin.generate_full(date(2026, 1, 5), date(2026, 1, 5), [u.id for u in us], False)
    row = Shift.query.filter_by(user_id=us[0].id).first()
    row.locked = True
    leave = Leave(
        user_id=us[0].id, start_date=date(2026, 1, 5), end_date=date(2026, 1, 5)
    )
    db.session.add(leave)
    db.session.commit()
    regenerated, messages, _u, failed_shift_dates, _p, _s = Admin.rebalance_after_leave(
        leave
    )
    assert Shift.query.filter_by(id=row.id).count() == 1
    assert regenerated == []
    assert failed_shift_dates == [date(2026, 1, 5)]
    assert any(m.startswith("[ERROR]") for m in messages)


def test_pre_window_oncall_is_used_for_role():
    from app.utils.automation.planner.types import OnCallSnapshot

    u = (UserRef(1, "Synthetic A", None), UserRef(2, "Synthetic B", None))
    past = OnCallSnapshot(2, None, datetime(2025, 12, 26, 21), datetime(2026, 1, 2, 7))
    f = shifts(u, existing_oncalls=(past,))
    assert next(s for s in f.proposed if s.user_id == 2).role_slot == "rotation"


def test_transition_friday_incoming_holder_gets_rotation():
    u = (UserRef(1, "Synthetic A", None), UserRef(2, "Synthetic B", None))
    f = shifts(
        u,
        day=date(2026, 1, 9),
        proposed_oncalls={(date(2026, 1, 2), None): 1, (date(2026, 1, 9), None): 2},
    )
    assert next(s for s in f.proposed if s.user_id == 2).role_slot == "rotation"


def test_f19_fallback_rest_violation_not_persisted_through_refresh(test_app):
    _, us = seed()
    from app.utils.automation.rules.shift_slots import (
        ONCALL_KEY,
        get_shift_type_for_role,
    )

    t = get_shift_type_for_role(ONCALL_KEY)
    AutomationRule.set("staffing_limits", {str(t.id): 0})
    AutomationRule.set("rest_after_oncall", {"min_rest_hours": 11})
    row, error = OnCallService.add_oncall(us[0], date(2026, 1, 2))
    assert row and not error
    Admin.refresh_shifts(date(2026, 1, 9), date(2026, 1, 9), "none")
    assert Shift.query.filter_by(user_id=us[0].id, date=date(2026, 1, 9)).count() == 0
    # Everyone else still got their shift.
    assert Shift.query.filter_by(date=date(2026, 1, 9)).count() == len(us) - 1


def test_f21_leave_api_reports_failure_when_locked_rebalance_is_unsafe(test_app):
    _, us = seed()
    from app.models import AppNotification
    from app.services.leave_service import LeaveService

    us[3].is_admin = True
    db.session.commit()
    Admin.generate_full(date(2026, 1, 5), date(2026, 1, 5), [u.id for u in us], False)
    row = Shift.query.filter_by(user_id=us[0].id).one()
    row.locked = True
    db.session.commit()
    leave, regenerated = LeaveService.add_leave(
        us[0], date(2026, 1, 5), date(2026, 1, 5)
    )
    assert leave is not None and regenerated is None
    updated, error, rebalance_failed = LeaveService.api_update(
        leave.id, leave.start_date, leave.end_date
    )
    assert updated is not None and error is None and rebalance_failed
    assert AppNotification.query.filter_by(user_id=us[3].id).count() >= 1
    assert Shift.query.filter_by(id=row.id).count() == 1


def test_f10_leave_minimum_is_per_group_in_per_group_mode(test_app):
    from app.utils.helpers import leave_keeps_minimum_headcount

    a = Group(name="Solo", is_part_of_oncall=True, is_part_of_schedule=True)
    b = Group(name="Pair", is_part_of_oncall=True, is_part_of_schedule=True)
    db.session.add_all([a, b])
    db.session.flush()
    solo = User(name="Solo", email="solo@example.invalid", group_id=a.id)
    db.session.add_all(
        [
            solo,
            User(name="Pair 1", email="p1@example.invalid", group_id=b.id),
            User(name="Pair 2", email="p2@example.invalid", group_id=b.id),
        ]
    )
    db.session.commit()
    monday = date(2026, 1, 5)
    # Shared mode: the pooled headcount (3) allows it.
    assert leave_keeps_minimum_headcount(solo, monday, monday)
    SettingsService.set_shift_scheduling_mode("per_group")
    # Per-group: Solo is their group's last available worker.
    assert not leave_keeps_minimum_headcount(solo, monday, monday)


def test_f13_route_renders_excluded_user_unticked(logged_in_client):
    from app.models import AutomationConfig

    _, us = seed()
    AutomationConfig.set_rotation_order([u.id for u in us[:3]])
    AutomationConfig.set_rotation_excluded([us[3].id])
    html = logged_in_client.get("/admin/automation/full").get_data(as_text=True)
    assert f'name="include_{us[3].id}" value="1" >' in html
    assert f'name="include_{us[0].id}" value="1" checked>' in html


def test_f13_route_refuses_empty_selection(logged_in_client):
    from app.models import AutomationConfig

    _, us = seed()
    data = {f"rotation_order_{u.id}": str(i) for i, u in enumerate(us, 1)}
    data.update(action="save_order", start_date="2026-01-02", end_date="2026-01-09")
    resp = logged_in_client.post("/admin/automation/full", data=data)
    assert resp.status_code == 302
    assert AutomationConfig.get_rotation_order() == []
