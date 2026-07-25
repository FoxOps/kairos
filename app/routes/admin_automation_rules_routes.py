"""
Admin route for the configurable automation rules engine
(app/models/automation_rule.py, app/utils/automation/rules/).
Registered on admin_bp (see app/routes/admin.py). Separate from
admin_automation_routes.py, which owns rotation order + the
generate/refresh actions - this page only edits rule parameters.

Each rule-type form section posts independently (a `section` hidden
field selects which AutomationRuleAdminService.save_*() runs), same
pattern as admin_settings_routes.py. A `group_id` selector (query
param on GET, hidden field on every rule-type POST) switches which
scope is being edited: blank/absent means the organization-wide
default, a Group's id means that Group's own override - see
AutomationRuleAdminService's module docstring for when an override
actually takes effect. The two scheduling-mode sections
(shift_scheduling_mode/oncall_scheduling_mode) are deliberately NOT
scoped by group_id - they're the org-wide switch that decides whether
per-Group overrides get looked up at all, so a "per-Group override of
the mode toggle itself" wouldn't be meaningful.
"""

from flask import flash, redirect, render_template, request, url_for
from flask_babel import gettext as _

from app.auth.decorators import admin_required
from app.models import Group
from app.repositories.user_repository import GroupRepository
from app.routes.admin import admin_bp
from app.services import AutomationRuleAdminService, SettingsService
from app.services.shift_type_service import ShiftTypeService
from app.utils.automation.rules import (
    MandatoryShiftRule,
    OnCallAnchorRule,
    OnCallShiftOverlapRule,
    OnCallSpacingRule,
    RestAfterOnCallRule,
    ShiftSlotsRule,
    StaffingLimitsRule,
    WeekendDefinitionRule,
)

WEEKDAY_LABELS = [
    _("Lundi"),
    _("Mardi"),
    _("Mercredi"),
    _("Jeudi"),
    _("Vendredi"),
    _("Samedi"),
    _("Dimanche"),
]


def _parse_int(value: str) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _flash_result(error: str | None, success_message: str) -> None:
    if error:
        flash(_("Erreur : %(error)s", error=error), "danger")
    else:
        flash(success_message, "success")


def _resolve_group(group_id_raw: str | None) -> Group | None:
    group_id = _parse_int(group_id_raw) if group_id_raw else None
    return GroupRepository.get_by_id(group_id) if group_id is not None else None


