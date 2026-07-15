"""
Base model for Leviia Schedule.

This module provides the BaseModel class that contains common fields
and methods for all models in the application.
"""

from datetime import datetime, timezone

from app import db


def _utcnow() -> datetime:
    """datetime.utcnow() est dépréciée (Python 3.12+) - utilisée comme
    `default`/`onupdate` de colonne (référence de fonction, pas un appel),
    donc un simple `datetime.now` ne suffit pas, il faut fixer l'argument
    `timezone.utc`. Le round-trip SQLite de SQLAlchemy retire le tzinfo à
    la lecture (vérifié empiriquement) : la valeur stockée reste une heure
    UTC naïve comme avant, seul l'avertissement de dépréciation disparaît."""
    return datetime.now(timezone.utc)


class BaseModel(db.Model):  # type: ignore[name-defined]  # limitation connue mypy + Flask-SQLAlchemy sans stubs dédiés
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
