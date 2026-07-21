"""
Admin routes for automation (on-calls/shifts). Registered on admin_bp
(see app/routes/admin.py).
"""

import re
from datetime import date, datetime, timedelta

from flask import flash, redirect, render_template, request, url_for
from flask_babel import gettext as _

from app import db
from app.auth.decorators import admin_required
from app.models import AutomationConfig
from app.repositories.oncall_repository import OnCallRepository
from app.repositories.shift_repository import ShiftRepository
from app.routes.admin import admin_bp
from app.services import (
    AppNotificationService,
    AppriseNotificationService,
    AutomationAdminService,
)
from app.utils.automation import (
    AdvancedShiftAutomation,
    OnCallAutomation,
    get_automation_status,
)

# app/utils/automation/ (AdvancedShiftAutomation/OnCallAutomation) encodes
# each generated message's severity as a leading emoji rather than a
# separate field. Detect the category from it here, then strip the emoji
# before display - Font Awesome icons, not emoji, are this project's icon
# convention (see base.html's flash rendering, which already prepends a
# category icon; keeping the emoji too would show it twice).
_EMOJI_PREFIX_RE = re.compile(r"^[\U0001F300-\U0001FAFF☀-➿️]+\s*")


def _classify_automation_message(
    msg: str, default_category: str = "info"
) -> tuple[str, str]:
    """Returns (category, message with its leading emoji stripped)."""
    if "✅" in msg or "🎉" in msg:
        category = "success"
    elif "⚠️" in msg:
        category = "warning"
    elif default_category == "info":
        category = "info"
    else:
        category = "danger"
    return category, _EMOJI_PREFIX_RE.sub("", msg)


def _flash_automation_messages(messages, default_category="info"):
    for msg in messages:
        category, stripped_msg = _classify_automation_message(msg, default_category)
        flash(stripped_msg, category)


def _notify_oncall_gap_if_any(unfilled_dates):
    if not unfilled_dates:
        return
    AppNotificationService.notify_admins_oncall_gap(unfilled_dates)
    AppriseNotificationService.notify(
        "system",
        _("Génération d'astreintes incomplète"),
        _(
            "Aucun utilisateur disponible dans le respect du "
            "délai légal de 2 semaines pour : %(dates)s. "
            "Assignation manuelle nécessaire dans "
            "/admin/automation.",
            dates=", ".join(d.strftime("%d/%m/%Y") for d in unfilled_dates),
        ),
    )


def _notify_shift_unfilled_if_any(unfilled_dates):
    if not unfilled_dates:
        return
    AppNotificationService.notify_admins_shift_unfilled(unfilled_dates)
    AppriseNotificationService.notify(
        "system",
        _("Génération de shifts incomplète"),
        _(
            "Aucun utilisateur disponible pour générer un shift pour : "
            "%(dates)s. Assignation manuelle nécessaire dans "
            "/admin/automation.",
            dates=", ".join(d.strftime("%d/%m/%Y") for d in unfilled_dates),
        ),
    )


@admin_bp.route("/admin/automation")
@admin_required
def automation_dashboard():
    """Automation dashboard."""
    status = get_automation_status()
    oncall_gaps = OnCallAutomation.detect_oncall_gaps()

    return render_template(
        "admin/automation/dashboard.html",
        status=status,
        oncall_gaps=oncall_gaps,
    )


