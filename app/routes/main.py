from flask import render_template, request, redirect, url_for, flash
from app import app, db
from app.models import Shift, OnCall, Leave, User, Group
from app.utils.helpers import (
    can_add_shift,
    can_add_leave,
    can_add_oncall,
    is_user_on_leave,
    is_user_on_shift
)
from datetime import datetime, timedelta

@app.route('/')
def index():
    # Récupérer tous les événements pour le calendrier
    shifts = Shift.query.order_by(Shift.start_time).all()
    on_calls = OnCall.query.order_by(OnCall.start_time).all()
    leaves = Leave.query.order_by(Leave.start_date).all()

    # Sérialiser les objets pour JSON
    serialized_shifts = []
    for shift in shifts:
        serialized_shifts.append({
            'id': shift.id,
            'user_id': shift.user_id,
            'user_name': shift.user.name,
            'shift_type': shift.shift_type,
            'start_time': shift.start_time.isoformat() if shift.start_time else None,
            'end_time': shift.end_time.isoformat() if shift.end_time else None,
            'date': shift.date.isoformat() if shift.date else None
        })

    serialized_on_calls = []
    for oncall in on_calls:
        serialized_on_calls.append({
            'id': oncall.id,
            'user_id': oncall.user_id,
            'user_name': oncall.user.name,
            'start_time': oncall.start_time.isoformat() if oncall.start_time else None,
            'end_time': oncall.end_time.isoformat() if oncall.end_time else None
        })

    serialized_leaves = []
    for leave in leaves:
        serialized_leaves.append({
            'id': leave.id,
            'user_id': leave.user_id,
            'user_name': leave.user.name,
            'start_date': leave.start_date.isoformat() if leave.start_date else None,
            'end_date': leave.end_date.isoformat() if leave.end_date else None,
            'reason': leave.reason
        })

    return render_template('index.html',
                          shifts=serialized_shifts,
                          on_calls=serialized_on_calls,
                          leaves=serialized_leaves)


# ========== ROUTES POUR LES ASTREINTES ==========

# Lister les astreintes
@app.route('/oncall')
def oncall():
    on_calls = OnCall.query.order_by(OnCall.start_time).all()
    return render_template('oncall.html', on_calls=on_calls)

# Ajouter une astreinte (uniquement les utilisateurs dont le groupe fait partie de l'astreinte)
@app.route('/oncall/add', methods=['GET', 'POST'])
def add_oncall():
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        start_date_str = request.form.get('start_date')

        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            # L'astreinte commence le vendredi à 21h
            if start_date.weekday() != 4:  # 4 = vendredi
                flash('❌ L\'astreinte doit commencer un vendredi.', 'error')
                return redirect(url_for('add_oncall'))

            # Créer le datetime de début : vendredi à 21h
            start_time = datetime.combine(start_date, datetime.min.time()).replace(hour=21)
            # L'astreinte se termine le vendredi suivant à 07h (7 jours plus tard)
            end_time = start_time + timedelta(days=7, hours=-14)  # 7 jours - 14h (21h → 07h)

            # Vérifier si l'astreinte peut être ajoutée
            can_add, error_message = can_add_oncall(user_id, start_time)
            if not can_add:
                flash(error_message, 'error')
                return redirect(url_for('add_oncall'))

            # Ajouter l'astreinte (7 jours consécutifs)
            new_oncall = OnCall(
                user_id=user_id,
                start_time=start_time,
                end_time=end_time
            )
            db.session.add(new_oncall)
            db.session.commit()
            flash('✅ Astreinte ajoutée avec succès ! (Du vendredi 21h au vendredi suivant 07h)', 'success')
            return redirect(url_for('oncall'))
        except Exception as e:
            db.session.rollback()
            flash(f'❌ Erreur : {str(e)}', 'error')

    # Filtrer les utilisateurs : uniquement ceux dont le groupe fait partie de l'astreinte
    users = User.query.join(Group).filter(Group.is_part_of_oncall == True).all()
    return render_template('add_oncall.html', users=users)

