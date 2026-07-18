"""
AutomationConfig model for Kairos.

This module contains the AutomationConfig model for storing automation
configuration settings.
"""

import json
from datetime import datetime, timezone

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

    def __repr__(self) -> str:
        return f"<AutomationConfig {self.config_key} = {self.config_value}>"
