"""
Settings service for Kairos.

Typed getters/setters for admin-editable, DB-backed application settings
(app/models/setting.py). Fallback rule: if no Setting row exists for a
given key, read the equivalent value live from app.config/env (never a
one-time seed into the DB) - so existing env-var-only deployments keep
working unchanged until an admin explicitly saves a value through
/admin/settings. Once a DB row exists for a key, it always wins.

Error convention mirrors AutomationAdminService: setters return
error_message | None instead of raising.
"""

from zoneinfo import available_timezones

from flask import current_app
from flask_babel import gettext as _

from app import db
from app.config.base import get_bool_from_env, get_int_from_env
from app.models import Setting
from app.services.audit_service import AuditService

DEFAULT_TIMEZONE_KEY = "default_timezone"
DEFAULT_LANGUAGE_KEY = "default_language"
DEFAULT_DATE_FORMAT_KEY = "default_date_format"
DEFAULT_TIME_FORMAT_KEY = "default_time_format"
PUBLIC_BASE_URL_KEY = "public_base_url"
ITEMS_PER_PAGE_KEY = "items_per_page"
MAX_PER_PAGE_KEY = "max_per_page"
NOTIFICATIONS_ENABLED_KEY = "notifications_enabled"
BACKUP_RETENTION_DAYS_KEY = "backup_retention_days"
BACKUP_MAX_BACKUPS_KEY = "backup_max_backups"
AUDIT_LOG_RETENTION_DAYS_KEY = "audit_log_retention_days"
APPRISE_NOTIFICATIONS_ENABLED_KEY = "apprise_notifications_enabled"
# Setting key name, not a secret
ICS_TOKEN_EXPIRY_DAYS_KEY = "ics_token_expiry_days"  # noqa: S105 # nosec B105

FALLBACK_DEFAULT_TIMEZONE = "Europe/Paris"
# Unlike every other FALLBACK_* constant in this module, there is no
# equivalent env var to fall back to here - language was never a
# configurable concept before this Setting existed. This hardcoded "fr"
# is also load-bearing for test stability: it's what keeps every
# existing test's assertions on French response text passing unchanged
# (see app/__init__.py::get_locale(), which falls back here whenever no
# per-request locale can be resolved).
FALLBACK_DEFAULT_LANGUAGE = "fr"
SUPPORTED_LANGUAGES = ("fr", "en")

# Same no-env-var-equivalent situation as language above: date/time
# display format was never a configurable concept before this Setting
# existed. These fallbacks match the format hardcoded everywhere in the
# app before this feature (%d/%m/%Y, %H:%M), so existing tests asserting
# on that exact rendering keep passing unchanged.
FALLBACK_DEFAULT_DATE_FORMAT = "%d/%m/%Y"
FALLBACK_DEFAULT_TIME_FORMAT = "%H:%M"
SUPPORTED_DATE_FORMATS = ("%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d")
SUPPORTED_TIME_FORMATS = ("%H:%M", "%I:%M %p")


