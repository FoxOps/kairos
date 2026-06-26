from flask import render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy import func
from app import app, db
from app.models import User, Shift, OnCall, Leave, Group, ShiftType
from app.utils.optimizations import cached_route, paginated_route, eager_load, optimize_query, cache_result
from app.utils.decorators import admin_required
from app.utils.automation import (
    OnCallAutomation,
    ShiftAutomation,
    BusinessRules,
    generate_full_schedule,
    get_automation_status,
)
from app.utils.advanced_shift_automation import AdvancedShiftAutomation
from datetime import datetime, date, timedelta



# Dashboard admin
@app.route("/admin")
@admin_required
def admin_dashboard():
    # Optimisation : Utiliser des requêtes count() simples mais efficaces
    # Les requêtes count() sont déjà optimisées par SQLAlchemy
    # On peut les exécuter en parallèle avec des sous-requêtes
    from sqlalchemy import func
    
    # Exécuter toutes les requêtes count en une seule transaction
    users_count = db.session.query(func.count(User.id)).scalar()
    shifts_count = db.session.query(func.count(Shift.id)).scalar()
    on_calls_count = db.session.query(func.count(OnCall.id)).scalar()
    leaves_count = db.session.query(func.count(Leave.id)).scalar()
    groups_count = db.session.query(func.count(Group.id)).scalar()
    
    return render_template(
        "admin/dashboard.html",
        users_count=users_count,
        shifts_count=shifts_count,
        on_calls_count=on_calls_count,
        leaves_count=leaves_count,
        groups_count=groups_count,
    )


# ==================== GESTION DES GROUPES ====================


@app.route("/admin/groups")
@admin_required
@eager_load(Group, ['users'])
def list_groups():
    groups = Group.query.order_by(Group.name).all()
    return render_template("admin/groups.html", groups=groups)


@app.route("/admin/groups/add", methods=["GET", "POST"])
@admin_required
def add_group():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        is_part_of_schedule = "is_part_of_schedule" in request.form
        is_part_of_oncall = "is_part_of_oncall" in request.form

        if not name:
            flash("❌ Le nom du groupe est obligatoire.", "danger")
            return redirect(url_for("add_group"))

        if Group.query.filter_by(name=name).first():
            flash("❌ Un groupe avec ce nom existe déjà.", "danger")
            return redirect(url_for("add_group"))

        try:
            new_group = Group(
                name=name,
                is_part_of_schedule=is_part_of_schedule,
                is_part_of_oncall=is_part_of_oncall,
            )
            db.session.add(new_group)
            db.session.commit()
            flash("✅ Groupe ajouté avec succès !", "success")
            return redirect(url_for("list_groups"))
        except Exception as e:
            db.session.rollback()
            flash(f"❌ Erreur : {str(e)}", "danger")

    return render_template("admin/add_group.html")


@app.route("/admin/groups/edit/<int:group_id>", methods=["GET", "POST"])
@admin_required
def edit_group(group_id):
    group = db.session.get(Group, group_id) or abort(404)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        is_part_of_schedule = "is_part_of_schedule" in request.form
        is_part_of_oncall = "is_part_of_oncall" in request.form

        if not name:
            flash("❌ Le nom du groupe est obligatoire.", "danger")
            return redirect(url_for("edit_group", group_id=group_id))

        existing_group = Group.query.filter(
            Group.name == name, Group.id != group_id
        ).first()
        if existing_group:
            flash("❌ Un groupe avec ce nom existe déjà.", "danger")
            return redirect(url_for("edit_group", group_id=group_id))

        try:
            group.name = name
            group.is_part_of_schedule = is_part_of_schedule
            group.is_part_of_oncall = is_part_of_oncall
            db.session.commit()
            flash("✅ Groupe modifié avec succès !", "success")
            return redirect(url_for("list_groups"))
        except Exception as e:
            db.session.rollback()
            flash(f"❌ Erreur : {str(e)}", "danger")

    return render_template("admin/edit_group.html", group=group)


