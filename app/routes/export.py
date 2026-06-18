from flask import make_response
from app import app
from app.models import Shift, OnCall, Leave
from app.utils.ics_exporter import generate_ics_shifts, generate_ics_oncall, generate_ics_leaves


# Exporter les shifts au format ICS
@app.route('/export/shifts')
def export_shifts():
    shifts = Shift.query.all()
    ics_content = generate_ics_shifts(shifts)
    response = make_response(ics_content)
    response.headers['Content-Type'] = 'text/calendar; charset=utf-8'
    response.headers['Content-Disposition'] = 'attachment; filename=shifts.ics'
    return response


# Exporter les astreintes au format ICS
@app.route('/export/oncall')
def export_oncall():
    on_calls = OnCall.query.all()
    ics_content = generate_ics_oncall(on_calls)
    response = make_response(ics_content)
    response.headers['Content-Type'] = 'text/calendar; charset=utf-8'
    response.headers['Content-Disposition'] = 'attachment; filename=oncall.ics'
    return response


# Exporter les congés au format ICS
@app.route('/export/leaves')
def export_leaves():
    leaves = Leave.query.all()
    ics_content = generate_ics_leaves(leaves)
    response = make_response(ics_content)
    response.headers['Content-Type'] = 'text/calendar; charset=utf-8'
    response.headers['Content-Disposition'] = 'attachment; filename=leaves.ics'
    return response