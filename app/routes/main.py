from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload
from app import app, db
from app.models import Shift, OnCall, Leave, User, Group, ShiftType
from app.utils.helpers import (
    can_add_shift,
    can_add_leave,
    can_add_oncall,
)
from app.utils.decorators import admin_required, user_owns_resource
from app.utils.advanced_shift_automation import AdvancedShiftAutomation
from datetime import datetime, timedelta

CALENDAR_WINDOW_DAYS = 180


def _calendar_window():
    """Fenêtre de ±6 mois autour d'aujourd'hui pour le calendrier."""
    now = datetime.now()
    return now - timedelta(days=CALENDAR_WINDOW_DAYS), now + timedelta(
        days=CALENDAR_WINDOW_DAYS
    )


def _build_calendar_events(shifts, on_calls, leaves):
    events = []

    for shift in shifts:
        label = shift.shift_type.label if shift.shift_type else shift.shift_type
        events.append(
            {
                "title": f"{shift.user.name} - {label}",
                "start": shift.start_time.isoformat(),
                "end": shift.end_time.isoformat(),
                "className": "fc-event-shift",
                "url": url_for("schedule"),
            }
        )

    for oncall in on_calls:
        events.append(
            {
                "title": f"Astreinte - {oncall.user.name}",
                "start": oncall.start_time.isoformat(),
                "end": oncall.end_time.isoformat(),
                "className": "fc-event-oncall",
                "url": url_for("oncall"),
            }
        )

    for leave in leaves:
        events.append(
            {
                "title": f"Conge - {leave.user.name}",
                "start": leave.start_date.isoformat(),
                "end": (leave.end_date + timedelta(days=1)).isoformat(),
                "className": "fc-event-leave",
                "allDay": True,
                "url": url_for("leave"),
            }
        )

    return events


@app.route("/")
@login_required
def index():
    """Page d'accueil - accessible uniquement aux utilisateurs connectés."""
    window_start, window_end = _calendar_window()
    window_start_date = window_start.date()
    window_end_date = window_end.date()

    # Optimisation : Utiliser des requêtes avec joinedload pour éviter le N+1
    # et sélectionner uniquement les colonnes nécessaires
    shifts = (
        Shift.query.options(joinedload(Shift.user))
        .filter(
            Shift.start_time >= window_start,
            Shift.start_time <= window_end,
        )
        .order_by(Shift.start_time)
        .all()
    )

    on_calls = (
        OnCall.query.options(joinedload(OnCall.user))
        .filter(
            OnCall.start_time <= window_end,
            OnCall.end_time >= window_start,
        )
        .order_by(OnCall.start_time)
        .all()
    )

    leaves = (
        Leave.query.options(joinedload(Leave.user))
        .filter(
            Leave.end_date >= window_start_date,
            Leave.start_date <= window_end_date,
        )
        .order_by(Leave.start_date)
        .all()
    )

    events = _build_calendar_events(shifts, on_calls, leaves)
    return render_template("index.html", events=events)


# ========== ROUTES POUR LES CONGÉS ==========


@app.route("/leave")
@login_required
def leave():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # Options de pagination
    per_page_options = [5, 10, 25, 50, 100]
    
    # Si "Tout" est sélectionné, utiliser un grand nombre
    if per_page == 0 or per_page == -1:
        per_page = 999999  # Tous les éléments
    
    # S'assurer que per_page est dans les options valides
    if per_page not in per_page_options and per_page != 999999:
        per_page = 20
    
    # Optimisation : Utiliser joinedload pour éviter le N+1 sur user
    # et sélectionner uniquement les colonnes nécessaires
    leaves_paginated = (
        Leave.query.options(joinedload(Leave.user))
        .order_by(Leave.start_date)
        .paginate(page=page, per_page=per_page, error_out=False)
    )
    
    return render_template("leave.html", leaves=leaves_paginated, per_page=per_page, per_page_options=per_page_options)


