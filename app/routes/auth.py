from flask import render_template, request, redirect, url_for, flash, session, current_app
from flask_login import login_user, logout_user, current_user, login_required
from app import app, db
from app.models import User, Group
from config_oidc import OIDCConfig
from app.auth.oidc_auth import oidc_auth


def is_basic_auth_disabled():
    """Vérifie si l'authentification basique est désactivée."""
    return OIDCConfig.ENABLED and OIDCConfig.DISABLE_BASIC_AUTH


@app.route("/login", methods=["GET", "POST"])
def login():
    """Page de connexion."""
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    # Vérifier si l'authentification basique est désactivée
    if is_basic_auth_disabled():
        # Rediriger vers la connexion OIDC
        return redirect(url_for("oidc_login"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        remember = "remember" in request.form

        if not email or not password:
            flash("e94c Email et mot de passe sont obligatoires.", "danger")
            return redirect(url_for("login"))

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user, remember=remember)
            flash("e905 Connexion réussie !", "success")

            # Rediriger vers la page demandée ou vers l'index
            next_page = request.args.get("next")
            return redirect(next_page or url_for("index"))
        else:
            flash("e94c Email ou mot de passe incorrect.", "danger")

    return render_template("auth/login.html", oidc_enabled=OIDCConfig.ENABLED)


@app.route("/oidc/login")
def oidc_login():
    """Redirige vers le fournisseur OIDC pour l'authentification."""
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    
    # ✅ DEBUG: Vérifier l'état de l'authentification OIDC
    print(f"[DEBUG oidc_login] OIDCConfig.ENABLED: {OIDCConfig.ENABLED}")
    print(f"[DEBUG oidc_login] OIDCConfig.is_configured(): {OIDCConfig.is_configured()}")
    print(f"[DEBUG oidc_login] oidc_auth.oidc_client: {oidc_auth.oidc_client}")
    print(f"[DEBUG oidc_login] session avant: {dict(session)}")
    
    if not OIDCConfig.ENABLED or not OIDCConfig.is_configured():
        print("[DEBUG oidc_login] OIDC non configuré, redirection vers login")
        flash("L'authentification OIDC n'est pas configurée.", "danger")
        return redirect(url_for("login"))
    
    # Générer l'URL d'autorisation OIDC
    auth_url = oidc_auth.get_authorization_url()
    print(f"[DEBUG oidc_login] auth_url générée: {auth_url}")
    print(f"[DEBUG oidc_login] session après get_authorization_url: {dict(session)}")
    
    if not auth_url:
        print("[DEBUG oidc_login] auth_url est None!")
        flash("Impossible de générer l'URL d'authentification OIDC.", "danger")
        return redirect(url_for("login"))
    
    print(f"[DEBUG oidc_login] Redirection vers: {auth_url}")
    return redirect(auth_url)


@app.route("/oidc/callback")
def oidc_callback():
    """Gère le callback OIDC après l'authentification."""
    print(f"[DEBUG callback] session à l'arrivée: {dict(session)}")
    print(f"[DEBUG callback] request.args: {dict(request.args)}")
    
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    
    if not OIDCConfig.ENABLED or not OIDCConfig.is_configured():
        flash("L'authentification OIDC n'est pas configurée.", "danger")
        return redirect(url_for("login"))
    
    # Gérer le callback OIDC
    user_data = oidc_auth.handle_oauth_callback(request)
    
    if not user_data:
        print("[DEBUG callback] user_data est None")
        return redirect(url_for("login"))
    
    # Connecter l'utilisateur
    user = oidc_auth.login_user(user_data)
    
    if not user:
        flash("Impossible de connecter l'utilisateur OIDC.", "danger")
        return redirect(url_for("login"))
    
    flash("e905 Connexion OIDC réussie !", "success")
    
    # Rediriger vers la page demandée ou vers l'index
    next_page = session.pop('next', None) or request.args.get('next')
    return redirect(next_page or url_for("index"))


@app.route("/logout")
@login_required
def logout():
    """Déconnexion."""
    # Déconnexion OIDC si nécessaire
    if OIDCConfig.ENABLED:
        # Pour une déconnexion complète OIDC, il faudrait rediriger vers 
        # l'endpoint de fin de session du fournisseur OIDC
        # Pour l'instant, on se contente de la déconnexion locale
        pass
    
    logout_user()
    
    # Nettoyer la session
    session.clear()
    
    flash("e905 Déconnexion réussie.", "success")
    return redirect(url_for("index"))


@app.route("/register", methods=["GET", "POST"])
def register():
    """Page d'inscription (désactivée par défaut, seule l'admin peut créer des utilisateurs)."""
    # Vérifier si l'inscription est autorisée (par exemple, via une variable de config)
    # Pour l'instant, on désactive l'inscription publique
    
    # Si OIDC est activé et que l'authentification basique est désactivée,
    # rediriger vers la connexion OIDC
    if is_basic_auth_disabled():
        flash("e94c L'inscription publique est désactivée. Utilisez l'authentification OIDC.", "danger")
        return redirect(url_for("oidc_login"))
    
    flash(
        "e94c L'inscription publique est désactivée. Contactez l'administrateur.",
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
            flash("e94c Le nom et l'email sont obligatoires.", "danger")
            return redirect(url_for("update_profile"))

        # Vérifier si l'email est déjà utilisé par un autre utilisateur
        existing_user = User.query.filter(
            User.email == email, User.id != current_user.id
        ).first()
        if existing_user:
            flash("e94c Cet email est déjà utilisé par un autre utilisateur.", "danger")
            return redirect(url_for("update_profile"))

        # Mettre à jour les informations de base
        current_user.name = name
        current_user.email = email

        # Mettre à jour le mot de passe si fourni
        if new_password:
            # Pour les utilisateurs OIDC, on ne peut pas changer le mot de passe
            # car ils s'authentifient via OIDC
            if current_user.password_hash is None:
                flash(
                    "e94c Les utilisateurs OIDC ne peuvent pas changer leur mot de passe. Utilisez votre fournisseur OIDC.",
                    "danger",
                )
                return redirect(url_for("update_profile"))
            
            if not current_password:
                flash(
                    "e94c Le mot de passe actuel est obligatoire pour changer de mot de passe.",
                    "danger",
                )
                return redirect(url_for("update_profile"))

            if not current_user.check_password(current_password):
                flash("e94c Le mot de passe actuel est incorrect.", "danger")
                return redirect(url_for("update_profile"))

            if new_password != confirm_password:
                flash("e94c Les nouveaux mots de passe ne correspondent pas.", "danger")
                return redirect(url_for("update_profile"))

            current_user.set_password(new_password)

        try:
            db.session.commit()
            flash("e905 Profil mis à jour avec succès !", "success")
            return redirect(url_for("profile"))
        except Exception as e:
            db.session.rollback()
            flash(f"e94c Erreur : {str(e)}", "danger")

    return render_template("auth/update_profile.html", user=current_user)


@app.route("/profile/ics-token", methods=["GET", "POST"])
@login_required
def generate_ics_token():
    """Génère ou régénère le token ICS pour l'export du calendrier."""
    if request.method == "POST":
        # Régénérer le token
        token = current_user.generate_ics_token()
        try:
            db.session.commit()
            flash(f"e905 Token ICS régénéré avec succès !", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"e94c Erreur : {str(e)}", "danger")
    
    # Afficher la page avec le token actuel
    token = current_user.ics_token
    
    return render_template(
        "auth/ics_token.html",
        user=current_user,
        token=token
    )
