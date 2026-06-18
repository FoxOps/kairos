from flask import render_template, request, redirect, url_for, flash
from sqlalchemy.orm import joinedload
from app import app, db
from app.models import Shift, OnCall, Leave, User, Group
from app.utils.helpers import (
    can_add_shift,
    can_add_leave,
    can_add_oncall,
)
from datetime import datetime, timedelta

SHIFT_TYPE_LABELS = {
    'morning': '07h-15h',
    'afternoon': '09h-17h',
    'evening': '13h-21h',
}

CALENDAR_WINDOW_DAYS = 180


def _calendar_window():
    """Fenêtre de ±6 mois autour d'aujourd'hui pour le calendrier."""
    now = datetime.now()
    return now - timedelta(days=CALENDAR_WINDOW_DAYS), now + timedelta(days=CALENDAR_WINDOW_DAYS)


def _build_calendar_events(shifts, on_calls, leaves):
    events = []

    for shift in shifts:
        label = SHIFT_TYPE_LABELS.get(shift.shift_type, shift.shift_type)
        events.append({
            'title': f'{shift.user.name} - {label}',
            'start': shift.start_time.isoformat(),
            'end': shift.end_time.isoformat(),
            'className': 'fc-event-shift',
            'url': url_for('schedule'),
        })

    for oncall in on_calls:
        events.append({
            'title': f'Astreinte - {oncall.user.name}',
            'start': oncall.start_time.isoformat(),
            'end': oncall.end_time.isoformat(),
            'className': 'fc-event-oncall',
            'url': url_for('oncall'),
        })

    for leave in leaves:
        events.append({
            'title': f'Congé - {leave.user.name}',
            'start': leave.start_date.isoformat(),
            'end': (leave.end_date + timedelta(days=1)).isoformat(),
            'className': 'fc-event-leave',
            'allDay': True,
            'url': url_for('leave'),
        })

    return events


@app.route('/')
def index():
    window_start, window_end = _calendar_window()
    window_start_date = window_start.date()

    shifts = Shift.query.options(joinedload(Shift.user)).filter(
        Shift.start_time >= window_start,
        Shift.start_time <= window_end,
    ).order_by(Shift.start_time).all()

    on_calls = OnCall.query.options(joinedload(OnCall.user)).filter(
        OnCall.start_time <= window_end,
        OnCall.end_time >= window_start,
    ).order_by(OnCall.start_time).all()

    leaves = Leave.query.options(joinedload(Leave.user)).filter(
        Leave.end_date >= window_start_date,
        Leave.start_date <= window_end.date(),
    ).order_by(Leave.start_date).all()

    events = _build_calendar_events(shifts, on_calls, leaves)
    return render_template('index.html', events=events)


# ========== ROUTES POUR LES CONGÉS ==========

@app.route('/leave')
def leave():
    leaves = Leave.query.options(joinedload(Leave.user)).order_by(Leave.start_date).all()
    return render_template('leave.html', leaves=leaves)


@app.route('/leave/add', methods=['GET', 'POST'])
def add_leave():
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        reason = request.form.get('reason', '').strip()

        if not all([user_id, start_date_str, end_date_str]):
            flash('❌ Tous les champs obligatoires doivent être remplis.', 'danger')
            return redirect(url_for('add_leave'))

        try:
            user_id = int(user_id)
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

            can_add, error_message = can_add_leave(user_id, start_date, end_date)
            if not can_add:
                flash(error_message, 'danger')
                return redirect(url_for('add_leave'))

            new_leave = Leave(
                user_id=user_id,
                start_date=start_date,
                end_date=end_date,
                reason=reason or None,
            )
            db.session.add(new_leave)
            db.session.commit()
            flash('✅ Congé ajouté avec succès !', 'success')
            return redirect(url_for('leave'))
        except ValueError:
            db.session.rollback()
            flash('❌ Format de date invalide. Utilise le format AAAA-MM-JJ.', 'danger')
            return redirect(url_for('add_leave'))
        except Exception as e:
            db.session.rollback()
            flash(f'❌ Erreur : {str(e)}', 'danger')

    users = User.query.order_by(User.name).all()
    return render_template('add_leave.html', users=users)


