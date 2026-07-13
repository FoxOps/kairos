"""
Base model for Leviia Schedule.

This module provides the BaseModel class that contains common fields
and methods for all models in the application.
"""

from datetime import datetime

from app import db


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
    created_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, index=True
    )
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        index=True,
    )

    def save(self) -> None:
        """Save the model instance to the database."""
        db.session.add(self)
        db.session.commit()

    def delete(self) -> None:
        """Delete the model instance from the database."""
        db.session.delete(self)
        db.session.commit()

    def update(self, **kwargs) -> None:
        """
        Update the model instance with the provided keyword arguments.

        Args:
            **kwargs: Fields to update and their new values
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        db.session.commit()

    @classmethod
    def get_by_id(cls, id: int):
        """
        Get a model instance by its ID.

        Args:
            id: The ID of the model instance

        Returns:
            The model instance or None if not found
        """
        return cls.query.get(id)

    @classmethod
    def get_all(cls):
        """
        Get all instances of the model.

        Returns:
            List of all model instances
        """
        return cls.query.all()

    @classmethod
    def get_first(cls):
        """
        Get the first instance of the model.

        Returns:
            The first model instance or None if none exist
        """
        return cls.query.first()

    @classmethod
    def count(cls) -> int:
        """
        Count the number of instances of the model.

        Returns:
            The count of model instances
        """
        return cls.query.count()

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
