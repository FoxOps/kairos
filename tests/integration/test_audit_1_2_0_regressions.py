"""Regression tests for the 1.2.0 audit (report/1.2.0/AUDIT_REPORT_1.2.0.md).

Started as the auditor's synthetic proofs (each asserting an observed
defect); every defect assertion was inverted into the intended behavior
as its fix landed - see report/1.2.0/AUDIT_FIXES_1.2.0.md for the
finding -> fix -> test mapping. Tests named after a fix that was already
verified at revision B kept their original positive assertion.
"""
from dataclasses import replace
from datetime import date, datetime, timedelta
import pytest
from app import db
from app.models import User, Group, OnCall, Shift, ShiftType, AutomationRule, Leave
from app.services.oncall_service import OnCallService
from app.services.shift_service import ShiftService
from app.services.automation_admin_service import AutomationAdminService as Admin
from app.services.settings_service import SettingsService
from app.utils.automation import queries
from app.utils.automation.planner import build_planning_request, plan_schedule
from app.utils.automation.planner.types import UserRef, LeaveSpan
from app.utils.automation.planner.oncall_planner import plan_oncalls_for_scope
from app.utils.automation.planner.shift_planner import plan_shifts_for_scope
from app.utils.automation.planner.fairness import compute_fairness_metrics
from tests.unit.test_planner_oncall_scenarios import BASE_RULES

def seed():
    g=Group(name='Synthetic',is_part_of_oncall=True,is_part_of_schedule=True)
    db.session.add(g); db.session.flush()
    users=[User(name=f'Synthetic {i}',email=f'u{i}@example.invalid',group_id=g.id) for i in range(4)]
    db.session.add_all(users); db.session.commit()
    return g,users

def oc(users, start=date(2026,1,2), end=date(2026,1,23), **kw):
    args=dict(start_date=start,end_date=end,group_id=None,rotation_order=users,
      rotation_anchor_epoch=start,existing_oncalls=(),existing_leaves=(),locked=frozenset(),published={},rules=BASE_RULES)
    args.update(kw)
    return plan_oncalls_for_scope(**args)

def shifts(users, day=date(2026,1,5), **kw):
    args=dict(start_date=day,end_date=day,group_id=None,oncall_group_ids=(None,),eligible_users=users,
      proposed_oncalls={},existing_oncalls=(),existing_leaves=(),locked=frozenset(),published={},
      rotation_order=users,rotation_anchor_epoch=date(2026,1,2),rules=BASE_RULES)
    args.update(kw)
    return plan_shifts_for_scope(**args)

def test_manual_oncall_ignores_spacing(test_app):
    _,us=seed()
    a,e=OnCallService.add_oncall(us[0],date(2026,1,2)); assert a and not e
    b,e=OnCallService.add_oncall(us[0],date(2026,1,9)); assert b and not e
    assert b.start_time-a.end_time == timedelta(hours=14)

def test_unchecked_rotation_user_is_added_back(test_app):
    _,us=seed()
    assert us[3].id in [u.id for u in queries.get_rotation_order([u.id for u in us[:3]])]

def test_locked_week_not_in_spacing_solver():
    u=(UserRef(1,'Synthetic',None),)
    f=oc(u,end=date(2026,1,9),locked=frozenset({(date(2026,1,2),None)}),published={(date(2026,1,2),None):1})
    assert [o.user_id for o in f.proposed]==[1,1]
    assert not f.unfilled

def test_overlap_block_unused_by_planner():
    u=(UserRef(1,'Synthetic',None),)
    f=shifts(u,proposed_oncalls={(date(2026,1,2),None):1},rules=replace(BASE_RULES,oncall_shift_overlap_block=True))
    assert len(f.proposed)==1 and f.proposed[0].role_slot=='oncall'
    assert not f.violations

def test_empty_population_has_no_work_requirement():
    f=shifts(())
    assert not f.proposed and not f.unfilled and not f.violations

def test_fairness_omits_zero_assignment_users():
    f=oc(tuple(UserRef(i,f'U{i}',None) for i in range(1,5)),end=date(2026,1,2))
    m=compute_fairness_metrics(f.proposed,())
    assert len(m.oncall_count_by_user)==1 and m.oncall_count_stddev==0

