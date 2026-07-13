"""
Shift and ShiftType models for Leviia Schedule.

This module contains the Shift and ShiftType models for shift management.
"""

from app import db
from app.models.base import BaseModel


class ShiftType(BaseModel):
    """
    ShiftType model for defining different types of shifts.

    Attributes:
        name: Unique name of the shift type
        label: Display label for the shift type
        start_hour: Start hour (0-23)
        end_hour: End hour (0-23)
        shifts: Relationship to Shift model
    """

    __tablename__ = "shift_types"

    name = db.Column(db.String(20), nullable=False, unique=True)
    label = db.Column(db.String(20), nullable=False)
    start_hour = db.Column(db.Integer, nullable=False)
    end_hour = db.Column(db.Integer, nullable=False)

    # Relationships
    shifts = db.relationship(
        "Shift", backref="shift_type", lazy=True, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<ShiftType {self.name} ({self.start_hour}:00-{self.end_hour}:00)>"


class Shift(BaseModel):
    """
    Shift model for tracking user work shifts.

    Attributes:
        user_id: Foreign key to User
        shift_type_id: Foreign key to ShiftType
        start_time: Start datetime of the shift
        end_time: End datetime of the shift
        date: Date of the shift (for indexing and filtering)
    """

    __tablename__ = "shift"

    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False, index=True
    )
    shift_type_id = db.Column(
        db.Integer, db.ForeignKey("shift_types.id"), nullable=False, index=True
    )
    start_time = db.Column(db.DateTime, nullable=False, index=True)
    end_time = db.Column(db.DateTime, nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, index=True)

    # Composite indexes for frequent queries
    __table_args__ = (
        db.Index("idx_shift_user_date", "user_id", "date"),
        db.Index("idx_shift_date_start", "date", "start_time"),
    )

    def duration(self) -> int:
        """Calculate the duration of the shift in hours.

        Returns:
            Duration in hours
        """
        delta = self.end_time - self.start_time
        return delta.total_seconds() / 3600

    def __repr__(self) -> str:
        return f"<Shift {self.id} - {self.user.name} - {self.date}>"
