from flask import render_template, request, redirect, url_for, flash
from app import app, db
from app.models import User, Shift, OnCall, Leave, Group

# Dashboard admin
@app.route('/admin')
def admin_dashboard():
    users = User.query.all()
    shifts = Shift.query.all()
    on_calls = OnCall.query.all()
    leaves = Leave.query.all()
    groups = Group.query.all()
    return render_template('admin/dashboard.html', users=users, shifts=shifts, on_calls=on_calls, leaves=leaves, groups=groups)

# ==================== GESTION DES GROUPES ====================

# Lister tous les groupes
@app.route('/admin/groups')
def list_groups():
    groups = Group.query.order_by(Group.name).all()
    return render_template('admin/groups.html', groups=groups)

# Ajouter un groupe
@app.route('/admin/groups/add', methods=['GET', 'POST'])
def add_group():
    if request.method == 'POST':
        name = request.form.get('name')
        is_part_of_schedule = 'is_part_of_schedule' in request.form
        is_part_of_oncall = 'is_part_of_oncall' in request.form

        if Group.query.filter_by(name=name).first():
            flash('❌ Un groupe avec ce nom existe déjà.', 'error')
            return redirect(url_for('add_group'))

        try:
            new_group = Group(
                name=name,
                is_part_of_schedule=is_part_of_schedule,
                is_part_of_oncall=is_part_of_oncall
            )
            db.session.add(new_group)
            db.session.commit()
            flash('✅ Groupe ajouté avec succès !', 'success')
            return redirect(url_for('list_groups'))
        except Exception as e:
            db.session.rollback()
            flash(f'❌ Erreur : {str(e)}', 'error')

    return render_template('admin/add_group.html')

# Modifier un groupe
@app.route('/admin/groups/edit/<int:group_id>', methods=['GET', 'POST'])
def edit_group(group_id):
    group = Group.query.get_or_404(group_id)

    if request.method == 'POST':
        name = request.form.get('name')
        is_part_of_schedule = 'is_part_of_schedule' in request.form
        is_part_of_oncall = 'is_part_of_oncall' in request.form

        existing_group = Group.query.filter(Group.name == name, Group.id != group_id).first()
        if existing_group:
            flash('❌ Un groupe avec ce nom existe déjà.', 'error')
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
            flash(f'❌ Erreur : {str(e)}', 'error')

    return render_template('admin/edit_group.html', group=group)

# Supprimer un groupe
@app.route('/admin/groups/delete/<int:group_id>')
def delete_group(group_id):
    group = Group.query.get_or_404(group_id)

    # Vérifier qu'aucun utilisateur n'est dans ce groupe
    if User.query.filter_by(group_id=group_id).first():
        flash('❌ Impossible de supprimer ce groupe : des utilisateurs y sont associés.', 'error')
        return redirect(url_for('list_groups'))

    try:
        db.session.delete(group)
        db.session.commit()
        flash('✅ Groupe supprimé avec succès !', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Erreur : {str(e)}', 'error')

    return redirect(url_for('list_groups'))

# ==================== GESTION DES UTILISATEURS ====================

# Lister tous les utilisateurs
@app.route('/admin/users')
def list_users():
    users = User.query.order_by(User.name).all()
    groups = Group.query.all()
    return render_template('admin/users.html', users=users, groups=groups)

# Ajouter un utilisateur
@app.route('/admin/users/add', methods=['GET', 'POST'])
def add_user():
    
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        group_id = request.form.get('group_id')

        if User.query.filter_by(email=email).first():
            flash('❌ Un utilisateur avec cet email existe déjà.', 'error')
            return redirect(url_for('add_user'))

        try:
            new_user = User(name=name, email=email, group_id=group_id)
            db.session.add(new_user)
            db.session.commit()
            flash('✅ Utilisateur ajouté avec succès !', 'success')
            return redirect(url_for('list_users'))
        except Exception as e:
            db.session.rollback()
            flash(f'❌ Erreur : {str(e)}', 'error')
        pass
    groups = Group.query.all()  # ✅ Ajoute cette ligne pour envoyer les groupes au template
    return render_template('admin/add_user.html', groups=groups)

# Modifier un utilisateur
@app.route('/admin/users/edit/<int:user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    groups = Group.query.all()

    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        group_id = request.form.get('group_id')

        existing_user = User.query.filter(User.email == email, User.id != user_id).first()
        if existing_user:
            flash('❌ Un utilisateur avec cet email existe déjà.', 'error')
            return redirect(url_for('edit_user', user_id=user_id))

        try:
            user.name = name
            user.email = email
            user.group_id = group_id
            db.session.commit()
            flash('✅ Utilisateur modifié avec succès !', 'success')
            return redirect(url_for('list_users'))
        except Exception as e:
            db.session.rollback()
            flash(f'❌ Erreur : {str(e)}', 'error')
        pass
    groups = Group.query.all()  # ✅ Ajoute cette ligne pour envoyer les groupes au template
    return render_template('admin/edit_user.html', user=user, groups=groups)

# Supprimer un utilisateur
@app.route('/admin/users/delete/<int:user_id>')
def delete_user(user_id):
    user = User.query.get_or_404(user_id)

    if Shift.query.filter_by(user_id=user_id).first() or \
       OnCall.query.filter_by(user_id=user_id).first() or \
       Leave.query.filter_by(user_id=user_id).first():
        flash('❌ Impossible de supprimer cet utilisateur : il a des shifts, astreintes ou congés associés.', 'error')
        return redirect(url_for('list_users'))

    try:
        db.session.delete(user)
        db.session.commit()
        flash('✅ Utilisateur supprimé avec succès !', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Erreur : {str(e)}', 'error')

    return redirect(url_for('list_users'))