def test_nonfriday_anchor_shift_roles_are_wrong():
    # Wednesday 7 Jan begins an on-call; Thursday 8 Jan is inside it.
    u=(UserRef(1,'Synthetic',None),)
    f=shifts(u,day=date(2026,1,8),proposed_oncalls={(date(2026,1,7),None):1},rules=replace(BASE_RULES,oncall_anchor_weekday=2))
    assert f.proposed[0].role_slot!='oncall'

def test_shift_time_edits_invisible_to_diff(test_app):
    _,us=seed()
    Admin.generate_full(date(2026,1,2),date(2026,1,9),[u.id for u in us],False)
    row=Shift.query.filter_by(date=date(2026,1,5)).first()
    row.start_time=row.start_time.replace(hour=2); db.session.commit()
    req=build_planning_request(date(2026,1,2),date(2026,1,9)); plan=plan_schedule(req)
    proposed=next(s for s in plan.shifts if s.user_id==row.user_id and s.date==row.date)
    assert proposed.start_time!=row.start_time and proposed.change_type=='unchanged'

def test_preview_mutates_rotation_config(test_app):
    _,us=seed()
    Admin.generate_full(date(2026,1,2),date(2026,1,9),[u.id for u in us],True)
    from app.models import AutomationConfig
    assert AutomationConfig.get_rotation_epoch()==date(2026,1,2)
    assert AutomationConfig.get_rotation_order()==[u.id for u in us]
    assert OnCall.query.count()==0

def test_ineligible_groups_existing_rows_preserved(test_app):
    g,us=seed(); g.is_part_of_schedule=False; g.is_part_of_oncall=False
    t=ShiftType(name='synthetic',label='Synthetic',start_hour=9,end_hour=17); db.session.add(t); db.session.flush()
    db.session.add(Shift(user_id=us[0].id,group_id=g.id,shift_type_id=t.id,date=date(2026,1,5),start_time=datetime(2026,1,5,9),end_time=datetime(2026,1,5,17)))
    db.session.commit()
    SettingsService.set_shift_scheduling_mode('per_group'); SettingsService.set_oncall_scheduling_mode('per_group')
    plan=plan_schedule(build_planning_request(date(2026,1,2),date(2026,1,9)))
    assert not any(e.kind=='shift' and e.change_type=='removed' for e in plan.diff)
    assert plan.safe_to_apply

def test_end_before_start_accepted(test_app):
    _,us=seed()
    row,e=OnCallService.add_oncall(us[0],date(2026,1,2)); assert row
    row,e=OnCallService.api_update(row.id,datetime(2026,1,2,21),datetime(2026,1,1,7))
    assert not e and row.end_time<row.start_time


def test_fill_gaps_doublebooks_locked_holder(test_app):
    _,us=seed()
    row,e=OnCallService.add_oncall(us[0],date(2026,1,2)); assert row
    # Force other candidates unavailable for the second week.
    for u in us[1:]:
        db.session.add(Leave(user_id=u.id,start_date=date(2026,1,9),end_date=date(2026,1,16)))
    db.session.commit()
    Admin.refresh_shifts(date(2026,1,2),date(2026,1,9),'fill_gaps')
    assert OnCall.query.filter_by(user_id=us[0].id).count()==2


def test_shift_update_checks_type_hours_not_actual_hours(test_app):
    _,us=seed()
    t=ShiftType(name='synthetic',label='Synthetic',start_hour=13,end_hour=21)
    db.session.add(t)
    db.session.add(OnCall(user_id=us[0].id,group_id=us[0].group_id,start_time=datetime(2025,12,26,21),end_time=datetime(2026,1,2,7)))
    db.session.commit()
    AutomationRule.set('rest_after_oncall',{'min_rest_hours':5})
    row,e=ShiftService.api_create(us[0],t,datetime(2026,1,2,8),datetime(2026,1,2,16))
    assert row and not e  # Actual 1h rest, validation used type's 13:00 (6h).

def _oidc_sync(claims):
    from app.auth.oidc_auth import OIDCAuthLib
    from app.auth.user_manager import UserManager
    data=OIDCAuthLib().extract_user_info_from_token({},claims)
    return UserManager().sync_user_from_oidc(data)

