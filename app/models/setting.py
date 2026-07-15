"""
Setting model for Leviia Schedule.

Generic DB-backed key/value store for admin-editable application settings
(default timezone, public base URL, pagination, notifications toggle,
backup retention, ICS token expiry). Same shape/pattern as AutomationConfig
(app/models/automation_config.py) but kept as a separate model: that one is
domain-named for on-call automation and its helpers (get_rotation_order/
set_rotation_order) don't belong next to unrelated settings.
"""

import json
from datetime import datetime, timezone

from app import db
from app.models.base import BaseModel


class Setting(BaseModel):
    """
    Generic key/value application setting.

    Attributes:
        key: Unique key identifying the setting
        value: Setting value (JSON-encoded for non-string values)
        updated_at: Timestamp of last update (inherited from BaseModel)
    """

    __tablename__ = "setting"

    key = db.Column(db.String(80), nullable=False, unique=True)
    value = db.Column(db.Text, nullable=False)

    @classmethod
    def get(cls, key: str, default=None):
        """
        Retrieve a setting value.

        Args:
            key: Setting key
            default: Value returned if no row exists for this key

        Returns:
            The stored value (decoded from JSON if applicable), or default
        """
        setting = cls.query.filter_by(key=key).first()
        if setting:
            try:
                return json.loads(setting.value)
            except json.JSONDecodeError:
                return setting.value
        return default

    @classmethod
    def set(cls, key: str, value):
        """
        Set a setting value (upsert).

        Args:
            key: Setting key
            value: Value to store (JSON-encoded unless already a string)

        Returns:
            The created or updated Setting instance
        """
        setting = cls.query.filter_by(key=key).first()
        encoded_value = json.dumps(value) if not isinstance(value, str) else value
        if setting:
            setting.value = encoded_value
            setting.updated_at = datetime.now(timezone.utc)
        else:
            setting = cls(key=key, value=encoded_value)
            db.session.add(setting)
        db.session.commit()
        return setting

    def __repr__(self) -> str:
        return f"<Setting {self.key} = {self.value}>"
