"""
Base model for Leviia Schedule.

This module provides the BaseModel class that contains common fields
and methods for all models in the application.
"""

from datetime import datetime, timezone

from app import db


def _utcnow() -> datetime:
    """datetime.utcnow() is deprecated (Python 3.12+) - used here as a
    column `default`/`onupdate` (a function reference, not a call), so a
    plain `datetime.now` isn't enough; the `timezone.utc` argument must be
    bound. SQLAlchemy's SQLite round-trip strips tzinfo back out on read:
    the stored value stays a naive UTC datetime exactly as before, only
    the deprecation warning goes away."""
    return datetime.now(timezone.utc)


class BaseModel(db.Model):  # type: ignore[name-defined]  # known mypy + Flask-SQLAlchemy limitation without dedicated stubs
    """
    Abstract base model with common fields and methods.

    All models should inherit from this class to ensure consistency
    and to have access to common functionality.

    Attributes:
        id: Primary key
        created_at: Timestamp when the record was created
        updated_at: Timestamp when the record was last updated
    """

    __abstract__ = True

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow, index=True)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=_utcnow,
        onupdate=_utcnow,
        index=True,
    )

    def to_dict(self) -> dict:
        """
        Convert the model instance to a dictionary.

        Returns:
            Dictionary representation of the model
        """
        return {
            column.name: getattr(self, column.name) for column in self.__table__.columns
        }

    def __repr__(self) -> str:
        """String representation of the model instance."""
        return f"<{self.__class__.__name__} id={self.id}>"
