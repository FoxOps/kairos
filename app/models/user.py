"""
User and Group models for Leviia Schedule.

This module contains the User and Group models for user management
and authentication.
"""

import secrets

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app import db
from app.models.base import BaseModel


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
        timezone: Optional personal IANA timezone (e.g. "Europe/Paris"); None
            means "use the organization's default_timezone setting"
        shift_notifications_enabled: Opt-out for the weekly shift reminder
            email (only takes effect if notifications are enabled org-wide,
            see SettingsService.get_notifications_enabled())
        oncall_notifications_enabled: Opt-out for the weekly on-call
            reminder email (same org-wide gate as above)
        shifts: Relationship to Shift model
        on_calls: Relationship to OnCall model
        leaves: Relationship to Leave model
    """

    __tablename__ = "user"

    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    is_admin = db.Column(db.Boolean, default=False)
    group_id = db.Column(
        db.Integer, db.ForeignKey("groups.id"), nullable=False, default=1, index=True
    )
    ics_token = db.Column(db.String(64), unique=True, nullable=True)
    timezone = db.Column(db.String(64), nullable=True)
    shift_notifications_enabled = db.Column(db.Boolean, nullable=False, default=True)
    oncall_notifications_enabled = db.Column(db.Boolean, nullable=False, default=True)

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

        Returns:
            The generated token
        """
        self.ics_token = secrets.token_urlsafe(32)
        return self.ics_token

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

    def __repr__(self) -> str:
        return f"<User {self.name} ({self.email})>"
