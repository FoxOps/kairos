from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, current_user, login_required
from app import db
from app.models import User, Group
from config_oidc import OIDCConfig
from app.auth.oidc_auth import oidc_auth
from app.auth.decorators import admin_required, role_required

# Create blueprint
auth_bp = Blueprint("auth", __name__)


def is_basic_auth_disabled():
    """Vérifie si l'authentification basique est désactivée."""
    return OIDCConfig.ENABLED and OIDCConfig.DISABLE_BASIC_AUTH


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """Page d'inscription (désactivée par défaut, seule l'admin peut créer des utilisateurs)."""
    # Vérifier si l'inscription est autorisée (par exemple, via une variable de config)
    # Pour l'instant, on désactive l'inscription publique

    # Si OIDC est activé et que l'authentification basique est désactivée,
    # rediriger vers la connexion OIDC
    if is_basic_auth_disabled():
        flash(
            "L'inscription publique est désactivée. Utilisez l'authentification OIDC.",
            "danger",
        )
        return redirect(url_for("auth.oidc_login"))

    flash(
        "L'inscription publique est désactivée. Contactez l'administrateur.",
        "danger",
    )
    return redirect(url_for("auth.login"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Page de connexion."""
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    # Vérifier si l'authentification basique est désactivée
    #
    # oidc_error=1 casse volontairement ce renvoi automatique : sans lui,
    # tout échec OIDC (fournisseur injoignable, mauvaise config,
    # synchronisation utilisateur qui échoue...) redirige vers /login,
    # qui ici redirige aussitôt vers /oidc/login, qui échoue à nouveau et
    # redirige vers /login - boucle de redirection infinie
    # (ERR_TOO_MANY_REDIRECTS côté navigateur), application totalement
    # inaccessible tant que le SSO ne fonctionne pas. Bug réel trouvé en
    # écrivant les tests OIDC (voir tests/integration/test_oidc_routes.py).
    if is_basic_auth_disabled() and not request.args.get("oidc_error"):
        # Rediriger vers la connexion OIDC
        return redirect(url_for("auth.oidc_login"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
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
    if not is_basic_auth_disabled():
        return redirect(url_for("auth.login"))

    auth_url = oidc_auth.get_authorization_url()
    if not auth_url:
        flash("La connexion OIDC n'est pas disponible pour le moment.", "danger")
        return redirect(url_for("auth.login", oidc_error=1))

    return redirect(auth_url)


@auth_bp.route("/oidc/callback")
def oidc_callback():
    """Callback pour l'authentification OIDC."""
    if not is_basic_auth_disabled():
        return redirect(url_for("auth.login"))

    user_data = oidc_auth.handle_oauth_callback(request)
    if not user_data:
        # handle_oauth_callback affiche déjà un message d'erreur (flash)
        return redirect(url_for("auth.login", oidc_error=1))

    user = oidc_auth.login_user(user_data)
    if not user:
        flash("La connexion OIDC a échoué. Veuillez réessayer.", "danger")
        return redirect(url_for("auth.login", oidc_error=1))

    flash("Connexion OIDC réussie !", "success")
    return redirect(url_for("main.index"))


@auth_bp.route("/logout")
@login_required
def logout():
    """Déconnexion."""
    is_oidc_mode = is_basic_auth_disabled()
    logout_user()

    if is_oidc_mode:
        # Déconnexion locale seulement : la session côté fournisseur OIDC
        # reste active, donc la prochaine redirection vers l'écran de
        # connexion ré-authentifie silencieusement l'utilisateur via SSO
        # (la déconnexion semble ne rien faire). Utiliser la déconnexion
        # RP-initiated si le fournisseur l'expose (end_session_endpoint).
        logout_url = oidc_auth.build_logout_url(
            OIDCConfig.POST_LOGOUT_REDIRECT_URI or None
        )
        if logout_url:
            return redirect(logout_url)
        return redirect(url_for("auth.login"))

    flash("Vous avez été déconnecté.", "success")
    return redirect(url_for("auth.login"))


@auth_bp.route("/profile")
@login_required
def profile():
    """Page de profil utilisateur."""
    return render_template("auth/profile.html", user=current_user)


@auth_bp.route("/profile/update", methods=["GET", "POST"])
@login_required
def update_profile():
    """Mise à jour du profil utilisateur."""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        # Vérifier que le nom et l'email ne sont pas vides
        if not name or not email:
            flash("Le nom et l'email sont obligatoires.", "danger")
            return redirect(url_for("auth.update_profile"))

        # Vérifier si l'email a changé
        if email != current_user.email:
            # Vérifier que l'email n'est pas déjà utilisé
            existing_user = User.query.filter_by(email=email).first()
            if existing_user and existing_user.id != current_user.id:
                flash("Cet email est déjà utilisé par un autre utilisateur.", "danger")
                return redirect(url_for("auth.update_profile"))
            current_user.email = email

        # Mettre à jour le nom
        current_user.name = name

        # Mettre à jour le mot de passe si fourni
        if new_password:
            if not current_password:
                flash(
                    "Le mot de passe actuel est obligatoire pour changer de mot de passe.",
                    "danger",
                )
                return redirect(url_for("auth.update_profile"))

            if not current_user.check_password(current_password):
                flash("Le mot de passe actuel est incorrect.", "danger")
                return redirect(url_for("auth.update_profile"))

            if new_password != confirm_password:
                flash("Les nouveaux mots de passe ne correspondent pas.", "danger")
                return redirect(url_for("auth.update_profile"))

            current_user.set_password(new_password)

        db.session.commit()
        flash("Votre profil a été mis à jour avec succès !", "success")
        return redirect(url_for("auth.profile"))

    return render_template("auth/update_profile.html", user=current_user)


@auth_bp.route("/profile/ics-token", methods=["GET", "POST"])
@login_required
def generate_ics_token():
    """Génère ou régénère le token ICS pour l'export du calendrier."""
    if request.method == "POST":
        # Régénérer le token
        token = current_user.generate_ics_token()
        try:
            db.session.commit()
            flash("Token ICS régénéré avec succès !", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Erreur : {str(e)}", "danger")

    # Afficher la page avec le token actuel
    token = current_user.ics_token

    return render_template("auth/ics_token.html", user=current_user, token=token)