@admin_bp.route("/admin/automation/rules", methods=["GET", "POST"])
@admin_required
def automation_rules_dashboard():
    if request.method == "POST":
        section = request.form.get("section")
        group = _resolve_group(request.form.get("group_id"))

        if section == "shift_slots":
            oncall_id = _parse_int(request.form.get("oncall_shift_type_id", ""))
            rotation_id = _parse_int(request.form.get("rotation_shift_type_id", ""))
            default_id = _parse_int(request.form.get("default_shift_type_id", ""))
            if None in (oncall_id, rotation_id, default_id):
                flash(_("Erreur : sélection de créneau invalide"), "danger")
            else:
                error = AutomationRuleAdminService.save_shift_slots(
                    oncall_id, rotation_id, default_id, group=group
                )
                _flash_result(error, _("Créneaux de shift enregistrés"))

        elif section == "weekend_definition":
            days = [_parse_int(d) for d in request.form.getlist("weekend_days")]
            if None in days:
                flash(_("Erreur : jour invalide"), "danger")
            else:
                error = AutomationRuleAdminService.save_weekend_definition(
                    days, group=group
                )
                _flash_result(error, _("Définition du week-end enregistrée"))

        elif section == "oncall_spacing":
            weeks = _parse_int(request.form.get("min_spacing_weeks", ""))
            if weeks is None:
                flash(_("Erreur : valeur invalide"), "danger")
            else:
                error = AutomationRuleAdminService.save_oncall_spacing(
                    weeks, group=group
                )
                _flash_result(error, _("Espacement des astreintes enregistré"))

        elif section == "oncall_anchor":
            weekday = _parse_int(request.form.get("weekday", ""))
            start_hour = _parse_int(request.form.get("start_hour", ""))
            end_hour = _parse_int(request.form.get("end_hour", ""))
            if None in (weekday, start_hour, end_hour):
                flash(_("Erreur : valeur invalide"), "danger")
            else:
                error = AutomationRuleAdminService.save_oncall_anchor(
                    weekday, start_hour, end_hour, group=group
                )
                _flash_result(error, _("Ancrage de la semaine d'astreinte enregistré"))

        elif section == "staffing_limits":
            limits = {}
            for shift_type in ShiftTypeService.list_all():
                min_value = _parse_int(request.form.get(f"min_{shift_type.id}", ""))
                max_value = _parse_int(request.form.get(f"max_{shift_type.id}", ""))
                if min_value is not None or max_value is not None:
                    limits[shift_type.id] = (min_value, max_value)
            error = AutomationRuleAdminService.save_staffing_limits(limits, group=group)
            _flash_result(error, _("Effectifs enregistrés"))

        elif section == "mandatory_shift":
            ids = [
                _parse_int(i) for i in request.form.getlist("mandatory_shift_type_ids")
            ]
            if None in ids:
                flash(_("Erreur : sélection invalide"), "danger")
            else:
                error = AutomationRuleAdminService.save_mandatory_shift(
                    ids, group=group
                )
                _flash_result(error, _("Créneaux obligatoires enregistrés"))

        elif section == "rest_after_oncall":
            hours = _parse_int(request.form.get("min_rest_hours", ""))
            if hours is None:
                flash(_("Erreur : valeur invalide"), "danger")
            else:
                error = AutomationRuleAdminService.save_rest_after_oncall(
                    hours, group=group
                )
                _flash_result(error, _("Repos après astreinte enregistré"))

        elif section == "oncall_shift_overlap":
            block = request.form.get("block") == "on"
            error = AutomationRuleAdminService.save_oncall_shift_overlap(
                block, group=group
            )
            _flash_result(error, _("Règle de chevauchement enregistrée"))

        elif section == "shift_scheduling_mode":
            mode = request.form.get("shift_scheduling_mode", "")
            error = SettingsService.set_shift_scheduling_mode(mode)
            _flash_result(error, _("Mode de planification des shifts enregistré"))

        elif section == "oncall_scheduling_mode":
            mode = request.form.get("oncall_scheduling_mode", "")
            error = SettingsService.set_oncall_scheduling_mode(mode)
            _flash_result(error, _("Mode de planification des astreintes enregistré"))

        return redirect(
            url_for(
                "admin.automation_rules_dashboard",
                group_id=group.id if group is not None else None,
            )
        )

    group = _resolve_group(request.args.get("group_id"))
    groups = GroupRepository.get_all()
    shift_types = ShiftTypeService.list_all()
    weekday_choices = list(enumerate(WEEKDAY_LABELS))
    staffing_limits = {
        shift_type.id: StaffingLimitsRule.get_limits(shift_type.id, group=group)
        for shift_type in shift_types
    }

    return render_template(
        "admin/automation/rules.html",
        groups=groups,
        selected_group=group,
        shift_types=shift_types,
        weekday_choices=weekday_choices,
        shift_slots=ShiftSlotsRule.resolve(group=group),
        weekend_definition=WeekendDefinitionRule.resolve(group=group),
        oncall_spacing=OnCallSpacingRule.resolve(group=group),
        oncall_anchor=OnCallAnchorRule.resolve(group=group),
        staffing_limits=staffing_limits,
        mandatory_shift=MandatoryShiftRule.resolve(group=group),
        rest_after_oncall=RestAfterOnCallRule.resolve(group=group),
        oncall_shift_overlap=OnCallShiftOverlapRule.resolve(group=group),
        shift_scheduling_mode=SettingsService.get_shift_scheduling_mode(),
        oncall_scheduling_mode=SettingsService.get_oncall_scheduling_mode(),
    )