@app.route("/leave/add", methods=["GET", "POST"])
@login_required
def add_leave():
    if request.method == "POST":
        user_id = request.form.get("user_id")
        start_date_str = request.form.get("start_date")
        end_date_str = request.form.get("end_date")

        if not all([user_id, start_date_str, end_date_str]):
            flash("Tous les champs obligatoires doivent être remplis.", "danger")
            return redirect(url_for("add_leave"))

        try:
            user_id = int(user_id)

            # Vérification des permissions : un utilisateur normal ne peut ajouter que ses propres congés
            if not current_user.is_admin and current_user.id != user_id:
                flash(
                    "❌ Vous ne pouvez ajouter des congés que pour vous-même.", "danger"
                )
                return redirect(url_for("leave"))

            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()

            can_add, error_message = can_add_leave(user_id, start_date, end_date)
            if not can_add:
                flash(error_message, "danger")
                return redirect(url_for("add_leave"))

            new_leave = Leave(
                user_id=user_id,
                start_date=start_date,
                end_date=end_date,
            )
            db.session.add(new_leave)
            db.session.commit()
            
            # Rééquilibrer automatiquement les shifts après l'ajout d'un congé
            try:
                _, rebalance_messages = AdvancedShiftAutomation.rebalance_after_leave(new_leave, dry_run=False)
                for msg in rebalance_messages:
                    flash(msg, "info")
            except Exception as e:
                flash(f"⚠️ Rééquilibrage automatique des shifts échoué : {str(e)}", "warning")
            
            flash("Conge ajoute avec succes !", "success")
            return redirect(url_for("leave"))
        except ValueError:
            db.session.rollback()
            flash("Format de date invalide. Utilisez le format AAAA-MM-JJ.", "danger")
            return redirect(url_for("add_leave"))
        except Exception as e:
            db.session.rollback()
            flash(f"Erreur : {str(e)}", "danger")

    # Un utilisateur normal ne voit que lui-même dans la liste
    if current_user.is_admin:
        users = User.query.order_by(User.name).all()
    else:
        users = [current_user]
    return render_template("add_leave.html", users=users)


