#!/usr/bin/env python3
"""SQLite database initialization script for Kairos."""

from app import app, db
from app.models import Group, ShiftType, User
from run import setup_database

# Default shift types
DEFAULT_SHIFT_TYPES = [
    {"name": "morning", "label": "07h-15h", "start_hour": 7, "end_hour": 15},
    {"name": "afternoon", "label": "09h-17h", "start_hour": 9, "end_hour": 17},
    {"name": "evening", "label": "13h-21h", "start_hour": 13, "end_hour": 21},
]


def main():
    """Initializes the database with the default tables and data."""
    with app.app_context():
        setup_database()

        # Default shift types
        for st in DEFAULT_SHIFT_TYPES:
            if not ShiftType.query.filter_by(name=st["name"]).first():
                db.session.add(ShiftType(**st))

        # Default group
        if not Group.query.first():
            db.session.add(
                Group(name="Defaut", is_part_of_schedule=True, is_part_of_oncall=True)
            )
            db.session.commit()

        # Default admin
        if not User.query.first():
            group = Group.query.first()
            admin = User(
                name="Admin",
                email="admin@kairos.local",
                is_admin=True,
                group_id=group.id,
            )
            admin.set_password("admin123")
            admin.generate_ics_token()
            db.session.add(admin)
            db.session.commit()
            print("✅ Utilisateur admin créé")


if __name__ == "__main__":
    main()
