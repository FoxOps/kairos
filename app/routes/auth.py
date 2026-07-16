from urllib.parse import urljoin, urlparse
from zoneinfo import available_timezones

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_babel import gettext as _
from flask_login import current_user, login_required, login_user, logout_user

from app import db
from app.auth.oidc_auth import oidc_auth
from app.models import User
from app.services import AuditService, SettingsService
from app.utils.helpers.common_helpers import (
    get_date_format_choices,
    get_language_choices,
    get_time_format_choices,
    get_timezone_choices,
)
from config_oidc import OIDCConfig

# Create blueprint
auth_bp = Blueprint("auth", __name__)


def is_basic_auth_disabled():
    """Check whether basic authentication is disabled."""
    return OIDCConfig.ENABLED and OIDCConfig.DISABLE_BASIC_AUTH


def _is_safe_next_url(target: str) -> bool:
    """Reject post-login redirect URLs pointing outside this site.

    Without this, ?next=https://phishing.example would pass straight
    through to redirect(): an attacker sends a legitimate-looking login
    link with this parameter, the victim authenticates normally and
    lands on an external site (CWE-601, a classic open redirect used for
    phishing).
    """
    if not target:
        return False
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ("http", "https") and ref_url.netloc == test_url.netloc


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """Registration page (disabled by default, only an admin can create users)."""
    # Check whether registration is allowed (e.g. via a config variable)
    # For now, public registration is disabled

    # If OIDC is enabled and basic authentication is disabled, redirect
    # to OIDC login
    AuditService.log("auth.register", details=request.form.get("email", ""))

    if is_basic_auth_disabled():
        flash(
            _(
                "L'inscription publique est désactivée. Utilisez l'authentification OIDC."
            ),
            "danger",
        )
        return redirect(url_for("auth.oidc_login"))

    flash(
        _("L'inscription publique est désactivée. Contactez l'administrateur."),
        "danger",
    )
    return redirect(url_for("auth.login"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Login page."""
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    # oidc_error=1 deliberately breaks this automatic redirect: without
    # it, any OIDC failure (provider unreachable, bad config, user sync
    # failing...) redirects to /login, which here immediately redirects
    # to /oidc/login, which fails again and redirects to /login - an
    # infinite redirect loop (ERR_TOO_MANY_REDIRECTS in the browser),
    # making the app entirely inaccessible as long as SSO is broken. See
    # tests/integration/test_oidc_routes.py for the regression test.
    if is_basic_auth_disabled() and not request.args.get("oidc_error"):
        # Redirect to OIDC login
        return redirect(url_for("auth.oidc_login"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        remember = "remember" in request.form

        if not email or not password:
            flash(_("Email et mot de passe sont obligatoires."), "danger")
            return redirect(url_for("auth.login"))

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user, remember=remember)
            AuditService.log(
                "auth.login_success",
                resource_type="User",
                resource_id=user.id,
                actor=user,
            )
            flash(_("Connexion réussie !"), "success")

            # Redirect to the requested page, or to the index
            next_page = request.args.get("next")
            if next_page and _is_safe_next_url(next_page):
                return redirect(next_page)
            return redirect(url_for("main.index"))
        else:
            AuditService.log(
                "auth.login_failure",
                resource_type="User",
                resource_id=user.id if user else None,
                details=email,
            )
            flash(_("Email ou mot de passe incorrect."), "danger")

    return render_template("auth/login.html", oidc_enabled=OIDCConfig.ENABLED)


@auth_bp.route("/oidc/login")
def oidc_login():
    """Redirect to the OIDC provider for authentication.

    No guard on is_basic_auth_disabled() here (there used to be one,
    which was a real bug): this route must also work when
    OIDC_DISABLE_BASIC_AUTH is false (optional SSO alongside the regular
    login form - see the "Sign in with SSO" button on auth/login.html),
    not only when SSO is forced. The "OIDC not configured" case is
    already handled right below (get_authorization_url() returns None),
    so no extra guard is needed here.
    """
    auth_url = oidc_auth.get_authorization_url()
    if not auth_url:
        flash(_("La connexion OIDC n'est pas disponible pour le moment."), "danger")
        return redirect(url_for("auth.login", oidc_error=1))

    return redirect(auth_url)


@auth_bp.route("/oidc/callback")
def oidc_callback():
    """Callback for OIDC authentication.

    Same reason as oidc_login() above for the lack of a guard on
    is_basic_auth_disabled(): it used to block the IdP's return trip
    (code/state lost, redirect to /login) as soon as SSO was optional
    rather than forced. handle_oauth_callback() already handles the
    failure cleanly (flash + redirect) right below.
    """
    user_data = oidc_auth.handle_oauth_callback(request)
    if not user_data:
        # handle_oauth_callback already shows an error message (flash)
        return redirect(url_for("auth.login", oidc_error=1))

    user = oidc_auth.login_user(user_data)
    if not user:
        AuditService.log("auth.login_failure", details="OIDC")
        flash(_("La connexion OIDC a échoué. Veuillez réessayer."), "danger")
        return redirect(url_for("auth.login", oidc_error=1))

    AuditService.log(
        "auth.login_success",
        resource_type="User",
        resource_id=user.id,
        details="OIDC",
        actor=user,
    )
    flash(_("Connexion OIDC réussie !"), "success")
    return redirect(url_for("main.index"))


@auth_bp.route("/logout")
@login_required
def logout():
    """Logout."""
    is_oidc_mode = is_basic_auth_disabled()
    AuditService.log("auth.logout", resource_type="User", resource_id=current_user.id)
    logout_user()

    if is_oidc_mode:
        # Local logout only: the session on the OIDC provider's side
        # stays active, so the next redirect to the login screen
        # silently re-authenticates the user via SSO (logout appears to
        # do nothing). Use RP-initiated logout if the provider exposes
        # it (end_session_endpoint).
        logout_url = oidc_auth.build_logout_url(
            OIDCConfig.POST_LOGOUT_REDIRECT_URI or None
        )
        if logout_url:
            return redirect(logout_url)
        return redirect(url_for("auth.login"))

    flash(_("Vous avez été déconnecté."), "success")
    return redirect(url_for("auth.login"))


@auth_bp.route("/profile")
@login_required
def profile():
    """User profile page."""
    return render_template("auth/profile.html", user=current_user)


@auth_bp.route("/profile/update", methods=["GET", "POST"])
@login_required
def update_profile():
    """Update the user's profile."""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        # Check that name and email aren't empty
        if not name or not email:
            flash(_("Le nom et l'email sont obligatoires."), "danger")
            return redirect(url_for("auth.update_profile"))

        # Check whether the email changed
        if email != current_user.email:
            # Check that the email isn't already in use
            existing_user = User.query.filter_by(email=email).first()
            if existing_user and existing_user.id != current_user.id:
                flash(
                    _("Cet email est déjà utilisé par un autre utilisateur."), "danger"
                )
                return redirect(url_for("auth.update_profile"))
            current_user.email = email

        # Update the name
        current_user.name = name

        # Update the password if provided
        if new_password:
            if not current_password:
                flash(
                    _(
                        "Le mot de passe actuel est obligatoire pour changer de mot de passe."
                    ),
                    "danger",
                )
                return redirect(url_for("auth.update_profile"))

            if not current_user.check_password(current_password):
                flash(_("Le mot de passe actuel est incorrect."), "danger")
                return redirect(url_for("auth.update_profile"))

            if new_password != confirm_password:
                flash(_("Les nouveaux mots de passe ne correspondent pas."), "danger")
                return redirect(url_for("auth.update_profile"))

            current_user.set_password(new_password)

        db.session.commit()
        if new_password:
            AuditService.log(
                "profile.password_change",
                resource_type="User",
                resource_id=current_user.id,
            )
        flash(_("Votre profil a été mis à jour avec succès !"), "success")
        return redirect(url_for("auth.profile"))

    return render_template("auth/update_profile.html", user=current_user)


@auth_bp.route("/profile/settings", methods=["GET", "POST"])
@login_required
def profile_settings():
    """Personal settings: timezone preference and per-user notification
    opt-out. Kept separate from update_profile() (name/email/password) -
    a different concern, and the notification section is conditionally
    shown/hidden depending on the org-wide notifications toggle
    (SettingsService.get_notifications_enabled()), which doesn't belong
    mixed into the identity-focused profile form."""
    notifications_enabled_org_wide = SettingsService.get_notifications_enabled()
    apprise_notifications_enabled_org_wide = (
        SettingsService.get_apprise_notifications_enabled()
    )

    if request.method == "POST":
        timezone = request.form.get("timezone", "").strip()

        # Empty means "use the org default" (None); anything else must be
        # a real IANA zone name.
        if timezone and timezone not in available_timezones():
            flash(_("Fuseau horaire invalide."), "danger")
            return redirect(url_for("auth.profile_settings"))
        current_user.timezone = timezone or None

        language = request.form.get("language", "").strip()
        if language and language not in dict(get_language_choices()):
            flash(_("Langue invalide."), "danger")
            return redirect(url_for("auth.profile_settings"))
        current_user.language = language or None

        date_format = request.form.get("date_format", "").strip()
        if date_format and date_format not in dict(get_date_format_choices()):
            flash(_("Format de date invalide."), "danger")
            return redirect(url_for("auth.profile_settings"))
        current_user.date_format = date_format or None

        time_format = request.form.get("time_format", "").strip()
        if time_format and time_format not in dict(get_time_format_choices()):
            flash(_("Format d'heure invalide."), "danger")
            return redirect(url_for("auth.profile_settings"))
        current_user.time_format = time_format or None

        # Only apply the submitted notification checkboxes if the
        # section was actually visible/editable - otherwise a stale
        # form (opened while notifications were org-wide enabled, then
        # submitted after an admin disabled them) could silently flip a
        # preference the user never saw.
        if notifications_enabled_org_wide:
            current_user.shift_notifications_enabled = (
                request.form.get("shift_notifications_enabled") == "on"
            )
            current_user.oncall_notifications_enabled = (
                request.form.get("oncall_notifications_enabled") == "on"
            )

        if apprise_notifications_enabled_org_wide:
            current_user.apprise_shift_notifications_enabled = (
                request.form.get("apprise_shift_notifications_enabled") == "on"
            )
            current_user.apprise_oncall_notifications_enabled = (
                request.form.get("apprise_oncall_notifications_enabled") == "on"
            )

        db.session.commit()
        flash(_("Vos paramètres ont été mis à jour avec succès !"), "success")
        return redirect(url_for("auth.profile_settings"))

    date_formats = get_date_format_choices()
    time_formats = get_time_format_choices()
    default_date_format = SettingsService.get_default_date_format()
    default_time_format = SettingsService.get_default_time_format()

    return render_template(
        "auth/profile_settings.html",
        user=current_user,
        timezones=get_timezone_choices(),
        default_timezone=SettingsService.get_default_timezone(),
        languages=get_language_choices(),
        default_language=SettingsService.get_default_language(),
        date_formats=date_formats,
        default_date_format=default_date_format,
        default_date_format_sample=dict(date_formats).get(
            default_date_format, default_date_format
        ),
        time_formats=time_formats,
        default_time_format=default_time_format,
        default_time_format_sample=dict(time_formats).get(
            default_time_format, default_time_format
        ),
        notifications_enabled_org_wide=notifications_enabled_org_wide,
        apprise_notifications_enabled_org_wide=apprise_notifications_enabled_org_wide,
    )


@auth_bp.route("/profile/ics-token", methods=["GET", "POST"])
@login_required
def generate_ics_token():
    """Generate or regenerate the ICS token for calendar export."""
    if request.method == "POST":
        # Regenerate the token
        token = current_user.generate_ics_token()
        try:
            db.session.commit()
            flash(_("Token ICS régénéré avec succès !"), "success")
        except Exception as e:
            db.session.rollback()
            flash(_("Erreur : %(val0)s", val0=str(e)), "danger")

    # Show the page with the current token
    token = current_user.ics_token

    return render_template("auth/ics_token.html", user=current_user, token=token)
