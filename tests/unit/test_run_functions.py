"""
Unit tests for the functions in run.py
"""

from app import db
from app.models import Group, ShiftType, User
from run import (
    DEFAULT_SHIFT_TYPES,
    check_database_integrity,
    create_default_data,
    setup_database,
)


class TestDevServerDebugFlag:
    """Regression test (v1.0 load testing): app.run()'s debug argument
    used to be hardcoded True, ignoring FLASK_DEBUG/Config.DEBUG
    entirely - `python run.py` (the documented non-Docker way to run
    this app, HOST defaults to 0.0.0.0) always exposed Werkzeug's
    interactive debugger regardless of what an admin set in .env, a real
    RCE surface on any unhandled exception. The `if __name__ ==
    "__main__":` block itself can't be unit-tested without spawning a
    real subprocess (slow/flaky for CI) - this checks the source
    directly instead, same pattern as
    test_backup_database.py::test_no_import_of_app_package."""

    def test_dev_server_debug_flag_is_not_hardcoded(self):
        import run

        source = open(run.__file__).read()
        assert "debug=True" not in source
        assert 'app.config.get("DEBUG"' in source


class TestDefaultShiftTypes:
    """Tests for DEFAULT_SHIFT_TYPES."""

    def test_default_shift_types_structure(self):
        """Test that DEFAULT_SHIFT_TYPES has the right structure."""
        assert len(DEFAULT_SHIFT_TYPES) == 3

        for shift_type in DEFAULT_SHIFT_TYPES:
            assert "name" in shift_type
            assert "label" in shift_type
            assert "start_hour" in shift_type
            assert "end_hour" in shift_type

            assert isinstance(shift_type["name"], str)
            assert isinstance(shift_type["label"], str)
            assert isinstance(shift_type["start_hour"], int)
            assert isinstance(shift_type["end_hour"], int)

    def test_default_shift_types_values(self):
        """Test the specific values of DEFAULT_SHIFT_TYPES."""
        names = [st["name"] for st in DEFAULT_SHIFT_TYPES]
        assert "morning" in names
        assert "afternoon" in names
        assert "evening" in names

        # Check the hours
        for shift_type in DEFAULT_SHIFT_TYPES:
            assert 0 <= shift_type["start_hour"] < 24
            assert 0 <= shift_type["end_hour"] < 24
            assert shift_type["start_hour"] < shift_type["end_hour"]


class TestDatabaseIntegrity:
    """Tests for check_database_integrity."""

    def test_check_database_integrity_valid(self, test_app):
        """Test with a valid database."""
        with test_app.app_context():
            # Create every required table
            db.create_all()

            # Add the default shift types
            for shift_type_data in DEFAULT_SHIFT_TYPES:
                shift_type = ShiftType(
                    name=shift_type_data["name"],
                    label=shift_type_data["label"],
                    start_hour=shift_type_data["start_hour"],
                    end_hour=shift_type_data["end_hour"],
                )
                db.session.add(shift_type)
            db.session.commit()

            result = check_database_integrity()
            assert result is True

    def test_check_database_integrity_missing_table(self, test_app):
        """Test with a missing table."""
        with test_app.app_context():
            # Create no tables at all
            db.drop_all()

            result = check_database_integrity()
            assert result is False


class TestInitializeDatabase:
    """Tests for initialize_database."""

    def test_initialize_database_creates_tables(self, test_app):
        """Test that initialization creates every table."""
        with test_app.app_context():
            db.drop_all()
            setup_database()
            create_default_data()

            # Check that the tables exist
            from sqlalchemy import inspect

            inspector = inspect(db.engine)
            tables = inspector.get_table_names()

            assert "groups" in tables
            assert "user" in tables
            assert "shift_types" in tables
            assert "shift" in tables
            assert "on_call" in tables
            assert "leave" in tables
            assert "swap_request" in tables
            assert "app_notification" in tables

    def test_initialize_database_creates_default_shift_types(self, test_app):
        """Test that initialization creates the default shift types."""
        with test_app.app_context():
            db.drop_all()
            setup_database()
            create_default_data()

            # Check that the default shift types exist
            shift_types = ShiftType.query.all()
            assert len(shift_types) == len(DEFAULT_SHIFT_TYPES)

            for shift_type_data in DEFAULT_SHIFT_TYPES:
                shift_type = ShiftType.query.filter_by(
                    name=shift_type_data["name"]
                ).first()
                assert shift_type is not None
                assert shift_type.label == shift_type_data["label"]
                assert shift_type.start_hour == shift_type_data["start_hour"]
                assert shift_type.end_hour == shift_type_data["end_hour"]


class TestCreateDefaultData:
    """Tests for create_default_data."""

    def test_create_default_data_creates_group(self, test_app):
        """Test that create_default_data creates a default group."""
        with test_app.app_context():
            # Make sure no group exists
            Group.query.delete()
            db.session.commit()

            create_default_data()

            group = Group.query.first()
            assert group is not None
            assert group.name == "Defaut"
            assert group.is_part_of_schedule is True
            assert group.is_part_of_oncall is True

    def test_create_default_data_creates_admin_user(self, test_app):
        """Test that create_default_data creates an admin user."""
        with test_app.app_context():
            # Make sure no user exists
            User.query.delete()
            Group.query.delete()
            db.session.commit()

            create_default_data()

            user = User.query.first()
            assert user is not None
            assert user.name == "Administrateur"
            assert user.email == "admin@kairos.local"
            assert user.is_admin is True

            # Check that the password is correct

    def test_create_default_data_does_not_duplicate(self, test_app):
        """Test that create_default_data doesn't duplicate data."""
        with test_app.app_context():
            # Create a group and a user - the group name must match the
            # one create_default_data() looks for ("Defaut" by default),
            # otherwise this test verifies nothing: it would just create
            # a second group without ever exercising the
            # no-duplication logic.
            group = Group(
                name="Defaut", is_part_of_schedule=True, is_part_of_oncall=True
            )
            db.session.add(group)
            db.session.commit()

            user = User(
                name="Admin",
                email="admin@kairos.local",
                is_admin=True,
                group_id=group.id,
            )
            user.set_password("admin123")
            db.session.add(user)
            db.session.commit()

            initial_group_count = Group.query.count()
            initial_user_count = User.query.count()

            # Call create_default_data
            create_default_data()

            # Check that no duplicate was created
            assert Group.query.count() == initial_group_count
            assert User.query.count() == initial_user_count


class TestSetupDatabase:
    """Tests for setup_database."""

    def test_setup_database_empty(self, test_app):
        """Test setup_database with an empty database."""
        with test_app.app_context():
            db.drop_all()

            setup_database()

            # Check that the tables exist
            from sqlalchemy import inspect

            inspector = inspect(db.engine)
            tables = inspector.get_table_names()

            assert "groups" in tables
            assert "user" in tables

    def test_setup_database_with_valid_structure(self, test_app):
        """Test setup_database against a pre-Alembic database (tables
        already created by db.create_all(), no alembic_version table)."""
        with test_app.app_context():
            db.create_all()

            # Stamps the baseline revision and applies anything after
            # it - a no-op on the schema either way since it already
            # matches current models, but no longer a literal no-op
            # call (it does touch the DB to record the stamp).
            setup_database()

            # Check that the tables still exist
            from sqlalchemy import inspect

            inspector = inspect(db.engine)
            tables = inspector.get_table_names()

            assert "groups" in tables
            assert "user" in tables