@app.route('/leave/delete/<int:leave_id>')
def delete_leave(leave_id):
    leave_record = Leave.query.get_or_404(leave_id)
    try:
        db.session.delete(leave_record)
        db.session.commit()
        flash('✅ Congé supprimé avec succès !', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Erreur : {str(e)}', 'danger')
    return redirect(url_for('leave'))


# ========== ROUTES POUR LES ASTREINTES ==========

@app.route('/oncall')
def oncall():
    on_calls = OnCall.query.options(joinedload(OnCall.user)).order_by(OnCall.start_time).all()
    return render_template('oncall.html', on_calls=on_calls)


@app.route('/oncall/add', methods=['GET', 'POST'])
def add_oncall():
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        start_date_str = request.form.get('start_date')

        if not all([user_id, start_date_str]):
            flash('❌ Tous les champs sont obligatoires.', 'danger')
            return redirect(url_for('add_oncall'))

        try:
            user_id = int(user_id)
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            if start_date.weekday() != 4:
                flash('❌ L\'astreinte doit commencer un vendredi.', 'danger')
                return redirect(url_for('add_oncall'))

            start_time = datetime.combine(start_date, datetime.min.time()).replace(hour=21)
            end_time = start_time + timedelta(days=7, hours=-14)

            can_add, error_message = can_add_oncall(user_id, start_time, end_time)
            if not can_add:
                flash(error_message, 'danger')
                return redirect(url_for('add_oncall'))

            new_oncall = OnCall(
                user_id=user_id,
                start_time=start_time,
                end_time=end_time,
            )
            db.session.add(new_oncall)
            db.session.commit()
            flash('✅ Astreinte ajoutée avec succès ! (Du vendredi 21h au vendredi suivant 07h)', 'success')
            return redirect(url_for('oncall'))
        except ValueError:
            db.session.rollback()
            flash('❌ Format de date invalide. Utilise le format AAAA-MM-JJ.', 'danger')
            return redirect(url_for('add_oncall'))
        except Exception as e:
            db.session.rollback()
            flash(f'❌ Erreur : {str(e)}', 'danger')

    users = User.query.join(Group).filter(Group.is_part_of_oncall == True).all()
    return render_template('add_oncall.html', users=users)


@app.route('/oncall/delete/<int:oncall_id>')
def delete_oncall(oncall_id):
    oncall = OnCall.query.get_or_404(oncall_id)
    try:
        db.session.delete(oncall)
        db.session.commit()
        flash('✅ Astreinte supprimée avec succès !', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Erreur : {str(e)}', 'danger')
    return redirect(url_for('oncall'))


# ========== ROUTES POUR LES SHIFTS ==========

@app.route('/schedule')
def schedule():
    shifts = Shift.query.options(joinedload(Shift.user)).order_by(Shift.start_time).all()
    return render_template('schedule.html', shifts=shifts)


@app.route('/schedule/add', methods=['GET', 'POST'])
def add_shift():
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        shift_type = request.form.get('shift_type')
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')

        if not all([user_id, shift_type, start_date_str, end_date_str]):
            flash('❌ Tous les champs sont obligatoires.', 'danger')
            return redirect(url_for('add_shift'))

        shift_hours = {
            'morning': {'start': 7, 'end': 15},
            'afternoon': {'start': 9, 'end': 17},
            'evening': {'start': 13, 'end': 21},
        }

        if shift_type not in shift_hours:
            flash('Type de shift invalide', 'danger')
            return redirect(url_for('add_shift'))

        try:
            user_id = int(user_id)
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

            if start_date > end_date:
                flash('La date de début doit être antérieure à la date de fin.', 'danger')
                return redirect(url_for('add_shift'))

            current_date = start_date
            shifts_added = []

            while current_date <= end_date:
                if current_date.weekday() >= 5:
                    current_date += timedelta(days=1)
                    continue

                can_add, error_message = can_add_shift(user_id, current_date, shift_type)
                if not can_add:
                    flash(f"{error_message} (le {current_date.strftime('%d/%m/%Y')})", 'danger')
                    return redirect(url_for('add_shift'))

                start_time = datetime.combine(current_date, datetime.min.time()).replace(
                    hour=shift_hours[shift_type]['start']
                )
                end_time = datetime.combine(current_date, datetime.min.time()).replace(
                    hour=shift_hours[shift_type]['end']
                )

                new_shift = Shift(
                    user_id=user_id,
                    shift_type=shift_type,
                    start_time=start_time,
                    end_time=end_time,
                    date=current_date,
                )
                db.session.add(new_shift)
                shifts_added.append(current_date.strftime('%d/%m/%Y'))
                current_date += timedelta(days=1)

            db.session.commit()
            if shifts_added:
                flash(f'✅ Shifts ajoutés avec succès pour les dates : {", ".join(shifts_added)} !', 'success')
            else:
                flash('❌ Aucun shift ajouté (période invalide ou jours non ouvrés).', 'danger')
            return redirect(url_for('schedule'))
        except ValueError as e:
            db.session.rollback()
            flash(f'❌ Format de date invalide : {str(e)}. Utilise le format AAAA-MM-JJ.', 'danger')
            return redirect(url_for('add_shift'))
        except Exception as e:
            db.session.rollback()
            flash(f'❌ Erreur : {str(e)}', 'danger')
            return redirect(url_for('add_shift'))

    users = User.query.join(Group).filter(Group.is_part_of_schedule == True).all()
    return render_template('add_shift.html', users=users)


@app.route('/schedule/delete/<int:shift_id>')
def delete_shift(shift_id):
    shift = Shift.query.get_or_404(shift_id)
    try:
        db.session.delete(shift)
        db.session.commit()
        flash('✅ Shift supprimé avec succès !', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Erreur : {str(e)}', 'danger')
    return redirect(url_for('schedule'))