def test_f02_unverified_email_does_not_link_local_admin(test_app):
    _,us=seed(); us[0].is_admin=True; db.session.commit()
    claims={'email':us[0].email,'name':'Synthetic claimant','sub':'different-identity','email_verified':False}
    assert _oidc_sync(claims) is None
    assert db.session.get(User,us[0].id).oidc_subject is None

def test_f02_unverified_string_claim_also_refused(test_app):
    _,us=seed()
    assert _oidc_sync({'email':us[0].email,'sub':'x','email_verified':'false'}) is None

def test_f02_trust_flag_allows_linking_unverified(test_app,monkeypatch):
    from config_oidc import OIDCConfig
    monkeypatch.setattr(OIDCConfig,'TRUST_UNVERIFIED_EMAIL',True)
    _,us=seed()
    user=_oidc_sync({'email':us[0].email,'sub':'kc-1','email_verified':False})
    assert user.id==us[0].id and user.oidc_subject=='kc-1'

def test_f02_verified_email_binds_then_matches_by_subject(test_app):
    _,us=seed()
    user=_oidc_sync({'email':us[0].email,'sub':'kc-1','email_verified':True})
    assert user.id==us[0].id and user.oidc_subject=='kc-1'
    # Bound accounts are matched by subject - email_verified no longer matters.
    again=_oidc_sync({'email':us[0].email,'sub':'kc-1','email_verified':False})
    assert again.id==us[0].id

def test_f02_bound_account_refuses_other_subject(test_app):
    _,us=seed()
    _oidc_sync({'email':us[0].email,'sub':'kc-1'})
    assert _oidc_sync({'email':us[0].email,'sub':'attacker','email_verified':True}) is None

def test_f02_new_user_with_unverified_email_is_created(test_app):
    seed()
    user=_oidc_sync({'email':'brand-new@example.invalid','sub':'kc-new','email_verified':False})
    assert user is not None and not user.is_admin and user.oidc_subject=='kc-new'

def test_f02_missing_subject_refused(test_app):
    seed()
    assert _oidc_sync({'email':'nosub@example.invalid'}) is None

def test_swapping_same_day_shifts_hits_unique_constraint(test_app):
    _,us=seed()
    from app.services.swap_service import SwapService
    from app.models import SwapRequest
    from sqlalchemy.exc import IntegrityError
    t=ShiftType(name='synthetic',label='Synthetic',start_hour=9,end_hour=17)
    db.session.add(t); db.session.flush()
    rows=[Shift(user_id=u.id,group_id=u.group_id,shift_type_id=t.id,date=date(2026,1,5),start_time=datetime(2026,1,5,9),end_time=datetime(2026,1,5,17)) for u in us[:2]]
    db.session.add_all(rows); db.session.flush()
    req=SwapRequest(requester_id=us[0].id,target_user_id=us[1].id,shift_id=rows[0].id,target_shift_id=rows[1].id,status=SwapRequest.AWAITING_ADMIN)
    db.session.add(req); db.session.commit()
    with pytest.raises(IntegrityError):
        SwapService.approve_swap(req,us[2])
    db.session.rollback()

def test_single_day_leave_ics_has_zero_duration(test_app):
    _,us=seed()
    from app.utils.export.ics_exporter import export_to_ics
    from icalendar import Calendar
    row=Leave(user_id=us[0].id,start_date=date(2026,1,5),end_date=date(2026,1,5))
    db.session.add(row); db.session.commit()
    event=Calendar.from_ical(export_to_ics([row])).walk('VEVENT')[0]
    assert event.decoded('dtstart')==event.decoded('dtend')

def test_fresh_migrations_have_schema_drift(test_app):
    from flask_migrate import upgrade
    from alembic.migration import MigrationContext
    from alembic.autogenerate import compare_metadata
    db.drop_all()
    upgrade(directory='migrations')
    with db.engine.connect() as connection:
        diffs=compare_metadata(MigrationContext.configure(connection),db.metadata)
    assert len(diffs)==3, diffs  # remove old index, replace nonunique token index

