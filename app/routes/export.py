from flask import make_response
from sqlalchemy.orm import joinedload
from app import app
from app.models import Shift, OnCall, Leave
from app.utils.ics_exporter import generate_ics_shifts, generate_ics_oncall, generate_ics_leaves


@app.route('/export/shifts')
def export_shifts():
    shifts = Shift.query.options(joinedload(Shift.user)).order_by(Shift.start_time).all()
    ics_content = generate_ics_shifts(shifts)
    response = make_response(ics_content)
    response.headers['Content-Type'] = 'text/calendar; charset=utf-8'
    response.headers['Content-Disposition'] = 'attachment; filename=shifts.ics'
    return response


@app.route('/export/oncall')
def export_oncall():
    on_calls = OnCall.query.options(joinedload(OnCall.user)).order_by(OnCall.start_time).all()
    ics_content = generate_ics_oncall(on_calls)
    response = make_response(ics_content)
    response.headers['Content-Type'] = 'text/calendar; charset=utf-8'
    response.headers['Content-Disposition'] = 'attachment; filename=oncall.ics'
    return response


@app.route('/export/leaves')
def export_leaves():
    leaves = Leave.query.options(joinedload(Leave.user)).order_by(Leave.start_date).all()
    ics_content = generate_ics_leaves(leaves)
    response = make_response(ics_content)
    response.headers['Content-Type'] = 'text/calendar; charset=utf-8'
    response.headers['Content-Disposition'] = 'attachment; filename=leaves.ics'
    return response
