"""
Tests for ServiceAccountService (app/services/service_account_service.py).
"""

from app.models import AuditLog, ServiceAccount
from app.repositories.service_account_repository import ServiceAccountRepository
from app.services.service_account_service import ServiceAccountService


class TestCreateAccount:
    def test_creates_account_and_returns_full_token(self, test_app):
        with test_app.app_context():
            sa, full_token = ServiceAccountService.create_account(
                "Zapier", "Third-party integration"
            )

            assert sa.id is not None
            assert sa.name == "Zapier"
            assert full_token.startswith("ksak_")
            assert ServiceAccount.hash_token(full_token) == sa.token_hash

    def test_logs_audit_entry_without_leaking_token(self, test_app):
        with test_app.app_context():
            sa, full_token = ServiceAccountService.create_account("Zapier")

            entry = AuditLog.query.filter_by(action="service_account.create").first()
            assert entry is not None
            assert entry.details == "Zapier"
            assert full_token not in (entry.details or "")


class TestRevokeAndReactivate:
    def test_revoke_deactivates(self, test_app):
        with test_app.app_context():
            sa, _ = ServiceAccountService.create_account("Zapier")
            ServiceAccountService.revoke(sa)
            assert sa.is_active is False

            entry = AuditLog.query.filter_by(action="service_account.revoke").first()
            assert entry is not None

    def test_reactivate_reactivates(self, test_app):
        with test_app.app_context():
            sa, _ = ServiceAccountService.create_account("Zapier")
            ServiceAccountService.revoke(sa)
            ServiceAccountService.reactivate(sa)
            assert sa.is_active is True


class TestRegenerateSecret:
    def test_old_token_no_longer_matches(self, test_app):
        with test_app.app_context():
            sa, old_token = ServiceAccountService.create_account("Zapier")
            old_hash = sa.token_hash

            new_token = ServiceAccountService.regenerate_secret(sa)

            assert new_token != old_token
            assert sa.token_hash != old_hash
            assert ServiceAccountRepository.get_by_token_hash(old_hash) is None
            assert ServiceAccountRepository.get_by_token_hash(sa.token_hash) is not None

    def test_logs_audit_entry_without_leaking_token(self, test_app):
        with test_app.app_context():
            sa, _ = ServiceAccountService.create_account("Zapier")
            new_token = ServiceAccountService.regenerate_secret(sa)

            entry = AuditLog.query.filter_by(
                action="service_account.regenerate_secret"
            ).first()
            assert entry is not None
            assert new_token not in (entry.details or "")


class TestDelete:
    def test_deletes_account(self, test_app):
        with test_app.app_context():
            sa, _ = ServiceAccountService.create_account("Zapier")
            sa_id = sa.id

            ServiceAccountService.delete(sa)

            assert ServiceAccountRepository.get_by_id(sa_id) is None
            entry = AuditLog.query.filter_by(action="service_account.delete").first()
            assert entry is not None
