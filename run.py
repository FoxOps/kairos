import secrets

from app import app, db

# Import models to register the tables with SQLAlchemy
from app.models import Group, ShiftType, User

# Import routes so they get registered

# Default shift types
DEFAULT_SHIFT_TYPES = [
    {"name": "morning", "label": "07h-15h", "start_hour": 7, "end_hour": 15},
    {"name": "afternoon", "label": "09h-17h", "start_hour": 9, "end_hour": 17},
    {"name": "evening", "label": "13h-21h", "start_hour": 13, "end_hour": 21},
]


def check_database_integrity():
    """Check the database's integrity and return True if it's valid."""
    from sqlalchemy import inspect

    try:
        # Check that all tables exist
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()

        required_tables = [
            "user",
            "groups",
            "shift_types",
            "shift",
            "on_call",
            "leave",
            "swap_request",
            "app_notification",
        ]

        for table in required_tables:
            if table not in tables:
                return False

        return True
    except Exception:
        return False


def setup_database():
    """Set up the database.

    Requires an active application context (the caller must already be
    inside a `with app.app_context():`, or the test equivalent).
    """
    # Create the tables if they don't exist
    db.create_all()

    # Check the database's integrity
    if not check_database_integrity():
        # If the tables don't exist, recreate them
        db.drop_all()
        db.create_all()


def create_default_data():
    """Create the default data if it doesn't exist.

    Requires an active application context (the caller must already be
    inside a `with app.app_context():`, or the test equivalent).
    """
    import os

    from werkzeug.security import generate_password_hash

    # Create the default group
    default_group_name = os.environ.get("DEFAULT_GROUP_NAME") or "Defaut"
    default_group = Group.query.filter_by(name=default_group_name).first()
    if not default_group:
        default_group = Group(
            name=default_group_name,
            is_part_of_schedule=os.environ.get(
                "DEFAULT_GROUP_IN_SCHEDULE", "true"
            ).lower()
            != "false",
            is_part_of_oncall=os.environ.get("DEFAULT_GROUP_IN_ONCALL", "true").lower()
            != "false",
        )
        db.session.add(default_group)
        db.session.commit()

    # Create the default admin user
    default_admin_email = os.environ.get("DEFAULT_ADMIN_EMAIL") or "admin@leviia.local"
    default_admin_password = os.environ.get(
        "DEFAULT_ADMIN_PASSWORD"
    ) or secrets.token_urlsafe(16)

    admin_user = User.query.filter_by(email=default_admin_email).first()
    if not admin_user:
        # The User model has no 'username' field, use 'name' instead
        admin_user = User(
            email=default_admin_email,
            name="Administrateur",
            password_hash=generate_password_hash(default_admin_password),
            is_admin=True,
            group_id=default_group.id,
        )
        db.session.add(admin_user)
        db.session.commit()
        print(f"✅ Admin user created: {default_admin_email}")
    else:
        print(f"✅ Admin user already exists: {default_admin_email}")

    # Create the default shift types
    for shift_type_data in DEFAULT_SHIFT_TYPES:
        shift_type = ShiftType.query.filter_by(name=shift_type_data["name"]).first()
        if not shift_type:
            shift_type = ShiftType(
                name=shift_type_data["name"],
                label=shift_type_data["label"],
                start_hour=shift_type_data["start_hour"],
                end_hour=shift_type_data["end_hour"],
            )
            db.session.add(shift_type)
    db.session.commit()


if __name__ == "__main__":
    import os

    with app.app_context():
        # Set up the database (once)
        setup_database()

        # Create the default data
        create_default_data()

    # Listen on 0.0.0.0:5000 to allow external connections
    host = os.environ.get("FLASK_HOST") or "0.0.0.0"
    port = int(os.environ.get("FLASK_PORT") or 5000)

    # Disable the reloader to avoid "database is locked" issues with SQLite -
    # the reloader spawns a new process that can lock the database
    app.run(host=host, port=port, debug=True, use_reloader=False)
