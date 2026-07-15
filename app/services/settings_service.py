"""
Settings service for Leviia Schedule.

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

from app import db
from app.config.base import get_bool_from_env, get_int_from_env
from app.models import Setting

DEFAULT_TIMEZONE_KEY = "default_timezone"
DEFAULT_LANGUAGE_KEY = "default_language"
PUBLIC_BASE_URL_KEY = "public_base_url"
ITEMS_PER_PAGE_KEY = "items_per_page"
MAX_PER_PAGE_KEY = "max_per_page"
NOTIFICATIONS_ENABLED_KEY = "notifications_enabled"
BACKUP_RETENTION_DAYS_KEY = "backup_retention_days"
BACKUP_MAX_BACKUPS_KEY = "backup_max_backups"
# Setting key name, not a secret
ICS_TOKEN_EXPIRY_DAYS_KEY = "ics_token_expiry_days"  # noqa: S105

FALLBACK_DEFAULT_TIMEZONE = "Europe/Paris"
# Unlike every other FALLBACK_* constant in this module, there is no
# equivalent env var to fall back to here - language was never a
# configurable concept before this Setting existed. This hardcoded "fr"
# is also load-bearing for test stability: it's what keeps every
# existing test's assertions on French response text passing unchanged
# (see app/__init__.py::get_locale() and CLAUDE.md's i18n section).
FALLBACK_DEFAULT_LANGUAGE = "fr"
SUPPORTED_LANGUAGES = ("fr", "en")


class SettingsService:
    """Admin-editable, DB-backed settings with env-var fallback."""

    # --- timezone ---

    @staticmethod
    def get_default_timezone() -> str:
        value = Setting.get(DEFAULT_TIMEZONE_KEY)
        if value:
            return str(value)
        return FALLBACK_DEFAULT_TIMEZONE

    @staticmethod
    def set_default_timezone(tz_name: str) -> str | None:
        if tz_name not in available_timezones():
            return f"Fuseau horaire invalide : {tz_name}"
        try:
            Setting.set(DEFAULT_TIMEZONE_KEY, tz_name)
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
            return f"Langue invalide : {lang_code}"
        try:
            Setting.set(DEFAULT_LANGUAGE_KEY, lang_code)
            return None
        except Exception as e:
            db.session.rollback()
            return str(e)

    # --- public base url ---

    @staticmethod
    def get_public_base_url() -> str | None:
        value = Setting.get(PUBLIC_BASE_URL_KEY)
        if value:
            return str(value)
        return current_app.config.get("PUBLIC_BASE_URL")

    @staticmethod
    def set_public_base_url(url: str | None) -> str | None:
        try:
            Setting.set(PUBLIC_BASE_URL_KEY, url or "")
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
            return "Les valeurs de pagination doivent être positives"
        if items_per_page > max_per_page:
            return "items_per_page ne peut pas dépasser max_per_page"
        try:
            Setting.set(ITEMS_PER_PAGE_KEY, items_per_page)
            Setting.set(MAX_PER_PAGE_KEY, max_per_page)
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
            return "Les valeurs de rétention doivent être positives"
        try:
            Setting.set(BACKUP_RETENTION_DAYS_KEY, retention_days)
            Setting.set(BACKUP_MAX_BACKUPS_KEY, max_backups)
            return None
        except Exception as e:
            db.session.rollback()
            return str(e)

    # --- ICS token expiry (currently unenforced, see CLAUDE.md) ---

    @staticmethod
    def get_ics_token_expiry_days() -> int:
        """Falls back to the ICS_TOKEN_EXPIRY_DAYS env var (documented in
        .env.example, not part of app.config) when no DB override exists.
        No enforcement point reads this value yet - see CLAUDE.md."""
        value = Setting.get(ICS_TOKEN_EXPIRY_DAYS_KEY)
        if value is not None:
            return int(value)
        return get_int_from_env("ICS_TOKEN_EXPIRY_DAYS", 365)

    @staticmethod
    def set_ics_token_expiry_days(days: int) -> str | None:
        if days <= 0:
            return "La durée d'expiration doit être positive"
        try:
            Setting.set(ICS_TOKEN_EXPIRY_DAYS_KEY, days)
            return None
        except Exception as e:
            db.session.rollback()
            return str(e)