def test_two_plans_create_two_shared_oncalls(test_app):
    g,us=seed(); g.is_part_of_schedule=False; db.session.commit()
    from app.services.automation_apply_service import AutomationApplyService
    req=build_planning_request(date(2026,1,2),date(2026,1,2))
    first=plan_schedule(req)
    second=plan_schedule(replace(req,rotation_order={None:tuple(reversed(req.rotation_order[None]))}))
    assert first.oncalls[0].user_id!=second.oncalls[0].user_id
    assert AutomationApplyService.apply_plan(first).success
    assert AutomationApplyService.apply_plan(second).success
    assert OnCall.query.count()==2

def test_new_leave_between_plan_and_apply_not_checked(test_app):
    _,us=seed()
    from app.services.automation_apply_service import AutomationApplyService
    plan=plan_schedule(build_planning_request(date(2026,1,2),date(2026,1,2)))
    uid=plan.oncalls[0].user_id
    db.session.add(Leave(user_id=uid,start_date=date(2026,1,3),end_date=date(2026,1,4)))
    db.session.commit()
    assert AutomationApplyService.apply_plan(plan).success
    assert OnCall.query.filter_by(user_id=uid).count()==1

def test_f01_sso_only_mode_rejects_password_post_with_error_parameter(test_app,client,monkeypatch):
    _,us=seed(); us[0].set_password('Synthetic-Only-Password-719!'); db.session.commit()
    from config_oidc import OIDCConfig
    monkeypatch.setattr(OIDCConfig,'ENABLED',True)
    monkeypatch.setattr(OIDCConfig,'DISABLE_BASIC_AUTH',True)
    r=client.post('/login?oidc_error=1',data={'email':us[0].email,'password':'Synthetic-Only-Password-719!'})
    assert r.status_code==302
    with client.session_transaction() as session:
        assert session.get('_user_id') is None

def test_f01_sso_only_error_page_has_no_password_form(test_app,client,monkeypatch):
    from config_oidc import OIDCConfig
    monkeypatch.setattr(OIDCConfig,'ENABLED',True)
    monkeypatch.setattr(OIDCConfig,'DISABLE_BASIC_AUTH',True)
    r=client.get('/login?oidc_error=1')
    assert r.status_code==200 and b'name="password"' not in r.data

def test_preview_apply_use_same_staffing_rules(test_app):
    _,us=seed()
    from app.utils.automation.rules.shift_slots import get_shift_type_for_role, ROTATION_KEY
    t=get_shift_type_for_role(ROTATION_KEY)
    AutomationRule.set('staffing_limits',{str(t.id):0})
    preview=Admin.generate_full(date(2026,1,5),date(2026,1,5),[u.id for u in us],True)
    expected=sorted((s.user.id,s.shift_type.id,s.date) for s in preview.shifts)
    Admin.generate_full(date(2026,1,5),date(2026,1,5),[u.id for u in us],False)
    assert sorted((s.user_id,s.shift_type_id,s.date) for s in Shift.query.all())==expected
    assert not Shift.query.filter_by(shift_type_id=t.id).count()

def test_all_eligible_users_on_leave_reported():
    u=(UserRef(1,'Synthetic',None),)
    f=shifts(u,existing_leaves=(LeaveSpan(1,date(2026,1,5),date(2026,1,5)),))
    assert not f.proposed
    assert len(f.unfilled)==1 and f.unfilled[0].kind=='no_available_user'

def test_fallback_default_bypasses_rest_check():
    from app.utils.automation.planner.types import OnCallSnapshot
    u=(UserRef(1,'Synthetic',None),)
    past=OnCallSnapshot(1,None,datetime(2025,12,29,21),datetime(2026,1,5,7))
    rules=replace(BASE_RULES,oncall_anchor_weekday=0,rotation_slot_hours=(13,21),rest_after_oncall_hours=5,staffing_limits={200:0})
    f=shifts(u,existing_oncalls=(past,),rules=rules)
    assert len(f.proposed)==1 and not f.violations
    assert f.proposed[0].role_slot=='default'
    assert f.proposed[0].start_time-past.end_time==timedelta(hours=2)

def test_oncall_role_fallback_loses_rest_exemption_justification():
    u=(UserRef(1,'Synthetic',None),)
    f=shifts(u,day=date(2026,1,9),proposed_oncalls={(date(2026,1,2),None):1},
        rules=replace(BASE_RULES,rest_after_oncall_hours=11,staffing_limits={100:0}))
    assert f.proposed[0].role_slot=='default' and f.proposed[0].start_time.hour==9
    assert not f.violations

