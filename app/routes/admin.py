from flask import render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from sqlalchemy.orm import selectinload
from app import app, db
from app.models import User, Shift, OnCall, Leave, Group
from app.utils.decorators import admin_required


# Dashboard admin
@app.route('/admin')
@admin_required
def admin_dashboard():
    users_count = User.query.count()
    shifts_count = Shift.query.count()
    on_calls_count = OnCall.query.count()
    leaves_count = Leave.query.count()
    groups_count = Group.query.count()
    return render_template(
        'admin/dashboard.html',
        users_count=users_count,
        shifts_count=shifts_count,
        on_calls_count=on_calls_count,
        leaves_count=leaves_count,
        groups_count=groups_count,
    )


# ==================== GESTION DES GROUPES ====================

@app.route('/admin/groups')
@admin_required
def list_groups():
    groups = Group.query.order_by(Group.name).all()
    return render_template('admin/groups.html', groups=groups)


@app.route('/admin/groups/add', methods=['GET', 'POST'])
@admin_required
def add_group():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        is_part_of_schedule = 'is_part_of_schedule' in request.form
        is_part_of_oncall = 'is_part_of_oncall' in request.form

        if not name:
            flash('❌ Le nom du groupe est obligatoire.', 'danger')
            return redirect(url_for('add_group'))

        if Group.query.filter_by(name=name).first():
            flash('❌ Un groupe avec ce nom existe déjà.', 'danger')
            return redirect(url_for('add_group'))

        try:
            new_group = Group(
                name=name,
                is_part_of_schedule=is_part_of_schedule,
                is_part_of_oncall=is_part_of_oncall,
            )
            db.session.add(new_group)
            db.session.commit()
            flash('✅ Groupe ajouté avec succès !', 'success')
            return redirect(url_for('list_groups'))
        except Exception as e:
            db.session.rollback()
            flash(f'❌ Erreur : {str(e)}', 'danger')

    return render_template('admin/add_group.html')


@app.route('/admin/groups/edit/<int:group_id>', methods=['GET', 'POST'])
@admin_required
def edit_group(group_id):
    group = Group.query.get_or_404(group_id)

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        is_part_of_schedule = 'is_part_of_schedule' in request.form
        is_part_of_oncall = 'is_part_of_oncall' in request.form

        if not name:
            flash('❌ Le nom du groupe est obligatoire.', 'danger')
            return redirect(url_for('edit_group', group_id=group_id))

        existing_group = Group.query.filter(Group.name == name, Group.id != group_id).first()
        if existing_group:
            flash('❌ Un groupe avec ce nom existe déjà.', 'danger')
            return redirect(url_for('edit_group', group_id=group_id))

        try:
            group.name = name
            group.is_part_of_schedule = is_part_of_schedule
            group.is_part_of_oncall = is_part_of_oncall
            db.session.commit()
            flash('✅ Groupe modifié avec succès !', 'success')
            return redirect(url_for('list_groups'))
        except Exception as e:
            db.session.rollback()
            flash(f'❌ Erreur : {str(e)}', 'danger')

    return render_template('admin/edit_group.html', group=group)


@app.route('/admin/groups/delete/<int:group_id>')
@admin_required
def delete_group(group_id):
    group = Group.query.get_or_404(group_id)

    if User.query.filter_by(group_id=group_id).first():
        flash('❌ Impossible de supprimer ce groupe : des utilisateurs y sont associés.', 'danger')
        return redirect(url_for('list_groups'))

    try:
        db.session.delete(group)
        db.session.commit()
        flash('✅ Groupe supprimé avec succès !', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Erreur : {str(e)}', 'danger')

    return redirect(url_for('list_groups'))


# ==================== GESTION DES UTILISATEURS ====================

@app.route('/admin/users')
@admin_required
def list_users():
    users = User.query.options(
        selectinload(User.shifts),
        selectinload(User.on_calls),
        selectinload(User.leaves),
    ).order_by(User.name).all()
    groups = Group.query.all()
    return render_template('admin/users.html', users=users, groups=groups)


@app.route('/admin/users/add', methods=['GET', 'POST'])
@admin_required
def add_user():
    groups = Group.query.all()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        group_id = request.form.get('group_id')
        password = request.form.get('password', '')

        if not all([name, email, group_id]):
            flash('❌ Tous les champs sont obligatoires.', 'danger')
            return render_template('admin/add_user.html', groups=groups)

        if User.query.filter_by(email=email).first():
            flash('❌ Un utilisateur avec cet email existe déjà.', 'danger')
            return render_template('admin/add_user.html', groups=groups)

        try:
            new_user = User(name=name, email=email, group_id=int(group_id))
            if password:
                new_user.set_password(password)
            else:
                # Générer un mot de passe par défaut
                new_user.set_password('password123')
            db.session.add(new_user)
            db.session.commit()
            flash('✅ Utilisateur ajouté avec succès !', 'success')
            return redirect(url_for('list_users'))
        except Exception as e:
            db.session.rollback()
            flash(f'❌ Erreur : {str(e)}', 'danger')

    return render_template('admin/add_user.html', groups=groups)


@app.route('/admin/users/edit/<int:user_id>', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    groups = Group.query.all()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        group_id = request.form.get('group_id')
        is_admin = 'is_admin' in request.form
        password = request.form.get('password', '')

        if not all([name, email, group_id]):
            flash('❌ Tous les champs sont obligatoires.', 'danger')
            return render_template('admin/edit_user.html', user=user, groups=groups)

        existing_user = User.query.filter(User.email == email, User.id != user_id).first()
        if existing_user:
            flash('❌ Un utilisateur avec cet email existe déjà.', 'danger')
            return render_template('admin/edit_user.html', user=user, groups=groups)

        try:
            user.name = name
            user.email = email
            user.group_id = int(group_id)
            user.is_admin = is_admin
            if password:
                user.set_password(password)
            db.session.commit()
            flash('✅ Utilisateur modifié avec succès !', 'success')
            return redirect(url_for('list_users'))
        except Exception as e:
            db.session.rollback()
            flash(f'❌ Erreur : {str(e)}', 'danger')

    return render_template('admin/edit_user.html', user=user, groups=groups)


@app.route('/admin/users/delete/<int:user_id>')
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)

    if Shift.query.filter_by(user_id=user_id).first() or \
       OnCall.query.filter_by(user_id=user_id).first() or \
       Leave.query.filter_by(user_id=user_id).first():
        flash('❌ Impossible de supprimer cet utilisateur : il a des shifts, astreintes ou congés associés.', 'danger')
        return redirect(url_for('list_users'))

    try:
        db.session.delete(user)
        db.session.commit()
        flash('✅ Utilisateur supprimé avec succès !', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Erreur : {str(e)}', 'danger')

    return redirect(url_for('list_users'))