@app.route("/leave/delete/<int:leave_id>")
@login_required
@user_owns_resource(Leave, "leave_id")
def delete_leave(leave_id):
    leave_record = db.session.get(Leave, leave_id) or abort(404)

    try:
        db.session.delete(leave_record)
        db.session.commit()
        
        # Rééquilibrer automatiquement les shifts après la suppression d'un congé
        try:
            _, rebalance_messages = AdvancedShiftAutomation.rebalance_after_leave(leave_record, dry_run=False)
            for msg in rebalance_messages:
                flash(msg, "info")
        except Exception as e:
            flash(f"⚠️ Rééquilibrage automatique des shifts échoué : {str(e)}", "warning")
        
        flash("Conge supprime avec succes !", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Erreur : {str(e)}", "danger")
    return redirect(url_for("leave"))


# ========== ROUTES POUR LES ASTREINTES ==========


@app.route("/oncall")
@login_required
def oncall():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # Options de pagination
    per_page_options = [5, 10, 25, 50, 100]
    
    # Si "Tout" est sélectionné, utiliser un grand nombre
    if per_page == 0 or per_page == -1:
        per_page = 999999  # Tous les éléments
    
    # S'assurer que per_page est dans les options valides
    if per_page not in per_page_options and per_page != 999999:
        per_page = 20
    
    # Optimisation : Utiliser joinedload pour éviter le N+1 sur user
    on_calls_paginated = (
        OnCall.query.options(joinedload(OnCall.user))
        .order_by(OnCall.start_time)
        .paginate(page=page, per_page=per_page, error_out=False)
    )
    
    return render_template("oncall.html", on_calls=on_calls_paginated, per_page=per_page, per_page_options=per_page_options)


@app.route("/oncall/add", methods=["GET", "POST"])
@login_required
@admin_required
def add_oncall():
    if request.method == "POST":
        user_id = request.form.get("user_id")
        start_date_str = request.form.get("start_date")

        if not all([user_id, start_date_str]):
            flash("Tous les champs sont obligatoires.", "danger")
            return redirect(url_for("add_oncall"))

        try:
            user_id = int(user_id)

            start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
            if start_date.weekday() != 4:
                flash("L'astreinte doit commencer un vendredi.", "danger")
                return redirect(url_for("add_oncall"))

            start_time = datetime.combine(start_date, datetime.min.time()).replace(
                hour=21
            )
            end_time = start_time + timedelta(days=7, hours=-14)

            can_add, error_message = can_add_oncall(user_id, start_time, end_time)
            if not can_add:
                flash(error_message, "danger")
                return redirect(url_for("add_oncall"))

            new_oncall = OnCall(
                user_id=user_id,
                start_time=start_time,
                end_time=end_time,
            )
            db.session.add(new_oncall)
            db.session.commit()
            flash(
                "Astreinte ajoutee avec succes ! (Du vendredi 21h au vendredi suivant 07h)",
                "success",
            )
            return redirect(url_for("oncall"))
        except ValueError:
            db.session.rollback()
            flash("Format de date invalide. Utilisez le format AAAA-MM-JJ.", "danger")
            return redirect(url_for("add_oncall"))
        except Exception as e:
            db.session.rollback()
            flash(f"Erreur : {str(e)}", "danger")

    # Seuls les administrateurs peuvent voir cette page
    users = User.query.join(Group).filter(Group.is_part_of_oncall == True).all()
    return render_template("add_oncall.html", users=users)


@app.route("/oncall/delete/<int:oncall_id>")
@login_required
@admin_required
def delete_oncall(oncall_id):
    oncall = db.session.get(OnCall, oncall_id) or abort(404)

    try:
        db.session.delete(oncall)
        db.session.commit()
        flash("Astreinte supprimee avec succes !", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Erreur : {str(e)}", "danger")
    return redirect(url_for("oncall"))


@app.route("/oncall/delete-all", methods=["POST"])
@login_required
@admin_required
def delete_all_oncalls():
    """Supprime toutes les astreintes."""
    try:
        # Optimisation : Utiliser count() puis delete() sans charger tous les objets
        count = OnCall.query.count()
        if count > 0:
            OnCall.query.delete(synchronize_session=False)
            db.session.commit()
            flash(f"✅ Toutes les {count} astreintes ont été supprimées avec succès !", "success")
        else:
            flash("⚠️ Aucune astreinte à supprimer.", "warning")
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Erreur : {str(e)}", "danger")
    return redirect(url_for("oncall"))


@app.route("/oncall/delete-all-for-user/<int:user_id>", methods=["POST"])
@login_required
@admin_required
def delete_all_oncalls_for_user(user_id):
    """Supprime toutes les astreintes d'un utilisateur spécifique."""
    user = db.session.get(User, user_id) or abort(404)
    
    try:
        # Optimisation : Utiliser count() puis delete() sans charger tous les objets
        count = OnCall.query.filter_by(user_id=user_id).count()
        
        if count == 0:
            flash(f"⚠️ Aucun astreinte trouvée pour {user.name}.", "warning")
            return redirect(url_for("oncall"))
        
        # Supprimer directement sans charger tous les objets
        OnCall.query.filter_by(user_id=user_id).delete(synchronize_session=False)
        db.session.commit()
        flash(f"✅ Toutes les {count} astreintes de {user.name} ont été supprimées avec succès !", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Erreur : {str(e)}", "danger")
    return redirect(url_for("oncall"))


# ========== ROUTES POUR LES SHIFTS ====================

@app.route("/shift/delete-all", methods=["POST"])
@login_required
@admin_required
def delete_all_shifts():
    """Supprime tous les shifts."""
    try:
        # Optimisation : Utiliser count() puis delete() sans charger tous les objets
        count = Shift.query.count()
        if count > 0:
            Shift.query.delete(synchronize_session=False)
            db.session.commit()
            flash(f"✅ Tous les {count} shifts ont été supprimés avec succès !", "success")
        else:
            flash("⚠️ Aucun shift à supprimer.", "warning")
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Erreur : {str(e)}", "danger")
    return redirect(url_for("schedule"))


@app.route("/shift/delete-all-for-user/<int:user_id>", methods=["POST"])
@login_required
@admin_required
def delete_all_shifts_for_user(user_id):
    """Supprime tous les shifts d'un utilisateur spécifique."""
    user = db.session.get(User, user_id) or abort(404)
    
    try:
        # Optimisation : Utiliser count() puis delete() sans charger tous les objets
        count = Shift.query.filter_by(user_id=user_id).count()
        
        if count == 0:
            flash(f"⚠️ Aucun shift trouvé pour {user.name}.", "warning")
            return redirect(url_for("schedule"))
        
        # Supprimer directement sans charger tous les objets
        Shift.query.filter_by(user_id=user_id).delete(synchronize_session=False)
        db.session.commit()
        flash(f"✅ Tous les {count} shifts de {user.name} ont été supprimés avec succès !", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Erreur : {str(e)}", "danger")
    return redirect(url_for("schedule"))

@app.route("/shift/delete-day/<date_str>", methods=["POST"])
@login_required
@admin_required
def delete_all_shifts_for_day(date_str):
    """Supprime tous les shifts pour une journée spécifique."""
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        # Optimisation : Utiliser count() puis delete() sans charger tous les objets
        count = Shift.query.filter_by(date=date_obj).count()
        
        if count == 0:
            flash(f"⚠️ Aucun shift trouvé pour le {date_obj.strftime('%d/%m/%Y')}.", "warning")
            return redirect(url_for("schedule"))
        
        # Supprimer directement sans charger tous les objets
        Shift.query.filter_by(date=date_obj).delete(synchronize_session=False)
        db.session.commit()
        flash(f"✅ Tous les {count} shifts du {date_obj.strftime('%d/%m/%Y')} ont été supprimés avec succès !", "success")
    except ValueError:
        flash(f"❌ Format de date invalide.", "danger")
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Erreur : {str(e)}", "danger")
    return redirect(url_for("schedule"))


@app.route("/shift/delete-week/<date_str>", methods=["POST"])
@login_required
@admin_required
def delete_all_shifts_for_week(date_str):
    """Supprime tous les shifts pour une semaine complète (lundi-vendredi)."""
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        
        # Trouver le lundi de la semaine
        monday = date_obj - timedelta(days=date_obj.weekday())
        
        # Optimisation : Supprimer tous les shifts du lundi au vendredi en une seule requête
        # au lieu de faire une boucle avec des requêtes individuelles
        dates_to_delete = [monday + timedelta(days=day) for day in range(5)]  # lundi (0) à vendredi (4)
        
        # Compter d'abord pour le message
        deleted_count = Shift.query.filter(Shift.date.in_(dates_to_delete)).count()
        
        if deleted_count == 0:
            flash(f"⚠️ Aucun shift trouvé pour la semaine du {monday.strftime('%d/%m/%Y')}.", "warning")
        else:
            # Supprimer en une seule requête
            Shift.query.filter(Shift.date.in_(dates_to_delete)).delete(synchronize_session=False)
            db.session.commit()
            flash(f"✅ Tous les {deleted_count} shifts de la semaine du {monday.strftime('%d/%m/%Y')} ont été supprimés avec succès !", "success")
    except ValueError:
        flash(f"❌ Format de date invalide.", "danger")
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Erreur : {str(e)}", "danger")
    return redirect(url_for("schedule"))






@app.route("/schedule")
@login_required
def schedule():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # Options de pagination
    per_page_options = [5, 10, 25, 50, 100]
    
    # Si "Tout" est sélectionné, utiliser un grand nombre
    if per_page == 0 or per_page == -1:
        per_page = 999999  # Tous les éléments
    
    # S'assurer que per_page est dans les options valides
    if per_page not in per_page_options and per_page != 999999:
        per_page = 20
    
    # Optimisation : Utiliser joinedload pour éviter le N+1 sur user et shift_type
    shifts_paginated = (
        Shift.query.options(
            joinedload(Shift.user),
            joinedload(Shift.shift_type)
        )
        .order_by(Shift.start_time)
        .paginate(page=page, per_page=per_page, error_out=False)
    )
    
    return render_template("schedule.html", shifts=shifts_paginated, per_page=per_page, per_page_options=per_page_options)


@app.route("/schedule/add", methods=["GET", "POST"])
@login_required
@admin_required
def add_shift():
    if request.method == "POST":
        user_id = request.form.get("user_id")
        shift_type_id = request.form.get("shift_type_id")
        start_date_str = request.form.get("start_date")
        end_date_str = request.form.get("end_date")

        if not all([user_id, shift_type_id, start_date_str, end_date_str]):
            flash("Tous les champs sont obligatoires.", "danger")
            return redirect(url_for("add_shift"))

        try:
            shift_type = db.session.get(ShiftType, int(shift_type_id))
            if not shift_type:
                flash("Type de shift invalide.", "danger")
                return redirect(url_for("add_shift"))

            user_id = int(user_id)

            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()

            if start_date > end_date:
                flash(
                    "La date de debut doit etre anterieure a la date de fin.", "danger"
                )
                return redirect(url_for("add_shift"))

            current_date = start_date
            shifts_added = []

            while current_date <= end_date:
                if current_date.weekday() >= 5:
                    current_date += timedelta(days=1)
                    continue

                can_add, error_message = can_add_shift(
                    user_id, current_date, shift_type.name
                )
                if not can_add:
                    flash(
                        f"{error_message} (le {current_date.strftime('%d/%m/%Y')})",
                        "danger",
                    )
                    return redirect(url_for("add_shift"))

                start_time = datetime.combine(
                    current_date, datetime.min.time()
                ).replace(hour=shift_type.start_hour)
                end_time = datetime.combine(current_date, datetime.min.time()).replace(
                    hour=shift_type.end_hour
                )

                new_shift = Shift(
                    user_id=user_id,
                    shift_type_id=shift_type.id,
                    start_time=start_time,
                    end_time=end_time,
                    date=current_date,
                )
                db.session.add(new_shift)
                shifts_added.append(current_date.strftime("%d/%m/%Y"))
                current_date += timedelta(days=1)

            db.session.commit()
            if shifts_added:
                flash(
                    f"Shifts ajoutes avec succes pour les dates : {', '.join(shifts_added)} !",
                    "success",
                )
            else:
                flash(
                    "Aucun shift ajoute (periode invalide ou jours non ouvres).",
                    "danger",
                )
            return redirect(url_for("schedule"))
        except ValueError as e:
            db.session.rollback()
            flash(
                f"Format de date invalide : {str(e)}. Utilisez le format AAAA-MM-JJ.",
                "danger",
            )
            return redirect(url_for("add_shift"))
        except Exception as e:
            db.session.rollback()
            flash(f"Erreur : {str(e)}", "danger")
            return redirect(url_for("add_shift"))

    # Seuls les administrateurs peuvent voir cette page
    users = User.query.join(Group).filter(Group.is_part_of_schedule == True).all()
    shift_types = ShiftType.query.order_by(ShiftType.name).all()
    return render_template("add_shift.html", users=users, shift_types=shift_types)


@app.route("/schedule/delete/<int:shift_id>")
@login_required
@admin_required
def delete_shift(shift_id):
    shift = db.session.get(Shift, shift_id) or abort(404)

    try:
        db.session.delete(shift)
        db.session.commit()
        flash("Shift supprime avec succes !", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Erreur : {str(e)}", "danger")
    return redirect(url_for("schedule"))
