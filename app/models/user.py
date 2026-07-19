"""
User and Group models for Kairos.

This module contains the User and Group models for user management
and authentication.
"""

import json
import secrets

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app import db
from app.models.base import BaseModel, _utcnow


class Group(BaseModel):
    """
    Group model for organizing users.

    Attributes:
        name: Unique name of the group
        is_part_of_schedule: Whether group members are included in shift scheduling
        is_part_of_oncall: Whether group members are included in on-call rotations
        users: Relationship to User model
    """

    __tablename__ = "groups"

    name = db.Column(db.String(80), nullable=False, unique=True)
    is_part_of_schedule = db.Column(db.Boolean, default=False)
    is_part_of_oncall = db.Column(db.Boolean, default=False)

    # Relationships
    users = db.relationship(
        "User", backref="group", lazy=True, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Group {self.name} (id={self.id})>"


class User(BaseModel, UserMixin):
    """
    User model for authentication and user management.

    Attributes:
        name: User's full name
        email: Unique email address
        password_hash: Hashed password
        is_admin: Whether the user has administrator privileges
        group_id: Foreign key to Group
        ics_token: Unique token for ICS export
        ics_token_created_at: When ics_token was (re)generated - used to
            compute expiry against SettingsService.get_ics_token_expiry_days()
        timezone: Optional personal IANA timezone (e.g. "Europe/Paris"); None
            means "use the organization's default_timezone setting"
        language: Optional personal UI language ("fr"/"en"); None means
            "use the organization's default_language setting"
        date_format: Optional personal date display format (a strftime
            pattern, e.g. "%d/%m/%Y"); None means "use the organization's
            default_date_format setting"
        time_format: Optional personal time display format (a strftime
            pattern, e.g. "%H:%M"); None means "use the organization's
            default_time_format setting"
        shift_notifications_enabled: Opt-out for the weekly shift reminder
            email (only takes effect if notifications are enabled org-wide,
            see SettingsService.get_notifications_enabled())
        oncall_notifications_enabled: Opt-out for the weekly on-call
            reminder email (same org-wide gate as above)
        apprise_shift_target_ids: JSON-encoded list of NotificationTarget
            ids the user picked to relay their weekly shift reminder to
            (independent of shift_notifications_enabled above - a user
            may want one channel without the other). Empty/None means no
            relay. Only takes effect if
            SettingsService.get_apprise_notifications_enabled() is on.
        apprise_oncall_target_ids: Same as above, for the weekly
            on-call reminder
        shifts: Relationship to Shift model
        on_calls: Relationship to OnCall model
        leaves: Relationship to Leave model
    """

    __tablename__ = "user"

    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    # 255, not 128: werkzeug.security.generate_password_hash()'s default
    # method (scrypt) produces a ~162-character string - SQLite has no
    # VARCHAR length enforcement (silently accepted regardless of the
    # declared length), which is why this was never caught until MySQL/
    # PostgreSQL, both of which reject an over-length value outright
    # (confirmed: DataError "Data too long for column" on MariaDB, even
    # for the very first default-admin creation on a fresh install).
    password_hash = db.Column(db.String(255))
    is_admin = db.Column(db.Boolean, default=False)
    group_id = db.Column(
        db.Integer, db.ForeignKey("groups.id"), nullable=False, default=1, index=True
    )
    ics_token = db.Column(db.String(64), unique=True, nullable=True)
    ics_token_created_at = db.Column(db.DateTime, nullable=True)
    timezone = db.Column(db.String(64), nullable=True)
    language = db.Column(db.String(5), nullable=True)
    date_format = db.Column(db.String(20), nullable=True)
    time_format = db.Column(db.String(20), nullable=True)
    shift_notifications_enabled = db.Column(db.Boolean, nullable=False, default=True)
    oncall_notifications_enabled = db.Column(db.Boolean, nullable=False, default=True)
    apprise_shift_target_ids = db.Column(db.Text, nullable=True)
    apprise_oncall_target_ids = db.Column(db.Text, nullable=True)

    # Relationships
    shifts = db.relationship(
        "Shift",
        backref="user",
        lazy=True,
        cascade="all, delete-orphan",
        foreign_keys="Shift.user_id",
    )
    on_calls = db.relationship(
        "OnCall",
        backref="user",
        lazy=True,
        cascade="all, delete-orphan",
        foreign_keys="OnCall.user_id",
    )
    leaves = db.relationship(
        "Leave",
        backref="user",
        lazy=True,
        cascade="all, delete-orphan",
        foreign_keys="Leave.user_id",
    )

    def to_dict(self) -> dict:
        """Convert to dict, excluding password_hash and ics_token.

        BaseModel.to_dict() dumps every column verbatim - overridden here
        because password_hash and ics_token are secrets (ics_token is a
        bearer credential for the anonymous ICS feed), not just any other
        piece of user data.
        """
        data = super().to_dict()
        data.pop("password_hash", None)
        data.pop("ics_token", None)
        return data

    def set_password(self, password: str) -> None:
        """Set the user's password (hashed).

        Args:
            password: Plain text password to hash and store
        """
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Check if the provided password matches the stored hash.

        Args:
            password: Plain text password to check

        Returns:
            True if the password matches, False otherwise
        """
        return check_password_hash(self.password_hash, password)

    def generate_ics_token(self) -> str:
        """Generate a unique token for ICS export.

        Also resets ics_token_created_at, restarting the expiry clock
        used by is_ics_token_expired().

        Returns:
            The generated token
        """
        self.ics_token = secrets.token_urlsafe(32)
        self.ics_token_created_at = _utcnow()
        return self.ics_token

    def is_ics_token_expired(self) -> bool:
        """Whether ics_token is past SettingsService.get_ics_token_expiry_days().

        Only meaningful for a user resolved via ics_token
        (ExportService.resolve_user) - self.ics_token is guaranteed set on
        that path, since that's how the user was even found. A missing
        ics_token_created_at (a token issued before this check existed,
        not yet backfilled by the migration) is treated as expired -
        forces a fresh regeneration rather than silently granting
        indefinite access.
        """
        if not self.ics_token_created_at:
            return True
        from datetime import timedelta, timezone

        from app.services import SettingsService

        expiry_days = SettingsService.get_ics_token_expiry_days()
        created_at = self.ics_token_created_at.replace(tzinfo=timezone.utc)
        return _utcnow() > created_at + timedelta(days=expiry_days)

    def ics_token_expires_at(self):
        """Datetime ics_token becomes invalid, or None if there's no token
        or no creation timestamp yet. Display-only (e.g. /profile/ics-token)."""
        if not self.ics_token or not self.ics_token_created_at:
            return None
        from datetime import timedelta

        from app.services import SettingsService

        expiry_days = SettingsService.get_ics_token_expiry_days()
        return self.ics_token_created_at + timedelta(days=expiry_days)

    def get_ics_export_url(
        self, export_type: str = "shifts", scope: str = "all"
    ) -> str | None:
        """Get the ICS export URL with the user's token.

        Args:
            export_type: Type of export - "shifts", "oncall", or "leaves"
            scope: Scope of export - "all" or "my"

        Returns:
            The ICS export URL or None if no token is set
        """
        if not self.ics_token:
            return None
        return f"/export/{export_type}?scope={scope}&token={self.ics_token}"

    def effective_timezone(self) -> str:
        """The IANA timezone to use for this user: their own preference if
        set, otherwise the organization's default_timezone setting."""
        if self.timezone:
            return self.timezone
        from app.services import SettingsService

        return SettingsService.get_default_timezone()

    def effective_language(self) -> str:
        """The UI language to use for this user: their own preference if
        set, otherwise the organization's default_language setting."""
        if self.language:
            return self.language
        from app.services import SettingsService

        return SettingsService.get_default_language()

    def effective_date_format(self) -> str:
        """The strftime date pattern to use for this user: their own
        preference if set, otherwise the organization's default_date_format
        setting."""
        if self.date_format:
            return self.date_format
        from app.services import SettingsService

        return SettingsService.get_default_date_format()

    def effective_time_format(self) -> str:
        """The strftime time pattern to use for this user: their own
        preference if set, otherwise the organization's default_time_format
        setting."""
        if self.time_format:
            return self.time_format
        from app.services import SettingsService

        return SettingsService.get_default_time_format()

    def get_apprise_shift_target_ids(self) -> list[int]:
        if not self.apprise_shift_target_ids:
            return []
        try:
            return json.loads(self.apprise_shift_target_ids)
        except json.JSONDecodeError:
            return []

    def set_apprise_shift_target_ids(self, target_ids: list[int]) -> None:
        self.apprise_shift_target_ids = json.dumps(target_ids) if target_ids else None

    def get_apprise_oncall_target_ids(self) -> list[int]:
        if not self.apprise_oncall_target_ids:
            return []
        try:
            return json.loads(self.apprise_oncall_target_ids)
        except json.JSONDecodeError:
            return []

    def set_apprise_oncall_target_ids(self, target_ids: list[int]) -> None:
        self.apprise_oncall_target_ids = json.dumps(target_ids) if target_ids else None

    def __repr__(self) -> str:
        return f"<User {self.name} ({self.email})>"
