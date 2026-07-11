"""
Tests pour les modèles de la base de données.
"""

import pytest
from datetime import datetime, timedelta
from werkzeug.security import check_password_hash
from app.models import User, Group, Shift, OnCall, Leave, ShiftType
from app import db


class TestGroupModel:
    """Tests pour le modèle Group."""

    def test_group_creation(self, test_app):
        """Test la création d'un groupe."""
        with test_app.app_context():
            group = Group(
                name="Test Group", is_part_of_schedule=True, is_part_of_oncall=False
            )
            db.session.add(group)
            db.session.commit()

            assert group.id is not None
            assert group.name == "Test Group"
            assert group.is_part_of_schedule is True
            assert group.is_part_of_oncall is False

    def test_group_unique_name(self, test_app):
        """Test que le nom du groupe doit être unique."""
        with test_app.app_context():
            group1 = Group(name="Unique Group", is_part_of_schedule=True)
            db.session.add(group1)
            db.session.commit()

            group2 = Group(name="Unique Group", is_part_of_schedule=False)
            db.session.add(group2)

            with pytest.raises(Exception):
                db.session.commit()

    def test_group_default_values(self, test_app):
        """Test les valeurs par défaut du groupe."""
        with test_app.app_context():
            group = Group(name="Default Group")
            db.session.add(group)
            db.session.commit()

            assert group.is_part_of_schedule is False
            assert group.is_part_of_oncall is False

    def test_group_users_relationship(self, test_app, test_group, test_user):
        """Test la relation entre Group et User."""
        with test_app.app_context():
            assert test_user.group_id == test_group.id
            assert test_user in test_group.users


class TestUserModel:
    """Tests pour le modèle User."""

    def test_user_creation(self, test_app, test_group):
        """Test la création d'un utilisateur."""
        with test_app.app_context():
            user = User(name="New User", email="new@test.com", group_id=test_group.id)
            db.session.add(user)
            db.session.commit()

            assert user.id is not None
            assert user.name == "New User"
            assert user.email == "new@test.com"
            assert user.is_admin is False

    def test_user_unique_email(self, test_app, test_group):
        """Test que l'email de l'utilisateur doit être unique."""
        with test_app.app_context():
            user1 = User(name="User 1", email="unique@test.com", group_id=test_group.id)
            db.session.add(user1)
            db.session.commit()

            user2 = User(name="User 2", email="unique@test.com", group_id=test_group.id)
            db.session.add(user2)

            with pytest.raises(Exception):
                db.session.commit()

    def test_user_password_hashing(self, test_app, test_group):
        """Test le hachage du mot de passe."""
        with test_app.app_context():
            user = User(
                name="Password User", email="password@test.com", group_id=test_group.id
            )
            user.set_password("mysecretpassword")
            db.session.add(user)
            db.session.commit()

            assert user.password_hash is not None
            assert user.password_hash != "mysecretpassword"
            assert user.check_password("mysecretpassword") is True
            assert user.check_password("wrongpassword") is False

    def test_user_default_values(self, test_app, test_group):
        """Test les valeurs par défaut de l'utilisateur."""
        with test_app.app_context():
            user = User(
                name="Default User", email="default@test.com", group_id=test_group.id
            )
            db.session.add(user)
            db.session.commit()

            assert user.is_admin is False

    def test_user_repr(self, test_app, test_group):
        """Test la représentation string de l'utilisateur."""
        with test_app.app_context():
            user = User(name="Repr User", email="repr@test.com", group_id=test_group.id)
            db.session.add(user)
            db.session.commit()

            repr_str = repr(user)
            assert "Repr User" in repr_str
            assert "repr@test.com" in repr_str

    def test_user_relationships(self, test_app, test_user, test_shift_type, test_group):
        """Test les relations de l'utilisateur."""
        with test_app.app_context():
            # Créer un shift pour l'utilisateur
            shift_date = datetime(2023, 12, 1).date()
            start_time = datetime(2023, 12, 1, 7, 0)
            end_time = datetime(2023, 12, 1, 15, 0)
            shift = Shift(
                user_id=test_user.id,
                shift_type_id=test_shift_type.id,
                start_time=start_time,
                end_time=end_time,
                date=shift_date,
            )
            db.session.add(shift)

            # Créer une astreinte pour l'utilisateur
            oncall_start = datetime(2023, 12, 1, 21, 0)
            oncall_end = oncall_start + timedelta(days=7, hours=-14)
            oncall = OnCall(
                user_id=test_user.id, start_time=oncall_start, end_time=oncall_end
            )
            db.session.add(oncall)

            # Créer un congé pour l'utilisateur
            leave_start = datetime(2023, 12, 10).date()
            leave_end = datetime(2023, 12, 15).date()
            leave = Leave(
                user_id=test_user.id, start_date=leave_start, end_date=leave_end
            )
            db.session.add(leave)
            db.session.commit()

            # Vérifier les relations
            assert len(test_user.shifts) == 1
            assert test_user.shifts[0].id == shift.id
            assert len(test_user.on_calls) == 1
            assert test_user.on_calls[0].id == oncall.id
            assert len(test_user.leaves) == 1
            assert test_user.leaves[0].id == leave.id
            assert test_user.group.id == test_group.id


