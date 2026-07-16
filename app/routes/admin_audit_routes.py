"""
Admin route for the "Historique des modifications" (audit trail)
consultation page. Registered on admin_bp (see app/routes/admin.py).
Read-only list + a single purge action - AuditLog rows themselves are
only ever written by AuditService.log() (see app/services/audit_service.py),
never directly from a route.
"""

from datetime import datetime, timedelta

from flask import flash, redirect, render_template, request, url_for
from flask_babel import gettext as _

from app import db
from app.auth.decorators import admin_required
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.user_repository import UserRepository
from app.routes.admin import admin_bp
from app.services import SettingsService

# Domain prefixes in use across AuditService.log() call sites - see
# CLAUDE.md's "Audit trail" section for the full "<domain>.<verb>" naming
# convention. Kept here as a plain list (not derived at runtime) since
# it only drives the filter dropdown, not validation.
ACTION_DOMAINS = [
    "auth",
    "group",
    "leave",
    "oncall",
    "profile",
    "setting",
    "shift",
    "shift_type",
    "swap",
    "user",
]


@admin_bp.route("/admin/audit-log")
@admin_required
def audit_log():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    per_page_options = [20, 50, 100]
    if per_page not in per_page_options:
        per_page = 20

    actor_id = request.args.get("actor_id", type=int)
    action_domain = request.args.get("action_domain", "").strip()
    action_prefix = f"{action_domain}." if action_domain in ACTION_DOMAINS else None

    date_from_str = request.args.get("date_from", "").strip()
    date_to_str = request.args.get("date_to", "").strip()
    date_from = None
    date_to = None
    try:
        if date_from_str:
            date_from = datetime.strptime(date_from_str, "%Y-%m-%d").date()
        if date_to_str:
            date_to = datetime.strptime(date_to_str, "%Y-%m-%d").date()
    except ValueError:
        flash(_("Date invalide."), "danger")
        date_from_str = ""
        date_to_str = ""

    entries_paginated = AuditLogRepository.list_paginated(
        page=page,
        per_page=per_page,
        actor_id=actor_id,
        action_prefix=action_prefix,
        date_from=date_from,
        date_to=date_to,
    )

    return render_template(
        "admin/audit_log.html",
        entries=entries_paginated,
        per_page=per_page,
        per_page_options=per_page_options,
        users=UserRepository.get_all(),
        action_domains=ACTION_DOMAINS,
        selected_actor_id=actor_id,
        selected_action_domain=action_domain,
        date_from=date_from_str,
        date_to=date_to_str,
        audit_log_retention_days=SettingsService.get_audit_log_retention_days(),
    )


@admin_bp.route("/admin/audit-log/purge", methods=["POST"])
@admin_required
def purge_audit_log():
    retention_days = SettingsService.get_audit_log_retention_days()
    if retention_days is None:
        flash(
            _(
                "Aucune durée de rétention n'est configurée : réglez-la d'abord "
                "dans les paramètres pour pouvoir purger l'historique."
            ),
            "danger",
        )
        return redirect(url_for("admin.audit_log"))

    cutoff = datetime.utcnow() - timedelta(days=retention_days)
    count = AuditLogRepository.delete_older_than(cutoff)
    db.session.commit()
    flash(
        _("%(count)s entrée(s) d'historique purgée(s).", count=count),
        "success",
    )
    return redirect(url_for("admin.audit_log"))
