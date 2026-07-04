"""
Tests unitaires pour les fonctions dans run.py
"""

import pytest
from datetime import datetime, timedelta
from app import create_app, db
from app.models import User, Group, Shift, OnCall, Leave, ShiftType
from run import (
    check_database_integrity,
    setup_database,
    create_default_data,
    DEFAULT_SHIFT_TYPES,
)


@pytest.fixture(scope="function")
def app():
    """Crée une instance de l'application Flask pour les tests."""
    app = create_app()
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["SECRET_KEY"] = "test-secret-key"

    # Importer les routes
    from app.routes import main, admin, export, auth

    with test_app.app_context():
        db.drop_all()
        db.create_all()
        yield app
        db.session.rollback()
        db.drop_all()


class TestDefaultShiftTypes:
    """Tests pour DEFAULT_SHIFT_TYPES."""

    def test_default_shift_types_structure(self):
        """Test que DEFAULT_SHIFT_TYPES a la bonne structure."""
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
        """Test les valeurs spécifiques de DEFAULT_SHIFT_TYPES."""
        names = [st["name"] for st in DEFAULT_SHIFT_TYPES]
        assert "morning" in names
        assert "afternoon" in names
        assert "evening" in names
        
        # Vérifier les heures
        for shift_type in DEFAULT_SHIFT_TYPES:
            assert 0 <= shift_type["start_hour"] < 24
            assert 0 <= shift_type["end_hour"] < 24
            assert shift_type["start_hour"] < shift_type["end_hour"]


class TestDatabaseIntegrity:
    """Tests pour check_database_integrity."""

    def test_check_database_integrity_valid(self, test_app):
        """Test avec une base de données valide."""
        with test_app.app_context():
            # Créer toutes les tables nécessaires
            db.create_all()
            
            # Ajouter les types de shifts par défaut
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
        """Test avec une table manquante."""
        with test_app.app_context():
            # Ne créer aucune table
            db.drop_all()
            
            result = check_database_integrity()
            assert result is False


class TestInitializeDatabase:
    """Tests pour initialize_database."""

    def test_initialize_database_creates_tables(self, test_app):
        """Test que l'initialisation crée toutes les tables."""
        with test_app.app_context():
            db.drop_all()
            
            create_default_data()
            
            # Vérifier que les tables existent
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            assert "groups" in tables
            assert "user" in tables
            assert "shift_types" in tables
            assert "shift" in tables
            assert "on_call" in tables
            assert "leave" in tables

    def test_initialize_database_creates_default_shift_types(self, test_app):
        """Test que l'initialisation crée les types de shifts par défaut."""
        with test_app.app_context():
            db.drop_all()
            
            create_default_data()
            
            # Vérifier que les types de shifts par défaut existent
            shift_types = ShiftType.query.all()
            assert len(shift_types) == len(DEFAULT_SHIFT_TYPES)
            
            for shift_type_data in DEFAULT_SHIFT_TYPES:
                shift_type = ShiftType.query.filter_by(name=shift_type_data["name"]).first()
                assert shift_type is not None
                assert shift_type.label == shift_type_data["label"]
                assert shift_type.start_hour == shift_type_data["start_hour"]
                assert shift_type.end_hour == shift_type_data["end_hour"]


class TestCreateDefaultData:
    """Tests pour create_default_data."""

    def test_create_default_data_creates_group(self, test_app):
        """Test que create_default_data crée un groupe par défaut."""
        with test_app.app_context():
            # S'assurer qu'aucun groupe n'existe
            Group.query.delete()
            db.session.commit()
            
            create_default_data()
            
            group = Group.query.first()
            assert group is not None
            assert group.name == "Defaut"
            assert group.is_part_of_schedule is True
            assert group.is_part_of_oncall is True

    def test_create_default_data_creates_admin_user(self, test_app):
        """Test que create_default_data crée un utilisateur admin."""
        with test_app.app_context():
            # S'assurer qu'aucun utilisateur n'existe
            User.query.delete()
            Group.query.delete()
            db.session.commit()
            
            create_default_data()
            
            user = User.query.first()
            assert user is not None
            assert user.name == "Administrateur"
            assert user.email == "admin@leviia.local"
            assert user.is_admin is True
            
            # Vérifier que le mot de passe est correct

    def test_create_default_data_does_not_duplicate(self, test_app):
        """Test que create_default_data ne duplique pas les données."""
        with test_app.app_context():
            # Créer un groupe et un utilisateur
            group = Group(name="Test Group", is_part_of_schedule=True, is_part_of_oncall=True)
            db.session.add(group)
            db.session.commit()
            
            user = User(
                name="Admin",
                email="admin@leviia.local",
                is_admin=True,
                group_id=group.id,
            )
            user.set_password("admin123")
            db.session.add(user)
            db.session.commit()
            
            initial_group_count = Group.query.count()
            initial_user_count = User.query.count()
            
            # Appeler create_default_data
            create_default_data()
            
            # Vérifier qu'aucun duplicata n'a été créé
            assert Group.query.count() == initial_group_count
            assert User.query.count() == initial_user_count


    """Tests pour setup_database."""

    def test_setup_database_empty(self, test_app):
        """Test setup_database avec une base vide."""
        with test_app.app_context():
            db.drop_all()
            
            setup_database()
            
            # Vérifier que les tables existent
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            assert "groups" in tables
            assert "user" in tables

    def test_setup_database_with_valid_structure(self, test_app):
        """Test setup_database avec une structure valide."""
        with test_app.app_context():
            db.create_all()
            
            # setup_database ne devrait rien faire
            setup_database()
            
            # Vérifier que les tables existent toujours
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            assert "groups" in tables
            assert "user" in tables
