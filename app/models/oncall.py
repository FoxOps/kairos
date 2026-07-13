"""
OnCall model for Leviia Schedule.

This module contains the OnCall model for on-call duty management.
"""

from datetime import datetime

from app import db
from app.models.base import BaseModel


class OnCall(BaseModel):
    """
    OnCall model for tracking on-call duties.

    Attributes:
        user_id: Foreign key to User
        start_time: Start datetime of the on-call period
        end_time: End datetime of the on-call period
    """

    __tablename__ = "on_call"

    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False, index=True
    )
    start_time = db.Column(db.DateTime, nullable=False, index=True)
    end_time = db.Column(db.DateTime, nullable=False, index=True)

    # Composite index for frequent overlap queries
    __table_args__ = (
        db.Index("idx_oncall_user_start_end", "user_id", "start_time", "end_time"),
    )

    def duration(self) -> int:
        """Calculate the duration of the on-call period in hours.

        Returns:
            Duration in hours
        """
        delta = self.end_time - self.start_time
        return delta.total_seconds() / 3600

    def is_active(self) -> bool:
        """Check if this on-call period is currently active.

        Returns:
            True if the current time is within the on-call period
        """
        now = datetime.now()
        return self.start_time <= now <= self.end_time

    def __repr__(self) -> str:
        return f"<OnCall {self.id} - {self.user.name} - {self.start_time} to {self.end_time}>"
