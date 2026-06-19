"""
Configuration des tests pour Leviia Schedule.
"""
import pytest
from app import create_app, db


@pytest.fixture(scope='function')
def app():
    """Crée une instance de l'application Flask pour les tests."""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False

    # Importer les routes
    from app.routes import main, admin, export, auth

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    """Client de test Flask."""
    with app.test_client() as client:
        yield client