def test_rest_exclusion_does_not_repair_rotation_coverage():
    from app.utils.automation.planner.types import OnCallSnapshot
    u=(UserRef(1,'Synthetic A',None),UserRef(2,'Synthetic B',None))
    past=OnCallSnapshot(1,None,datetime(2025,12,29,21),datetime(2026,1,5,7))
    f=shifts(u,existing_oncalls=(past,),rules=replace(BASE_RULES,oncall_anchor_weekday=0,rest_after_oncall_hours=2))
    assert len(f.proposed)==1 and f.proposed[0].role_slot=='default'
    assert f.violations and not f.unfilled

def test_locked_shift_processed_late_exceeds_staffing_max():
    from app.utils.automation.planner.types import OnCallSnapshot
    u=(UserRef(1,'Synthetic A',None),UserRef(2,'Synthetic B',None))
    f=shifts(u,locked=frozenset({(date(2026,1,5),2)}),published={(date(2026,1,5),2):200},
        existing_oncalls=(OnCallSnapshot(1,None,datetime(2025,12,26,21),datetime(2026,1,2,7)),),
        rules=replace(BASE_RULES,staffing_limits={200:1}))
    assert sum(s.shift_type_id==200 for s in f.proposed)==2

def test_leave_rebalance_silently_ignores_unsafe_apply(test_app):
    _,us=seed()
    Admin.generate_full(date(2026,1,5),date(2026,1,5),[u.id for u in us],False)
    row=Shift.query.filter_by(user_id=us[0].id).first(); row.locked=True
    leave=Leave(user_id=us[0].id,start_date=date(2026,1,5),end_date=date(2026,1,5))
    db.session.add(leave); db.session.commit()
    result=Admin.rebalance_after_leave(leave)
    assert Shift.query.filter_by(id=row.id).count()==1
    assert not result[2] and not result[3] and not result[4] and not result[5]

def test_pre_window_oncall_is_used_for_role():
    from app.utils.automation.planner.types import OnCallSnapshot
    u=(UserRef(1,'Synthetic A',None),UserRef(2,'Synthetic B',None))
    past=OnCallSnapshot(2,None,datetime(2025,12,26,21),datetime(2026,1,2,7))
    f=shifts(u,existing_oncalls=(past,))
    assert next(s for s in f.proposed if s.user_id==2).role_slot=='rotation'

def test_transition_friday_incoming_holder_gets_rotation():
    u=(UserRef(1,'Synthetic A',None),UserRef(2,'Synthetic B',None))
    f=shifts(u,day=date(2026,1,9),proposed_oncalls={(date(2026,1,2),None):1,(date(2026,1,9),None):2})
    assert next(s for s in f.proposed if s.user_id==2).role_slot=='rotation'

def test_fallback_rest_violation_persists_through_refresh(test_app):
    _,us=seed()
    from app.utils.automation.rules.shift_slots import get_shift_type_for_role, ONCALL_KEY
    t=get_shift_type_for_role(ONCALL_KEY)
    AutomationRule.set('staffing_limits',{str(t.id):0})
    AutomationRule.set('rest_after_oncall',{'min_rest_hours':11})
    row,error=OnCallService.add_oncall(us[0],date(2026,1,2)); assert row and not error
    Admin.refresh_shifts(date(2026,1,9),date(2026,1,9),'none')
    shift=Shift.query.filter_by(user_id=us[0].id,date=date(2026,1,9)).one()
    assert shift.start_time-row.end_time==timedelta(hours=2)

def test_leave_api_reports_success_when_locked_rebalance_is_unsafe(test_app):
    _,us=seed()
    from app.services.leave_service import LeaveService
    Admin.generate_full(date(2026,1,5),date(2026,1,5),[u.id for u in us],False)
    row=Shift.query.filter_by(user_id=us[0].id).one(); row.locked=True; db.session.commit()
    leave,regenerated=LeaveService.add_leave(us[0],date(2026,1,5),date(2026,1,5))
    assert leave is not None and regenerated is not None
    updated,error,rebalance_failed=LeaveService.api_update(leave.id,leave.start_date,leave.end_date)
    assert updated is not None and error is None and not rebalance_failed
    assert Shift.query.filter_by(id=row.id).count()==1