class SettingsService:
    """Admin-editable, DB-backed settings with env-var fallback."""

    # --- timezone ---

    @staticmethod
    def get_default_timezone() -> str:
        """Cached on flask.g for the lifetime of the request, same
        pattern/rationale as app/__init__.py's get_date_format()/
        get_time_format(): every shift/on-call converted for the
        calendar (ScheduleService.build_calendar_events, via
        timezone_helpers.py) calls this at least once - without the
        cache, that's a real N+1 (one Setting.get() per shift/on-call
        per render) rather than one query for the whole request. Safe
        to cache: the setting cannot change mid-request."""
        from flask import g, has_request_context

        if not has_request_context():
            value = Setting.get(DEFAULT_TIMEZONE_KEY)
            return str(value) if value else FALLBACK_DEFAULT_TIMEZONE

        if not hasattr(g, "_resolved_default_timezone"):
            value = Setting.get(DEFAULT_TIMEZONE_KEY)
            g._resolved_default_timezone = (
                str(value) if value else FALLBACK_DEFAULT_TIMEZONE
            )

        return g._resolved_default_timezone

    @staticmethod
    def set_default_timezone(tz_name: str) -> str | None:
        if tz_name not in available_timezones():
            return _("Fuseau horaire invalide : %(tz_name)s", tz_name=tz_name)
        try:
            Setting.set(DEFAULT_TIMEZONE_KEY, tz_name)
            AuditService.log(
                "setting.update",
                resource_type="Setting",
                details=f"default_timezone={tz_name}",
            )
            return None
        except Exception as e:
            db.session.rollback()
            return str(e)

    # --- language ---

    @staticmethod
    def get_default_language() -> str:
        value = Setting.get(DEFAULT_LANGUAGE_KEY)
        if value:
            return str(value)
        return FALLBACK_DEFAULT_LANGUAGE

    @staticmethod
    def set_default_language(lang_code: str) -> str | None:
        if lang_code not in SUPPORTED_LANGUAGES:
            return _("Langue invalide : %(lang_code)s", lang_code=lang_code)
        try:
            Setting.set(DEFAULT_LANGUAGE_KEY, lang_code)
            AuditService.log(
                "setting.update",
                resource_type="Setting",
                details=f"default_language={lang_code}",
            )
            return None
        except Exception as e:
            db.session.rollback()
            return str(e)

    # --- date/time format ---

    @staticmethod
    def get_default_date_format() -> str:
        value = Setting.get(DEFAULT_DATE_FORMAT_KEY)
        if value:
            return str(value)
        return FALLBACK_DEFAULT_DATE_FORMAT

    @staticmethod
    def set_default_date_format(date_format: str) -> str | None:
        if date_format not in SUPPORTED_DATE_FORMATS:
            return _(
                "Format de date invalide : %(date_format)s", date_format=date_format
            )
        try:
            Setting.set(DEFAULT_DATE_FORMAT_KEY, date_format)
            AuditService.log(
                "setting.update",
                resource_type="Setting",
                details=f"default_date_format={date_format}",
            )
            return None
        except Exception as e:
            db.session.rollback()
            return str(e)

    @staticmethod
    def get_default_time_format() -> str:
        value = Setting.get(DEFAULT_TIME_FORMAT_KEY)
        if value:
            return str(value)
        return FALLBACK_DEFAULT_TIME_FORMAT

    @staticmethod
    def set_default_time_format(time_format: str) -> str | None:
        if time_format not in SUPPORTED_TIME_FORMATS:
            return _(
                "Format d'heure invalide : %(time_format)s", time_format=time_format
            )
        try:
            Setting.set(DEFAULT_TIME_FORMAT_KEY, time_format)
            AuditService.log(
                "setting.update",
                resource_type="Setting",
                details=f"default_time_format={time_format}",
            )
            return None
        except Exception as e:
            db.session.rollback()
            return str(e)

    # --- public base url ---

    @staticmethod
    def get_public_base_url() -> str | None:
        # value is not None (not `if value:`): a Setting row storing ""
        # means an admin explicitly cleared the override via
        # /admin/settings (see set_public_base_url() below) - that must
        # return None (no override), not silently fall through to the
        # env var. Setting.get() only returns None when no row exists at
        # all, so this correctly distinguishes "never set" from
        # "explicitly cleared", unlike a falsy check which conflated
        # them (bug found in the v1.0 bug hunt).
        value = Setting.get(PUBLIC_BASE_URL_KEY)
        if value is not None:
            return str(value) or None
        return current_app.config.get("PUBLIC_BASE_URL")

    @staticmethod
    def set_public_base_url(url: str | None) -> str | None:
        try:
            Setting.set(PUBLIC_BASE_URL_KEY, url or "")
            AuditService.log(
                "setting.update",
                resource_type="Setting",
                details=f"public_base_url={url}",
            )
            return None
        except Exception as e:
            db.session.rollback()
            return str(e)

    # --- pagination ---

    @staticmethod
    def get_items_per_page() -> int:
        value = Setting.get(ITEMS_PER_PAGE_KEY)
        if value is not None:
            return int(value)
        return int(current_app.config.get("ITEMS_PER_PAGE", 20))

    @staticmethod
    def get_max_per_page() -> int:
        value = Setting.get(MAX_PER_PAGE_KEY)
        if value is not None:
            return int(value)
        return int(current_app.config.get("MAX_PER_PAGE", 100))

    @staticmethod
    def set_pagination(items_per_page: int, max_per_page: int) -> str | None:
        if items_per_page <= 0 or max_per_page <= 0:
            return _("Les valeurs de pagination doivent être positives")
        if items_per_page > max_per_page:
            return _("items_per_page ne peut pas dépasser max_per_page")
        try:
            Setting.set(ITEMS_PER_PAGE_KEY, items_per_page)
            Setting.set(MAX_PER_PAGE_KEY, max_per_page)
            AuditService.log(
                "setting.update",
                resource_type="Setting",
                details=f"items_per_page={items_per_page}, max_per_page={max_per_page}",
            )
            return None
        except Exception as e:
            db.session.rollback()
            return str(e)

    # --- notifications ---

    @staticmethod
    def get_notifications_enabled() -> bool:
        """Falls back to the NOTIFICATIONS_ENABLED env var (not part of
        app.config - only scripts/notification_config.py reads it today)
        when no DB override exists."""
        value = Setting.get(NOTIFICATIONS_ENABLED_KEY)
        if value is not None:
            return bool(value)
        return get_bool_from_env("NOTIFICATIONS_ENABLED", False)

    @staticmethod
    def set_notifications_enabled(enabled: bool) -> str | None:
        try:
            Setting.set(NOTIFICATIONS_ENABLED_KEY, bool(enabled))
            AuditService.log(
                "setting.update",
                resource_type="Setting",
                details=f"notifications_enabled={enabled}",
            )
            return None
        except Exception as e:
            db.session.rollback()
            return str(e)

    # --- backups ---

    @staticmethod
    def get_backup_retention_days() -> int | None:
        """Returns None if no DB override exists - callers should fall
        back to BackupConfig.from_env() in that case."""
        value = Setting.get(BACKUP_RETENTION_DAYS_KEY)
        return int(value) if value is not None else None

    @staticmethod
    def get_backup_max_backups() -> int | None:
        """Returns None if no DB override exists - see get_backup_retention_days."""
        value = Setting.get(BACKUP_MAX_BACKUPS_KEY)
        return int(value) if value is not None else None

    @staticmethod
    def set_backup_retention(retention_days: int, max_backups: int) -> str | None:
        if retention_days <= 0 or max_backups <= 0:
            return _("Les valeurs de rétention doivent être positives")
        try:
            Setting.set(BACKUP_RETENTION_DAYS_KEY, retention_days)
            Setting.set(BACKUP_MAX_BACKUPS_KEY, max_backups)
            AuditService.log(
                "setting.update",
                resource_type="Setting",
                details=f"backup_retention_days={retention_days}, backup_max_backups={max_backups}",
            )
            return None
        except Exception as e:
            db.session.rollback()
            return str(e)

    # --- audit log retention ---

    @staticmethod
    def get_audit_log_retention_days() -> int | None:
        """Returns None if no DB override exists - callers should keep
        every AuditLog entry (no purge) in that case, unlike
        get_backup_retention_days() there is no env-var fallback: audit
        log retention was never configurable before this Setting
        existed, and defaulting to "purge something" without an admin
        explicitly opting in would be surprising for an audit trail."""
        value = Setting.get(AUDIT_LOG_RETENTION_DAYS_KEY)
        return int(value) if value is not None else None

    @staticmethod
    def set_audit_log_retention_days(days: int) -> str | None:
        if days <= 0:
            return _("La durée de rétention doit être positive")
        try:
            Setting.set(AUDIT_LOG_RETENTION_DAYS_KEY, days)
            AuditService.log(
                "setting.update",
                resource_type="Setting",
                details=f"audit_log_retention_days={days}",
            )
            return None
        except Exception as e:
            db.session.rollback()
            return str(e)

    # --- Apprise external notifications master toggle ---

    @staticmethod
    def get_apprise_notifications_enabled() -> bool:
        """No env var fallback - a brand new concept, never configurable
        before this Setting existed (same footnote as default_language/
        audit_log_retention_days). Defaults to False (opt-in): an admin
        must explicitly enable outbound network calls to external
        services, they should never start firing silently the moment
        this feature ships."""
        value = Setting.get(APPRISE_NOTIFICATIONS_ENABLED_KEY)
        return bool(value) if value is not None else False

    @staticmethod
    def set_apprise_notifications_enabled(enabled: bool) -> str | None:
        try:
            Setting.set(APPRISE_NOTIFICATIONS_ENABLED_KEY, bool(enabled))
            AuditService.log(
                "setting.update",
                resource_type="Setting",
                details=f"apprise_notifications_enabled={enabled}",
            )
            return None
        except Exception as e:
            db.session.rollback()
            return str(e)

    # --- ICS token expiry ---

    @staticmethod
    def get_ics_token_expiry_days() -> int:
        """Falls back to the ICS_TOKEN_EXPIRY_DAYS env var (documented in
        .env.example, not part of app.config) when no DB override exists.
        Enforced by User.is_ics_token_expired(), checked from
        ExportService.resolve_user()."""
        value = Setting.get(ICS_TOKEN_EXPIRY_DAYS_KEY)
        if value is not None:
            return int(value)
        return get_int_from_env("ICS_TOKEN_EXPIRY_DAYS", 365)

    @staticmethod
    def set_ics_token_expiry_days(days: int) -> str | None:
        if days <= 0:
            return _("La durée d'expiration doit être positive")
        try:
            Setting.set(ICS_TOKEN_EXPIRY_DAYS_KEY, days)
            AuditService.log(
                "setting.update",
                resource_type="Setting",
                details=f"ics_token_expiry_days={days}",
            )
            return None
        except Exception as e:
            db.session.rollback()
            return str(e)
