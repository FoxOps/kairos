"""
Tests for ServiceAccountRepository
(app/repositories/service_account_repository.py).
"""

from app import db
from app.models import ServiceAccount
from app.repositories.service_account_repository import ServiceAccountRepository


class TestCreate:
    def test_creates_service_account(self, test_app):
        with test_app.app_context():
            sa = ServiceAccountRepository.create(
                "Zapier", "Third-party integration", "lsak_abcd1234", "hash1"
            )
            db.session.commit()

            fetched = db.session.get(ServiceAccount, sa.id)
            assert fetched.name == "Zapier"
            assert fetched.description == "Third-party integration"
            assert fetched.token_prefix == "lsak_abcd1234"
            assert fetched.token_hash == "hash1"
            assert fetched.is_active is True
            assert fetched.expires_at is None


class TestGetByTokenHash:
    def test_finds_matching_hash(self, test_app):
        with test_app.app_context():
            ServiceAccountRepository.create("Zapier", None, "lsak_abcd", "hash1")
            db.session.commit()

            found = ServiceAccountRepository.get_by_token_hash("hash1")
            assert found is not None
            assert found.name == "Zapier"

    def test_no_match_returns_none(self, test_app):
        with test_app.app_context():
            assert ServiceAccountRepository.get_by_token_hash("nope") is None


class TestGetAll:
    def test_orders_by_name(self, test_app):
        with test_app.app_context():
            ServiceAccountRepository.create("Zeta", None, "lsak_z", "hz")
            ServiceAccountRepository.create("Alpha", None, "lsak_a", "ha")
            db.session.commit()

            accounts = ServiceAccountRepository.get_all()
            assert [a.name for a in accounts] == ["Alpha", "Zeta"]


class TestDelete:
    def test_deletes_service_account(self, test_app):
        with test_app.app_context():
            sa = ServiceAccountRepository.create("Zapier", None, "lsak_a", "hash1")
            db.session.commit()
            sa_id = sa.id

            ServiceAccountRepository.delete(sa)
            db.session.commit()

            assert ServiceAccountRepository.get_by_id(sa_id) is None


class TestTouchLastUsed:
    def test_sets_last_used_at(self, test_app):
        with test_app.app_context():
            sa = ServiceAccountRepository.create("Zapier", None, "lsak_a", "hash1")
            db.session.commit()
            assert sa.last_used_at is None

            ServiceAccountRepository.touch_last_used(sa)

            assert sa.last_used_at is not None