@admin_bp.route("/admin/automation/full", methods=["GET", "POST"])
@admin_required
def automation_full():
    """Single-page automation UI: full generation (on-calls + shifts,
    "generate"/"dry_run"/"save_order" actions) and shifts-only refresh
    ("refresh_shifts" action) sit as buttons on the same form, sharing
    one date range. Used to be two separate pages/routes
    (automation_full + the now-removed refresh_shifts), which user
    feedback flagged as confusing (unclear which page to use, easy to
    forget the other one exists) - an intermediate design put the two
    modes on two tabs of this same page, but user feedback on that too
    was that it should just be one more button next to "Dry Run",
    no tabs.

    refresh_shifts recomputes shifts from whatever on-calls exist,
    optionally also touching the on-calls themselves first depending
    on oncall_mode (form field, default "none" - left to the admin's
    judgment, not a single fixed choice):
    - "none": on-calls are left completely untouched (the original
      behaviour) - shifts are recomputed from whatever on-calls already
      exist, even manually modified ones.
    - "fill_gaps": before recomputing shifts, fills any Friday in the
      period that has no on-call at all (OnCallAutomation.
      fill_oncall_gaps) - existing on-calls, including manually
      assigned ones, are never touched or reassigned, only genuinely
      empty weeks get a new one.
    - "regenerate": deletes and fully regenerates on-calls for the
      period (like the "generate" action above) before recomputing
      shifts - overwrites manual on-call edits.
    """
    if request.method == "POST":
        action = request.form.get("action")

        if action == "refresh_shifts":
            start_date_str = request.form.get("start_date")
            end_date_str = request.form.get("end_date")
            oncall_mode = request.form.get("oncall_mode", "none")

            try:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()

                if oncall_mode == "fill_gaps":
                    _filled, oncall_messages, oncall_unfilled_dates = (
                        OnCallAutomation.fill_oncall_gaps(
                            start_date,
                            end_date,
                            rotation_order_ids=AutomationConfig.get_rotation_order(),
                            dry_run=False,
                        )
                    )
                    _flash_automation_messages(oncall_messages, default_category="info")
                    _notify_oncall_gap_if_any(oncall_unfilled_dates)
                elif oncall_mode == "regenerate":
                    oncalls_deleted = OnCallRepository.delete_overlapping_range(
                        start_date, end_date
                    )
                    if oncalls_deleted:
                        db.session.commit()
                        flash(
                            _(
                                "%(oncalls_deleted)s astreintes existantes supprimées pour la période",
                                oncalls_deleted=oncalls_deleted,
                            ),
                            "info",
                        )
                    _regenerated, oncall_messages, oncall_unfilled_dates = (
                        OnCallAutomation.generate_oncall_schedule(
                            start_date,
                            end_date,
                            rotation_order_ids=AutomationConfig.get_rotation_order(),
                            dry_run=False,
                        )
                    )
                    _flash_automation_messages(
                        oncall_messages, default_category="danger"
                    )
                    _notify_oncall_gap_if_any(oncall_unfilled_dates)

                # Only deletes shifts (never on-calls beyond what
                # oncall_mode above already handled): this recomputes
                # shifts, taking whatever on-calls now exist into
                # account.
                deleted = ShiftRepository.delete_in_date_range(start_date, end_date)
                if deleted:
                    db.session.commit()
                    flash(
                        _(
                            "%(deleted)s shifts existants supprimés pour la période",
                            deleted=deleted,
                        ),
                        "info",
                    )

                shifts, messages, shift_unfilled_dates = (
                    AdvancedShiftAutomation.generate_full_schedule(
                        start_date, end_date, dry_run=False
                    )
                )

                _flash_automation_messages(messages, default_category="info")
                _notify_shift_unfilled_if_any(shift_unfilled_dates)

                flash(
                    _("%(val0)s shifts régénérés avec succès !", val0=len(shifts)),
                    "success",
                )
            except ValueError as e:
                flash(_("Format de date invalide : %(val0)s", val0=str(e)), "danger")
            except Exception as e:
                db.session.rollback()
                flash(_("Erreur : %(val0)s", val0=str(e)), "danger")
            return redirect(url_for("admin.automation_full", mode="refresh"))

        if action in ["generate", "dry_run", "save_order"]:
            start_date_str = request.form.get("start_date")
            end_date_str = request.form.get("end_date")

            rotation_order_ids = AutomationAdminService.parse_rotation_order_from_form(
                request.form
            )

            if action == "save_order":
                error = AutomationAdminService.save_rotation_order(rotation_order_ids)
                if error:
                    flash(
                        _(
                            "Erreur lors de la sauvegarde de l'ordre : %(error)s",
                            error=error,
                        ),
                        "danger",
                    )
                else:
                    flash(
                        _(
                            "Ordre de rotation enregistré ! Utilisez le bouton 'Générer' pour appliquer."
                        ),
                        "success",
                    )
                return redirect(url_for("admin.automation_full"))

            try:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()

                dry_run = action == "dry_run"

                if not dry_run:
                    oncalls_deleted, shifts_deleted = (
                        AutomationAdminService.clear_period(start_date, end_date)
                    )
                    if oncalls_deleted:
                        flash(
                            _(
                                "%(oncalls_deleted)s astreintes existantes supprimées pour la période",
                                oncalls_deleted=oncalls_deleted,
                            ),
                            "info",
                        )
                    if shifts_deleted:
                        flash(
                            _(
                                "%(shifts_deleted)s shifts existants supprimés pour la période",
                                shifts_deleted=shifts_deleted,
                            ),
                            "info",
                        )

                oncalls, oncall_messages, oncall_unfilled_dates = (
                    OnCallAutomation.generate_oncall_schedule(
                        start_date, end_date, rotation_order_ids, dry_run=dry_run
                    )
                )

                if dry_run:
                    # Note: the shift preview is based on the on-calls
                    # already in the database for the period (the on-call
                    # dry_run above doesn't save anything) - it can
                    # therefore differ from the final result if no
                    # on-call exists yet for this period.
                    shifts, shift_messages, _shift_unfilled_dates = (
                        AdvancedShiftAutomation.generate_full_schedule(
                            start_date, end_date, dry_run=True
                        )
                    )
                    return render_template(
                        "admin/automation/full_dry_run.html",
                        result={
                            "oncall": {
                                "generated": oncalls,
                                "messages": [
                                    _classify_automation_message(m, "danger")
                                    for m in oncall_messages
                                ],
                            },
                            "shift": {
                                "generated": shifts,
                                "messages": [
                                    _classify_automation_message(m, "info")
                                    for m in shift_messages
                                ],
                            },
                        },
                        start_date=start_date,
                        end_date=end_date,
                        rotation_order_ids=rotation_order_ids,
                    )
                else:
                    shifts, shift_messages, shift_unfilled_dates = (
                        AdvancedShiftAutomation.generate_full_schedule(
                            start_date, end_date, dry_run=False
                        )
                    )

                    _flash_automation_messages(
                        oncall_messages, default_category="danger"
                    )
                    _flash_automation_messages(shift_messages, default_category="info")

                    _notify_oncall_gap_if_any(oncall_unfilled_dates)
                    _notify_shift_unfilled_if_any(shift_unfilled_dates)

                    flash(
                        _(
                            "Régénération complète terminée pour la période du %(strftime)s au %(strftime1)s",
                            strftime=start_date.strftime("%d/%m/%Y"),
                            strftime1=end_date.strftime("%d/%m/%Y"),
                        ),
                        "success",
                    )
                    return redirect(url_for("admin.automation_full"))

            except ValueError as e:
                flash(_("Format de date invalide : %(val0)s", val0=str(e)), "danger")
            except Exception as e:
                flash(_("Erreur : %(val0)s", val0=str(e)), "danger")

    oncall_users = OnCallAutomation.get_eligible_users()
    current_rotation_order = AutomationAdminService.get_rotation_order()

    today = date.today()
    end_date_default = today + timedelta(days=180)
    start_date_default = today
    while start_date_default.weekday() != 4:
        start_date_default += timedelta(days=1)

    # Allows deep-linking straight to a detected gap (see the dashboard's
    # "astreintes manquantes" alert, admin.automation_dashboard) instead
    # of the admin having to manually widen the Période fields to reach
    # a gap that predates today - the point of confusion that motivated
    # detect_oncall_gaps() in the first place.
    prefill_start = request.args.get("start_date")
    prefill_end = request.args.get("end_date")
    if prefill_start:
        try:
            start_date_default = datetime.strptime(prefill_start, "%Y-%m-%d").date()
        except ValueError:
            pass
    if prefill_end:
        try:
            end_date_default = datetime.strptime(prefill_end, "%Y-%m-%d").date()
        except ValueError:
            pass
    prefill_oncall_mode = request.args.get("oncall_mode", "none")

    return render_template(
        "admin/automation/full.html",
        oncall_users=oncall_users,
        start_date_default=start_date_default,
        end_date_default=end_date_default,
        current_rotation_order=current_rotation_order,
        prefill_oncall_mode=prefill_oncall_mode,
    )
