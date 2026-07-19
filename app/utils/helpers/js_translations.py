"""
Server-side translations for the handful of user-facing strings that
are hardcoded directly in JS files (aria-labels, confirm() dialogs) -
most JS-adjacent user-facing text (onclick="confirm('...')" attributes)
lives directly in Jinja templates instead and is translated there via
the normal {{ _('...') }} mechanism.

Injected into every page via base.html's #i18n-strings JSON script tag
(app/__init__.py::inject_js_translations) and read at runtime by
app/static/js/utils/i18n.js::getString(key).
"""

from flask_babel import gettext as _


def get_js_translations() -> dict[str, str]:
    return {
        "edit_mode_on": _("Mode édition activé"),
        "edit_mode_off": _("Mode édition désactivé"),
        "disable_edit_mode": _("Désactiver le mode édition"),
        "enable_edit_mode": _("Activer le mode édition"),
        "disable_edit_mode_short": _("Désactiver l'édition"),
        "enable_edit_mode_short": _("Activer l'édition"),
        "hide_tips": _("Cacher les conseils"),
        "show_tips": _("Afficher les conseils"),
        "hide_tips_short": _("Cacher conseils"),
        "show_tips_short": _("Afficher conseils"),
        "close": _("Fermer"),
        "cancel": _("Annuler"),
        "create_shift": _("Créer le shift"),
        "confirm_delete_shift": _("Voulez-vous supprimer ce shift ?"),
        "confirm_delete_oncall": _("Voulez-vous supprimer cette astreinte ?"),
        "confirm_delete_leave": _("Voulez-vous supprimer ce congé ?"),
        "unnamed_field": _("Champ non nommé"),
        "field_required": _("Le champ %(field)s est obligatoire."),
        "data_table": _("Tableau de données"),
        "confirmation_title": _("Confirmation"),
        "confirm": _("Confirmer"),
        "are_you_sure": _("Êtes-vous sûr ?"),
        "create_new_shift_title": _("Créer un nouveau shift"),
        "start_datetime": _("Date et heure de début"),
        "end_datetime": _("Date et heure de fin"),
        "user": _("Utilisateur"),
        "select_user": _("Sélectionnez un utilisateur"),
        "shift_type": _("Type de shift"),
        "select_shift_type": _("Sélectionnez un type de shift"),
        "create": _("Créer"),
        "rebalance_warning": _(
            "Événement mis à jour, mais le rééquilibrage automatique des shifts a échoué."
        ),
        "error_prefix": _("Erreur: "),
        "update_error": _("Une erreur est survenue lors de la mise à jour."),
        "resize_error": _("Une erreur est survenue lors du redimensionnement."),
        "event_deleted": _("Événement supprimé avec succès."),
        "delete_error": _("Une erreur est survenue lors de la suppression."),
        "delete_cancelled": _("Suppression annulée."),
        "weekend_restriction": _(
            "Les shifts ne peuvent pas être créés ou déplacés vers les week-ends "
            "(samedi/dimanche)."
        ),
        "shift_creation_cancelled": _("Création de shift annulée."),
        "fill_required_fields": _("Veuillez remplir tous les champs obligatoires."),
        "shift_created": _("Shift créé avec succès."),
        "shift_creation_error": _(
            "Une erreur est survenue lors de la création du shift."
        ),
        "data_load_error": _("Une erreur est survenue lors du chargement des données."),
        "dark_theme_enabled": _("Thème sombre activé"),
        "light_theme_enabled": _("Thème clair activé"),
        "copied": _("Copié !"),
    }