class TestShiftTypeModel:
    """Tests pour le modèle ShiftType."""

    def test_shift_type_creation(self, test_app):
        """Test la création d'un type de shift."""
        with test_app.app_context():
            shift_type = ShiftType(
                name="morning", label="Matin", start_hour=7, end_hour=15
            )
            db.session.add(shift_type)
            db.session.commit()

            assert shift_type.id is not None
            assert shift_type.name == "morning"
            assert shift_type.label == "Matin"
            assert shift_type.start_hour == 7
            assert shift_type.end_hour == 15

    def test_shift_type_unique_name(self, test_app):
        """Test que le nom du type de shift doit être unique."""
        with test_app.app_context():
            shift_type1 = ShiftType(
                name="unique", label="Unique", start_hour=8, end_hour=16
            )
            db.session.add(shift_type1)
            db.session.commit()

            shift_type2 = ShiftType(
                name="unique", label="Another", start_hour=9, end_hour=17
            )
            db.session.add(shift_type2)

            with pytest.raises(Exception):
                db.session.commit()

    def test_shift_type_shifts_relationship(self, test_app, test_shift_type, test_user):
        """Test la relation entre ShiftType et Shift."""
        with test_app.app_context():
            shift_date = datetime(2023, 12, 1).date()
            start_time = datetime(2023, 12, 1, 7, 0)
            end_time = datetime(2023, 12, 1, 15, 0)
            shift = Shift(
                user_id=test_user.id,
                shift_type_id=test_shift_type.id,
                start_time=start_time,
                end_time=end_time,
                date=shift_date,
            )
            db.session.add(shift)
            db.session.commit()

            assert len(test_shift_type.shifts) == 1
            assert test_shift_type.shifts[0].id == shift.id


class TestShiftModel:
    """Tests pour le modèle Shift."""

    def test_shift_creation(self, test_app, test_user, test_shift_type):
        """Test la création d'un shift."""
        with test_app.app_context():
            shift_date = datetime(2023, 12, 1).date()
            start_time = datetime(2023, 12, 1, 7, 0)
            end_time = datetime(2023, 12, 1, 15, 0)
            shift = Shift(
                user_id=test_user.id,
                shift_type_id=test_shift_type.id,
                start_time=start_time,
                end_time=end_time,
                date=shift_date,
            )
            db.session.add(shift)
            db.session.commit()

            assert shift.id is not None
            assert shift.user_id == test_user.id
            assert shift.shift_type_id == test_shift_type.id
            assert shift.date == shift_date

    def test_shift_relationships(self, test_app, test_shift):
        """Test les relations du shift."""
        with test_app.app_context():
            assert test_shift.user is not None
            assert test_shift.shift_type is not None
            assert test_shift in test_shift.user.shifts
            assert test_shift in test_shift.shift_type.shifts


class TestOnCallModel:
    """Tests pour le modèle OnCall."""

    def test_oncall_creation(self, test_app, test_user):
        """Test la création d'une astreinte."""
        with test_app.app_context():
            start_time = datetime(2023, 12, 1, 21, 0)
            end_time = start_time + timedelta(days=7, hours=-14)
            oncall = OnCall(
                user_id=test_user.id, start_time=start_time, end_time=end_time
            )
            db.session.add(oncall)
            db.session.commit()

            assert oncall.id is not None
            assert oncall.user_id == test_user.id
            assert oncall.start_time == start_time
            assert oncall.end_time == end_time

    def test_oncall_relationship(self, test_app, test_oncall):
        """Test la relation entre OnCall et User."""
        with test_app.app_context():
            assert test_oncall.user is not None
            assert test_oncall in test_oncall.user.on_calls


class TestLeaveModel:
    """Tests pour le modèle Leave."""

    def test_leave_creation(self, test_app, test_user):
        """Test la création d'un congé."""
        with test_app.app_context():
            start_date = datetime(2023, 12, 10).date()
            end_date = datetime(2023, 12, 15).date()
            leave = Leave(
                user_id=test_user.id, start_date=start_date, end_date=end_date
            )
            db.session.add(leave)
            db.session.commit()

            assert leave.id is not None
            assert leave.user_id == test_user.id
            assert leave.start_date == start_date
            assert leave.end_date == end_date

    def test_leave_relationship(self, test_app, test_leave):
        """Test la relation entre Leave et User."""
        with test_app.app_context():
            assert test_leave.user is not None
            assert test_leave in test_leave.user.leaves

    def test_leave_without_reason(self, test_app, test_user):
        """Test la création d'un congé sans raison."""
        with test_app.app_context():
            start_date = datetime(2023, 12, 10).date()
            end_date = datetime(2023, 12, 15).date()
            leave = Leave(
                user_id=test_user.id, start_date=start_date, end_date=end_date
            )
            db.session.add(leave)
            db.session.commit()

            assert leave.id is not None
