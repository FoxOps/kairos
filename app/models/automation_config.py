"""
AutomationConfig model for Kairos.

This module contains the AutomationConfig model for storing automation
configuration settings.
"""

import json
from datetime import date, datetime, timezone

from app import db
from app.models.base import BaseModel


class AutomationConfig(BaseModel):
    """
    Configuration model for automation settings.

    Stores configuration parameters like on-call rotation order.

    Attributes:
        config_key: Unique key to identify the configuration type
        config_value: Configuration value (JSON for complex objects)
        updated_at: Timestamp of last update
    """

    __tablename__ = "automation_config"

    # Fallback reference date for on-call rotation-order phase (absolute
    # week-number anchor, see app/utils/automation/planner/rotation.py),
    # used only when an admin has never explicitly set one via
    # get_rotation_epoch/set_rotation_epoch below. An arbitrary but
    # permanently fixed date - it does not need to fall on any
    # particular weekday, and must never change once real generations
    # have used it, or every future rotation offset would shift.
    FALLBACK_ROTATION_EPOCH = date(2000, 1, 3)

    config_key = db.Column(db.String(80), nullable=False, unique=True)
    config_value = db.Column(db.Text, nullable=False)

    @classmethod
    def get_config(cls, key: str, default=None):
        """
        Retrieve a configuration value.

        Args:
            key: Configuration key
            default: Default value if not found

        Returns:
            Configuration value (decoded from JSON if necessary)
        """
        config = cls.query.filter_by(config_key=key).first()
        if config:
            try:
                return json.loads(config.config_value)
            except json.JSONDecodeError:
                return config.config_value
        return default

    @classmethod
    def set_config(cls, key: str, value):
        """
        Set a configuration value.

        Args:
            key: Configuration key
            value: Value to store (will be encoded to JSON if necessary)

        Returns:
            The created or updated AutomationConfig instance
        """
        config = cls.query.filter_by(config_key=key).first()
        if config:
            config.config_value = (
                json.dumps(value) if not isinstance(value, str) else value
            )
            config.updated_at = datetime.now(timezone.utc)
        else:
            config = cls(
                config_key=key,
                config_value=json.dumps(value) if not isinstance(value, str) else value,
            )
            db.session.add(config)
        db.session.commit()
        return config

    @classmethod
    def get_rotation_order(cls) -> list:
        """Get the on-call rotation order."""
        return cls.get_config("oncall_rotation_order", [])

    @classmethod
    def set_rotation_order(cls, rotation_order: list):
        """Set the on-call rotation order."""
        cls.set_config("oncall_rotation_order", rotation_order)

    @classmethod
    def get_rotation_epoch(cls) -> date:
        """Reference date for on-call rotation-order phase (see
        app/utils/automation/planner/rotation.py::absolute_week_index) -
        same "config wins, else documented fallback" pattern as every
        other admin-tunable value in this codebase, never a bare
        unconfigurable constant. Admin-editable so an org can explicitly
        reset rotation phase (e.g. after a disruptive staffing change)
        instead of being stuck with whatever date the app happened to
        ship with."""
        stored = cls.get_config("oncall_rotation_epoch")
        if stored is None:
            return cls.FALLBACK_ROTATION_EPOCH
        return date.fromisoformat(stored)

    @classmethod
    def set_rotation_epoch(cls, epoch: date) -> None:
        """Set the on-call rotation-order reference date."""
        cls.set_config("oncall_rotation_epoch", epoch.isoformat())

    def __repr__(self) -> str:
        return f"<AutomationConfig {self.config_key} = {self.config_value}>"