# Supprimer une astreinte
@app.route('/oncall/delete/<int:oncall_id>')
def delete_oncall(oncall_id):
    oncall = OnCall.query.get_or_404(oncall_id)
    try:
        db.session.delete(oncall)
        db.session.commit()
        flash('✅ Astreinte supprimée avec succès !', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Erreur : {str(e)}', 'error')
    return redirect(url_for('oncall'))

# ========== ROUTES POUR LES SHIFTS ==========

# Lister les shifts
@app.route('/schedule')
def schedule():
    shifts = Shift.query.order_by(Shift.start_time).all()
    return render_template('schedule.html', shifts=shifts)

# Ajouter un shift pour chaque jour de la période (uniquement les utilisateurs dont le groupe fait partie de schedule)
@app.route('/schedule/add', methods=['GET', 'POST'])
def add_shift():
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        shift_type = request.form.get('shift_type')
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')

        if not all([user_id, shift_type, start_date_str, end_date_str]):
            flash('❌ Tous les champs sont obligatoires.', 'error')
            return redirect(url_for('add_shift'))

        shift_hours = {
            'morning': {'start': 7, 'end': 15},
            'afternoon': {'start': 9, 'end': 17},
            'evening': {'start': 13, 'end': 21}
        }

        if shift_type not in shift_hours:
            flash('Type de shift invalide', 'error')
            return redirect(url_for('add_shift'))

        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

            if start_date > end_date:
                flash('La date de début doit être antérieure à la date de fin.', 'error')
                return redirect(url_for('add_shift'))

            # Ajouter un shift pour chaque jour de la période (du lundi au vendredi)
            current_date = start_date
            shifts_added = []

            while current_date <= end_date:
                # Ignorer les samedi (5) et dimanche (6)
                if current_date.weekday() >= 5:
                    current_date += timedelta(days=1)
                    continue

                # Vérifier si le shift peut être ajouté pour ce jour
                can_add, error_message = can_add_shift(user_id, current_date, shift_type)
                if not can_add:
                    flash(f"{error_message} (le {current_date.strftime('%d/%m/%Y')})", 'error')
                    return redirect(url_for('add_shift'))

                start_time = datetime.combine(current_date, datetime.min.time()).replace(hour=shift_hours[shift_type]['start'])
                end_time = datetime.combine(current_date, datetime.min.time()).replace(hour=shift_hours[shift_type]['end'])

                new_shift = Shift(
                    user_id=user_id,
                    shift_type=shift_type,
                    start_time=start_time,
                    end_time=end_time,
                    date=current_date
                )
                db.session.add(new_shift)
                shifts_added.append(current_date.strftime('%d/%m/%Y'))

                current_date += timedelta(days=1)

            db.session.commit()
            if shifts_added:
                flash(f'✅ Shifts ajoutés avec succès pour les dates : {", ".join(shifts_added)} !', 'success')
            else:
                flash('❌ Aucun shift ajouté (période invalide ou jours non ouvrés).', 'error')
            return redirect(url_for('schedule'))
        except ValueError as e:
            db.session.rollback()
            flash(f'❌ Format de date invalide : {str(e)}. Utilise le format AAAA-MM-JJ.', 'error')
            return redirect(url_for('add_shift'))
        except Exception as e:
            db.session.rollback()
            flash(f'❌ Erreur : {str(e)}', 'error')
            return redirect(url_for('add_shift'))

    # Filtrer les utilisateurs : uniquement ceux dont le groupe fait partie de schedule
    users = User.query.join(Group).filter(Group.is_part_of_schedule == True).all()
    return render_template('add_shift.html', users=users)

# Supprimer un shift
@app.route('/schedule/delete/<int:shift_id>')
def delete_shift(shift_id):
    shift = Shift.query.get_or_404(shift_id)
    try:
        db.session.delete(shift)
        db.session.commit()
        flash('✅ Shift supprimé avec succès !', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Erreur : {str(e)}', 'error')
    return redirect(url_for('schedule'))