@app.route("/admin/groups/delete/<int:group_id>", methods=["POST"])
@admin_required
def delete_group(group_id):
    group = db.session.get(Group, group_id) or abort(404)

    if User.query.filter_by(group_id=group_id).first():
        flash(
            "❌ Impossible de supprimer ce groupe : des utilisateurs y sont associés.",
            "danger",
        )
        return redirect(url_for("list_groups"))

    try:
        db.session.delete(group)
        db.session.commit()
        flash("✅ Groupe supprimé avec succès !", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Erreur : {str(e)}", "danger")

    return redirect(url_for("list_groups"))


# ==================== GESTION DES UTILISATEURS ====================


@app.route("/admin/users")
@admin_required
@eager_load(User, ['group', 'shifts', 'on_calls', 'leaves'])
def list_users():
    users = (
        User.query.options(
            selectinload(User.group),
            selectinload(User.shifts),
            selectinload(User.on_calls),
            selectinload(User.leaves),
        )
        .order_by(User.name)
        .all()
    )
    groups = Group.query.all()
    return render_template("admin/users.html", users=users, groups=groups)


@app.route("/admin/users/add", methods=["GET", "POST"])
@admin_required
def add_user():
    groups = Group.query.all()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        group_id = request.form.get("group_id")
        password = request.form.get("password", "")

        if not all([name, email, group_id]):
            flash("❌ Tous les champs sont obligatoires.", "danger")
            return render_template("admin/add_user.html", groups=groups)

        if User.query.filter_by(email=email).first():
            flash("❌ Un utilisateur avec cet email existe déjà.", "danger")
            return render_template("admin/add_user.html", groups=groups)

        try:
            new_user = User(name=name, email=email, group_id=int(group_id))
            if password:
                new_user.set_password(password)
            else:
                # Générer un mot de passe par défaut
                new_user.set_password("password123")
            db.session.add(new_user)
            db.session.commit()
            flash("✅ Utilisateur ajouté avec succès !", "success")
            return redirect(url_for("list_users"))
        except Exception as e:
            db.session.rollback()
            flash(f"❌ Erreur : {str(e)}", "danger")

    return render_template("admin/add_user.html", groups=groups)


@app.route("/admin/users/edit/<int:user_id>", methods=["GET", "POST"])
@admin_required
def edit_user(user_id):
    user = db.session.get(User, user_id) or abort(404)
    groups = Group.query.all()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        group_id = request.form.get("group_id")
        is_admin = "is_admin" in request.form
        password = request.form.get("password", "")

        if not all([name, email, group_id]):
            flash("❌ Tous les champs sont obligatoires.", "danger")
            return render_template("admin/edit_user.html", user=user, groups=groups)

        existing_user = User.query.filter(
            User.email == email, User.id != user_id
        ).first()
        if existing_user:
            flash("❌ Un utilisateur avec cet email existe déjà.", "danger")
            return render_template("admin/edit_user.html", user=user, groups=groups)

        try:
            user.name = name
            user.email = email
            user.group_id = int(group_id)
            user.is_admin = is_admin
            if password:
                user.set_password(password)
            db.session.commit()
            flash("✅ Utilisateur modifié avec succès !", "success")
            return redirect(url_for("list_users"))
        except Exception as e:
            db.session.rollback()
            flash(f"❌ Erreur : {str(e)}", "danger")

    return render_template("admin/edit_user.html", user=user, groups=groups)


@app.route("/admin/users/delete/<int:user_id>", methods=["POST"])
@admin_required
def delete_user(user_id):
    user = db.session.get(User, user_id) or abort(404)

    if (
        Shift.query.filter_by(user_id=user_id).first()
        or OnCall.query.filter_by(user_id=user_id).first()
        or Leave.query.filter_by(user_id=user_id).first()
    ):
        flash(
            "❌ Impossible de supprimer cet utilisateur : il a des shifts, astreintes ou congés associés.",
            "danger",
        )
        return redirect(url_for("list_users"))

    try:
        db.session.delete(user)
        db.session.commit()
        flash("✅ Utilisateur supprimé avec succès !", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Erreur : {str(e)}", "danger")

    return redirect(url_for("list_users"))


# ==================== GESTION DES TYPES DE SHIFTS ====================


@app.route("/admin/shift-types")
@admin_required
@eager_load(ShiftType, ['shifts'])
def list_shift_types():
    shift_types = ShiftType.query.order_by(ShiftType.name).all()
    return render_template("admin/shift_types.html", shift_types=shift_types)


@app.route("/admin/shift-types/add", methods=["GET", "POST"])
@admin_required
def add_shift_type():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        label = request.form.get("label", "").strip()
        start_hour = request.form.get("start_hour")
        end_hour = request.form.get("end_hour")

        if not all([name, label, start_hour, end_hour]):
            flash("❌ Tous les champs sont obligatoires.", "danger")
            return redirect(url_for("add_shift_type"))

        if ShiftType.query.filter_by(name=name).first():
            flash("❌ Un type de shift avec ce nom existe déjà.", "danger")
            return redirect(url_for("add_shift_type"))

        try:
            start_hour = int(start_hour)
            end_hour = int(end_hour)
            if not (0 <= start_hour < 24) or not (0 <= end_hour < 24):
                flash("❌ Les heures doivent être comprises entre 0 et 23.", "danger")
                return redirect(url_for("add_shift_type"))
            if start_hour >= end_hour:
                flash(
                    "❌ L'heure de début doit être antérieure à l'heure de fin.",
                    "danger",
                )
                return redirect(url_for("add_shift_type"))

            new_shift_type = ShiftType(
                name=name,
                label=label,
                start_hour=start_hour,
                end_hour=end_hour,
            )
            db.session.add(new_shift_type)
            db.session.commit()
            flash("✅ Type de shift ajouté avec succès !", "success")
            return redirect(url_for("list_shift_types"))
        except ValueError:
            db.session.rollback()
            flash("❌ Les heures doivent être des nombres entiers.", "danger")
            return redirect(url_for("add_shift_type"))
        except Exception as e:
            db.session.rollback()
            flash(f"❌ Erreur : {str(e)}", "danger")

    return render_template("admin/add_shift_type.html")


@app.route("/admin/shift-types/edit/<int:shift_type_id>", methods=["GET", "POST"])
@admin_required
def edit_shift_type(shift_type_id):
    shift_type = db.session.get(ShiftType, shift_type_id) or abort(404)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        label = request.form.get("label", "").strip()
        start_hour = request.form.get("start_hour")
        end_hour = request.form.get("end_hour")

        if not all([name, label, start_hour, end_hour]):
            flash("❌ Tous les champs sont obligatoires.", "danger")
            return redirect(url_for("edit_shift_type", shift_type_id=shift_type_id))

        existing_shift_type = ShiftType.query.filter(
            ShiftType.name == name, ShiftType.id != shift_type_id
        ).first()
        if existing_shift_type:
            flash("❌ Un type de shift avec ce nom existe déjà.", "danger")
            return redirect(url_for("edit_shift_type", shift_type_id=shift_type_id))

        try:
            start_hour = int(start_hour)
            end_hour = int(end_hour)
            if not (0 <= start_hour < 24) or not (0 <= end_hour < 24):
                flash("❌ Les heures doivent être comprises entre 0 et 23.", "danger")
                return redirect(url_for("edit_shift_type", shift_type_id=shift_type_id))
            if start_hour >= end_hour:
                flash(
                    "❌ L'heure de début doit être antérieure à l'heure de fin.",
                    "danger",
                )
                return redirect(url_for("edit_shift_type", shift_type_id=shift_type_id))

            shift_type.name = name
            shift_type.label = label
            shift_type.start_hour = start_hour
            shift_type.end_hour = end_hour
            db.session.commit()
            flash("✅ Type de shift modifié avec succès !", "success")
            return redirect(url_for("list_shift_types"))
        except ValueError:
            db.session.rollback()
            flash("❌ Les heures doivent être des nombres entiers.", "danger")
            return redirect(url_for("edit_shift_type", shift_type_id=shift_type_id))
        except Exception as e:
            db.session.rollback()
            flash(f"❌ Erreur : {str(e)}", "danger")

    return render_template("admin/edit_shift_type.html", shift_type=shift_type)


@app.route("/admin/shift-types/delete/<int:shift_type_id>", methods=["POST"])
@admin_required
def delete_shift_type(shift_type_id):
    shift_type = db.session.get(ShiftType, shift_type_id) or abort(404)

    # Vérifier si le type de shift est utilisé
    if Shift.query.filter_by(shift_type_id=shift_type_id).first():
        flash(
            "❌ Impossible de supprimer ce type de shift : il est utilisé dans des shifts existants.",
            "danger",
        )
        return redirect(url_for("list_shift_types"))

    try:
        db.session.delete(shift_type)
        db.session.commit()
        flash("✅ Type de shift supprimé avec succès !", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Erreur : {str(e)}", "danger")

    return redirect(url_for("list_shift_types"))

# ============================================================================
# AUTOMATISATION - ASTREINTES ET SHIFTS
# ============================================================================


@app.route("/admin/automation")
@admin_required
def automation_dashboard():
    """Tableau de bord de l'automatisation."""
    status = get_automation_status()
    
    # Récupérer les utilisateurs éligibles
    oncall_users = OnCallAutomation.get_eligible_users()
    shift_users = ShiftAutomation.get_eligible_users()
    
    # Récupérer les types de shifts
    shift_types = ShiftAutomation.get_shift_types()
    
    # Récupérer les règles par défaut
    shift_rules = BusinessRules.get_shift_rules()
    oncall_rules = BusinessRules.get_oncall_rules()
    
    return render_template(
        "admin/automation/dashboard.html",
        status=status,
        oncall_users=oncall_users,
        shift_users=shift_users,
        shift_types=shift_types,
        shift_rules=shift_rules,
        oncall_rules=oncall_rules,
    )




@app.route("/admin/automation/shifts", methods=["GET", "POST"])
@admin_required
def automation_shifts():
    """Configuration et génération des shifts automatiques."""
    if request.method == "POST":
        action = request.form.get("action")
        
        if action == "generate":
            start_date_str = request.form.get("start_date")
            end_date_str = request.form.get("end_date")
            
            rules = BusinessRules.get_shift_rules()
            
            for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']:
                for shift_type in ['morning', 'afternoon', 'evening']:
                    count_key = f"{day}_{shift_type}"
                    if count_key in request.form:
                        try:
                            count = int(request.form[count_key])
                            if day not in rules['daily_requirements']:
                                rules['daily_requirements'][day] = {}
                            rules['daily_requirements'][day][shift_type] = count
                        except ValueError:
                            pass
            
            try:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
                
                shifts, messages = ShiftAutomation.generate_shift_schedule(
                    start_date, end_date, rules
                )
                
                for msg in messages:
                    flash(msg, "success" if "✅" in msg or "🎉" in msg else "warning" if "⚠️" in msg else "danger")
                
                return redirect(url_for("automation_shifts"))
                
            except ValueError as e:
                flash(f"❌ Format de date invalide : {str(e)}", "danger")
            except Exception as e:
                flash(f"❌ Erreur : {str(e)}", "danger")
        
        elif action == "dry_run":
            start_date_str = request.form.get("start_date")
            end_date_str = request.form.get("end_date")
            
            rules = BusinessRules.get_shift_rules()
            
            for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']:
                for shift_type in ['morning', 'afternoon', 'evening']:
                    count_key = f"{day}_{shift_type}"
                    if count_key in request.form:
                        try:
                            count = int(request.form[count_key])
                            if day not in rules['daily_requirements']:
                                rules['daily_requirements'][day] = {}
                            rules['daily_requirements'][day][shift_type] = count
                        except ValueError:
                            pass
            
            try:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
                
                shifts, messages = ShiftAutomation.generate_shift_schedule(
                    start_date, end_date, rules, dry_run=True
                )
                
                return render_template(
                    "admin/automation/shifts_dry_run.html",
                    shifts=shifts,
                    messages=messages,
                    start_date=start_date,
                    end_date=end_date,
                )
                
            except ValueError as e:
                flash(f"❌ Format de date invalide : {str(e)}", "danger")
            except Exception as e:
                flash(f"❌ Erreur : {str(e)}", "danger")
    
    shift_users = ShiftAutomation.get_eligible_users()
    shift_types = ShiftAutomation.get_shift_types()
    shift_rules = BusinessRules.get_shift_rules()
    
    today = date.today()
    end_date_default = today + timedelta(days=180)
    start_date_default = today
    
    return render_template(
        "admin/automation/shifts.html",
        shift_users=shift_users,
        shift_types=shift_types,
        shift_rules=shift_rules,
        start_date_default=start_date_default,
        end_date_default=end_date_default,
    )


@app.route("/admin/automation/full", methods=["GET", "POST"])
@admin_required
def automation_full():
    """Génération complète (astreintes + shifts)."""
    if request.method == "POST":
        action = request.form.get("action")
        
        if action in ["generate", "dry_run", "save_order"]:
            start_date_str = request.form.get("start_date")
            end_date_str = request.form.get("end_date")
            
            # Récupérer les positions et inclusions depuis le formulaire
            user_data = []
            for key, value in request.form.items():
                if key.startswith("rotation_order_"):
                    user_id = int(key.replace("rotation_order_", ""))
                    position = int(value)
                    include = request.form.get(f"include_{user_id}", "0") == "1"
                    user_data.append({
                        'user_id': user_id,
                        'position': position,
                        'include': include
                    })
            
            # Trier par position et extraire les IDs dans l'ordre
            user_data_sorted = sorted(user_data, key=lambda x: x['position'])
            rotation_order_ids = [u['user_id'] for u in user_data_sorted if u['include']]
            
            # Si c'est juste pour sauvegarder l'ordre, on sauvegarde dans la base
            if action == "save_order":
                try:
                    from app.models import AutomationConfig
                    AutomationConfig.set_rotation_order(rotation_order_ids)
                    flash("✅ Ordre de rotation enregistré ! Utilisez le bouton 'Générer' pour appliquer.", "success")
                except Exception as e:
                    db.session.rollback()
                    flash(f"❌ Erreur lors de la sauvegarde de l'ordre : {str(e)}", "danger")
                return redirect(url_for("automation_full"))
            
            try:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
                
                dry_run = (action == "dry_run")
                
                # Générer les astreintes
                oncalls, oncall_messages = OnCallAutomation.generate_oncall_schedule(
                    start_date, end_date, rotation_order_ids, dry_run=dry_run
                )
                
                if dry_run:
                    # Pour le dry run, afficher les astreintes générées
                    return render_template(
                        "admin/automation/oncall_dry_run.html",
                        oncalls=oncalls,
                        messages=oncall_messages,
                        start_date=start_date,
                        end_date=end_date,
                    )
                else:
                    # Supprimer les astreintes et shifts existants pour la période avant de régénérer
                    from app.models import Shift, OnCall
                    
                    # Supprimer les astreintes existantes qui chevauchent la période
                    # Une astreinte chevauche si : start_time < end_date ET end_time > start_date
                    existing_oncalls = OnCall.query.filter(
                        OnCall.start_time < datetime.combine(end_date + timedelta(days=1), datetime.min.time()),
                        OnCall.end_time > datetime.combine(start_date, datetime.min.time())
                    ).all()
                    
                    if existing_oncalls:
                        for oncall in existing_oncalls:
                            db.session.delete(oncall)
                        db.session.commit()
                        flash(f"🗑️ {len(existing_oncalls)} astreintes existantes supprimées pour la période", "info")
                    
                    # Supprimer les shifts existants pour la période
                    existing_shifts = Shift.query.filter(
                        Shift.date >= start_date,
                        Shift.date <= end_date
                    ).all()
                    
                    if existing_shifts:
                        for shift in existing_shifts:
                            db.session.delete(shift)
                        db.session.commit()
                        flash(f"🗑️ {len(existing_shifts)} shifts existants supprimés pour la période", "info")
                    
                    # Générer automatiquement les astreintes et shifts
                    shifts, shift_messages = AdvancedShiftAutomation.generate_full_schedule(
                        start_date, end_date, dry_run=False
                    )
                    
                    for msg in oncall_messages:
                        flash(msg, "success" if "✅" in msg or "🎉" in msg else "warning" if "⚠️" in msg else "danger")
                    for msg in shift_messages:
                        flash(msg, "success" if "✅" in msg or "🎉" in msg else "warning" if "⚠️" in msg else "info")
                    
                    flash(f"🔄 Régénération complète terminée pour la période du {start_date.strftime('%d/%m/%Y')} au {end_date.strftime('%d/%m/%Y')}", "success")
                    return redirect(url_for("automation_full"))
                
            except ValueError as e:
                flash(f"❌ Format de date invalide : {str(e)}", "danger")
            except Exception as e:
                flash(f"❌ Erreur : {str(e)}", "danger")
    
    oncall_users = OnCallAutomation.get_eligible_users()
    
    # Essayer de récupérer l'ordre de rotation actuel depuis la base de données
    try:
        from app.models import AutomationConfig
        current_rotation_order = AutomationConfig.get_rotation_order()
    except Exception:
        current_rotation_order = None
    
    today = date.today()
    end_date_default = today + timedelta(days=180)
    start_date_default = today
    while start_date_default.weekday() != 4:
        start_date_default += timedelta(days=1)
    
    return render_template(
        "admin/automation/full.html",
        oncall_users=oncall_users,
        start_date_default=start_date_default,
        end_date_default=end_date_default,
        current_rotation_order=current_rotation_order,
    )


@app.route("/admin/automation/status")
@admin_required
def automation_status():
    """Affiche l'état actuel de l'automatisation."""
    status = get_automation_status()
    return render_template("admin/automation/status.html", status=status)


@app.route("/admin/automation/refresh-shifts", methods=["GET", "POST"])
@admin_required
def refresh_shifts():
    """
    Rafraîchit les shifts en vérifiant les astreintes actuelles.
    
    Cette route permet de recalculer tous les shifts pour une période donnée
    en tenant compte des astreintes actuelles (même modifiées manuellement).
    """
    if request.method == "POST":
        start_date_str = request.form.get("start_date")
        end_date_str = request.form.get("end_date")
        
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            
            # D'abord, supprimer les shifts existants pour la période
            existing_shifts = Shift.query.filter(
                Shift.date >= start_date,
                Shift.date <= end_date
            ).all()
            
            if existing_shifts:
                for shift in existing_shifts:
                    db.session.delete(shift)
                db.session.commit()
                flash(f"🗑️ {len(existing_shifts)} shifts existants supprimés pour la période", "info")
            
            # Ensuite, régénérer les shifts avec les nouvelles règles
            shifts, messages = AdvancedShiftAutomation.generate_full_schedule(
                start_date, end_date, dry_run=False
            )
            
            for msg in messages:
                flash(msg, "success" if "✅" in msg or "🎉" in msg else "warning" if "⚠️" in msg else "info")
            
            flash(f"🔄 {len(shifts)} shifts régénérés avec succès !", "success")
            return redirect(url_for("refresh_shifts"))
            
        except ValueError as e:
            flash(f"❌ Format de date invalide : {str(e)}", "danger")
        except Exception as e:
            db.session.rollback()
            flash(f"❌ Erreur : {str(e)}", "danger")
    
    # Valeurs par défaut : aujourd'hui à aujourd'hui + 6 mois
    today = date.today()
    end_date_default = today + timedelta(days=180)
    start_date_default = today
    
    return render_template(
        "admin/automation/refresh_shifts.html",
        start_date_default=start_date_default,
        end_date_default=end_date_default,
    )
