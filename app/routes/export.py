from flask import make_response, request, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload
from app import app, db
from app.models import Shift, OnCall, Leave, User
from app.utils.ics_exporter import generate_ics_shifts, generate_ics_oncall, generate_ics_leaves


def _get_export_scope():
    """Récupère le scope de l'export depuis les paramètres de requête."""
    scope = request.args.get('scope', 'all')
    if scope not in ['all', 'my']:
        scope = 'all'
    return scope


def _filter_by_scope(query, model, scope, current_user):
    """Filtre une requête selon le scope (all ou my)."""
    if scope == 'my':
        return query.filter(model.user_id == current_user.id)
    return query


@app.route('/export/shifts')
@login_required
def export_shifts():
    scope = _get_export_scope()
    
    query = Shift.query.options(joinedload(Shift.user)).order_by(Shift.start_time)
    
    # Vérification des permissions : un utilisateur normal ne peut exporter que ses propres données
    if not current_user.is_admin and scope == 'all':
        flash('❌ Vous ne pouvez exporter que vos propres shifts.', 'danger')
        return redirect(url_for('schedule'))
    
    filtered_query = _filter_by_scope(query, Shift, scope, current_user)
    shifts = filtered_query.all()
    
    ics_content = generate_ics_shifts(shifts)
    response = make_response(ics_content)
    response.headers['Content-Type'] = 'text/calendar; charset=utf-8'
    filename = f"shifts_{'all' if scope == 'all' else 'my'}.ics"
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    return response


@app.route('/export/oncall')
@login_required
def export_oncall():
    scope = _get_export_scope()
    
    query = OnCall.query.options(joinedload(OnCall.user)).order_by(OnCall.start_time)
    
    # Vérification des permissions : un utilisateur normal ne peut exporter que ses propres données
    if not current_user.is_admin and scope == 'all':
        flash('❌ Vous ne pouvez exporter que vos propres astreintes.', 'danger')
        return redirect(url_for('oncall'))
    
    filtered_query = _filter_by_scope(query, OnCall, scope, current_user)
    on_calls = filtered_query.all()
    
    ics_content = generate_ics_oncall(on_calls)
    response = make_response(ics_content)
    response.headers['Content-Type'] = 'text/calendar; charset=utf-8'
    filename = f"oncall_{'all' if scope == 'all' else 'my'}.ics"
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    return response


@app.route('/export/leaves')
@login_required
def export_leaves():
    scope = _get_export_scope()
    
    query = Leave.query.options(joinedload(Leave.user)).order_by(Leave.start_date)
    
    # Vérification des permissions : un utilisateur normal ne peut exporter que ses propres données
    if not current_user.is_admin and scope == 'all':
        flash('❌ Vous ne pouvez exporter que vos propres congés.', 'danger')
        return redirect(url_for('leave'))
    
    filtered_query = _filter_by_scope(query, Leave, scope, current_user)
    leaves = filtered_query.all()
    
    ics_content = generate_ics_leaves(leaves)
    response = make_response(ics_content)
    response.headers['Content-Type'] = 'text/calendar; charset=utf-8'
    filename = f"leaves_{'all' if scope == 'all' else 'my'}.ics"
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    return response
