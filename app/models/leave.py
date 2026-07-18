"""
Leave model for Kairos.

This module contains the Leave model for leave management.
"""

from datetime import date

from app import db
from app.models.base import BaseModel


class Leave(BaseModel):
    """
    Leave model for tracking user leave requests.

    Attributes:
        user_id: Foreign key to User
        start_date: Start date of the leave
        end_date: End date of the leave
    """

    __tablename__ = "leave"

    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False, index=True
    )
    start_date = db.Column(db.Date, nullable=False, index=True)
    end_date = db.Column(db.Date, nullable=False, index=True)

    # Composite index for frequent overlap queries
    __table_args__ = (
        db.Index("idx_leave_user_date_range", "user_id", "start_date", "end_date"),
    )

    def duration(self) -> int:
        """Calculate the duration of the leave in days.

        Returns:
            Duration in days
        """
        delta = self.end_date - self.start_date
        return delta.days + 1  # Include both start and end dates

    def is_active(self) -> bool:
        """Check if this leave period is currently active.

        Returns:
            True if the current date is within the leave period
        """
        today = date.today()
        return self.start_date <= today <= self.end_date

    def __repr__(self) -> str:
        return f"<Leave {self.id} - {self.user.name} - {self.start_date} to {self.end_date}>"
