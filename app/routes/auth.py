from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from flask_login import login_user, logout_user, current_user, login_required
from app import db
from app.models import User, Group
from config_oidc import OIDCConfig
from app.auth.oidc_auth import oidc_auth

# Create blueprint
auth_bp = Blueprint("auth", __name__)


def is_basic_auth_disabled():
    """Vérifie si l'authentification basique est désactivée."""
    return OIDCConfig.ENABLED and OIDCConfig.DISABLE_BASIC_AUTH


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Page de connexion."""
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    # Vérifier si l'authentification basique est désactivée
    if is_basic_auth_disabled():
        # Rediriger vers la connexion OIDC
        return redirect(url_for("auth.oidc_login"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        remember = "remember" in request.form

        if not email or not password:
            flash("Email et mot de passe sont obligatoires.", "danger")
            return redirect(url_for("auth.login"))

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user, remember=remember)
            flash("Connexion réussie !", "success")

            # Rediriger vers la page demandée ou vers l'index
            next_page = request.args.get("next")
            return redirect(next_page or url_for("main.index"))
        else:
            flash("Email ou mot de passe incorrect.", "danger")

    return render_template("auth/login.html", oidc_enabled=OIDCConfig.ENABLED)


@auth_bp.route("/oidc/login")
def oidc_login():
    """Redirige vers le fournisseur OIDC pour l'authentification."""
    if is_basic_auth_disabled():
        return oidc_auth.authorize_redirect(request)
    else:
        return redirect(url_for("auth.login"))


@auth_bp.route("/oidc/callback")
def oidc_callback():
    """Callback pour l'authentification OIDC."""
    if not is_basic_auth_disabled():
        return redirect(url_for("auth.login"))
    
    try:
        token = oidc_auth.authorize_access_token(request)
        userinfo = token.parse_id_token(request, None)
        
        # Récupérer les informations de l'utilisateur depuis les claims OIDC
        email = userinfo.get(OIDCConfig.EMAIL_CLAIM, '')
        name = userinfo.get(OIDCConfig.NAME_CLAIM, '')
        username = userinfo.get(OIDCConfig.USERNAME_CLAIM, '')
        
        if not email:
            flash("Impossible de déterminer l'email depuis la réponse OIDC.", "danger")
            return redirect(url_for("auth.login"))
        
        # Trouver l'utilisateur existant par email
        user = User.query.filter_by(email=email).first()
        
        if not user:
            # Créer un nouvel utilisateur
            user = User(
                name=name or username or email,
                email=email,
                is_admin=False,
                group_id=1  # Groupe par défaut
            )
            db.session.add(user)
            db.session.commit()
        
        login_user(user, remember=True)
        flash("Connexion OIDC réussie !", "success")
        
        return redirect(url_for("main.index"))
        
    except Exception as e:
        current_app.logger.error(f"Erreur de callback OIDC : {e}")
        flash("La connexion OIDC a échoué. Veuillez réessayer.", "danger")
        return redirect(url_for("auth.login"))


@auth_bp.route("/logout")
@login_required
def logout():
    """Déconnexion."""
    logout_user()
    flash("Vous avez été déconnecté.", "success")
    return redirect(url_for("auth.login"))
