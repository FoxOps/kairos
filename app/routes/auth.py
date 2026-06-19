from flask import render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, current_user, login_required
from app import app, db
from app.models import User, Group


@app.route("/login", methods=["GET", "POST"])
def login():
    """Page de connexion."""
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        remember = "remember" in request.form

        if not email or not password:
            flash("❌ Email et mot de passe sont obligatoires.", "danger")
            return redirect(url_for("login"))

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user, remember=remember)
            flash("✅ Connexion réussie !", "success")

            # Rediriger vers la page demandée ou vers l'index
            next_page = request.args.get("next")
            return redirect(next_page or url_for("index"))
        else:
            flash("❌ Email ou mot de passe incorrect.", "danger")

    return render_template("auth/login.html")


@app.route("/logout")
@login_required
def logout():
    """Déconnexion."""
    logout_user()
    flash("✅ Déconnexion réussie.", "success")
    return redirect(url_for("index"))


@app.route("/register", methods=["GET", "POST"])
def register():
    """Page d'inscription (désactivée par défaut, seule l'admin peut créer des utilisateurs)."""
    # Vérifier si l'inscription est autorisée (par exemple, via une variable de config)
    # Pour l'instant, on désactive l'inscription publique
    flash(
        "❌ L'inscription publique est désactivée. Contactez l'administrateur.",
        "danger",
    )
    return redirect(url_for("login"))


@app.route("/profile")
@login_required
def profile():
    """Page de profil utilisateur."""
    return render_template("auth/profile.html", user=current_user)


@app.route("/profile/update", methods=["GET", "POST"])
@login_required
def update_profile():
    """Mettre à jour le profil utilisateur."""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not name or not email:
            flash("❌ Le nom et l'email sont obligatoires.", "danger")
            return redirect(url_for("update_profile"))

        # Vérifier si l'email est déjà utilisé par un autre utilisateur
        existing_user = User.query.filter(
            User.email == email, User.id != current_user.id
        ).first()
        if existing_user:
            flash("❌ Cet email est déjà utilisé par un autre utilisateur.", "danger")
            return redirect(url_for("update_profile"))

        # Mettre à jour les informations de base
        current_user.name = name
        current_user.email = email

        # Mettre à jour le mot de passe si fourni
        if new_password:
            if not current_password:
                flash(
                    "❌ Le mot de passe actuel est obligatoire pour changer de mot de passe.",
                    "danger",
                )
                return redirect(url_for("update_profile"))

            if not current_user.check_password(current_password):
                flash("❌ Le mot de passe actuel est incorrect.", "danger")
                return redirect(url_for("update_profile"))

            if new_password != confirm_password:
                flash("❌ Les nouveaux mots de passe ne correspondent pas.", "danger")
                return redirect(url_for("update_profile"))

            current_user.set_password(new_password)

        try:
            db.session.commit()
            flash("✅ Profil mis à jour avec succès !", "success")
            return redirect(url_for("profile"))
        except Exception as e:
            db.session.rollback()
            flash(f"❌ Erreur : {str(e)}", "danger")

    return render_template("auth/update_profile.html", user=current_user)
