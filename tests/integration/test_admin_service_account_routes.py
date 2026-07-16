"""
Tests for the admin service accounts UI
(app/routes/admin_service_account_routes.py): CRUD, admin-only
permission, and the "secret shown once" contract.
"""

from app import db
from app.models import AuditLog, ServiceAccount
from app.services.service_account_service import ServiceAccountService


class TestListRoute:
    def test_requires_admin(self, test_app, non_admin_client):
        resp = non_admin_client.get("/admin/service-accounts", follow_redirects=False)
        assert resp.status_code == 302

    def test_lists_accounts(self, test_app, logged_in_client):
        with test_app.app_context():
            ServiceAccountService.create_account("Zapier")
            db.session.commit()

        resp = logged_in_client.get("/admin/service-accounts")
        assert resp.status_code == 200
        assert b"Zapier" in resp.data


class TestAddServiceAccount:
    def test_requires_admin(self, test_app, non_admin_client):
        resp = non_admin_client.get(
            "/admin/service-accounts/add", follow_redirects=False
        )
        assert resp.status_code == 302

    def test_creates_account_and_shows_token_once(self, test_app, logged_in_client):
        resp = logged_in_client.post(
            "/admin/service-accounts/add",
            data={"name": "Zapier", "description": "Test integration"},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert b"lsak_" in resp.data

        with test_app.app_context():
            sa = ServiceAccount.query.filter_by(name="Zapier").first()
            assert sa is not None
            assert sa.description == "Test integration"

    def test_writes_audit_log_entry(self, test_app, logged_in_client):
        logged_in_client.post(
            "/admin/service-accounts/add",
            data={"name": "Zapier"},
            follow_redirects=True,
        )
        with test_app.app_context():
            entry = AuditLog.query.filter_by(action="service_account.create").first()
            assert entry is not None
            assert entry.details == "Zapier"

    def test_missing_name_rejected(self, test_app, logged_in_client):
        resp = logged_in_client.post(
            "/admin/service-accounts/add", data={}, follow_redirects=True
        )
        assert resp.status_code == 200
        with test_app.app_context():
            assert ServiceAccount.query.count() == 0

    def test_invalid_expiry_rejected(self, test_app, logged_in_client):
        resp = logged_in_client.post(
            "/admin/service-accounts/add",
            data={"name": "Zapier", "expires_at": "not-a-date"},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        with test_app.app_context():
            assert ServiceAccount.query.count() == 0


class TestEditServiceAccount:
    def test_requires_admin(self, test_app, non_admin_client):
        with test_app.app_context():
            sa, _ = ServiceAccountService.create_account("Zapier")
            db.session.commit()
            sa_id = sa.id

        resp = non_admin_client.get(
            f"/admin/service-accounts/edit/{sa_id}", follow_redirects=False
        )
        assert resp.status_code == 302

    def test_updates_name_and_description(self, test_app, logged_in_client):
        with test_app.app_context():
            sa, _ = ServiceAccountService.create_account("Zapier")
            db.session.commit()
            sa_id = sa.id

        resp = logged_in_client.post(
            f"/admin/service-accounts/edit/{sa_id}",
            data={"name": "Zapier renamed", "description": "New description"},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        with test_app.app_context():
            from app.repositories.service_account_repository import (
                ServiceAccountRepository,
            )

            refreshed = ServiceAccountRepository.get_by_id(sa_id)
            assert refreshed.name == "Zapier renamed"
            assert refreshed.description == "New description"

    def test_does_not_expose_secret_in_form(self, test_app, logged_in_client):
        with test_app.app_context():
            sa, full_token = ServiceAccountService.create_account("Zapier")
            db.session.commit()
            sa_id = sa.id

        resp = logged_in_client.get(f"/admin/service-accounts/edit/{sa_id}")
        assert full_token.encode() not in resp.data

    def test_nonexistent_404(self, test_app, logged_in_client):
        resp = logged_in_client.get("/admin/service-accounts/edit/999999")
        assert resp.status_code == 404


class TestRegenerateSecret:
    def test_requires_admin(self, test_app, non_admin_client):
        with test_app.app_context():
            sa, _ = ServiceAccountService.create_account("Zapier")
            db.session.commit()
            sa_id = sa.id

        resp = non_admin_client.post(
            f"/admin/service-accounts/{sa_id}/regenerate", follow_redirects=False
        )
        assert resp.status_code == 302

    def test_shows_new_token_once_and_invalidates_old(self, test_app, logged_in_client):
        with test_app.app_context():
            sa, old_token = ServiceAccountService.create_account("Zapier")
            db.session.commit()
            sa_id = sa.id

        resp = logged_in_client.post(
            f"/admin/service-accounts/{sa_id}/regenerate", follow_redirects=True
        )
        assert resp.status_code == 200
        assert old_token.encode() not in resp.data
        assert b"lsak_" in resp.data


class TestToggleActive:
    def test_requires_admin(self, test_app, non_admin_client):
        with test_app.app_context():
            sa, _ = ServiceAccountService.create_account("Zapier")
            db.session.commit()
            sa_id = sa.id

        resp = non_admin_client.post(
            f"/admin/service-accounts/{sa_id}/toggle-active", follow_redirects=False
        )
        assert resp.status_code == 302

    def test_toggles_active_state(self, test_app, logged_in_client):
        with test_app.app_context():
            sa, _ = ServiceAccountService.create_account("Zapier")
            db.session.commit()
            sa_id = sa.id

        from app.repositories.service_account_repository import (
            ServiceAccountRepository,
        )

        logged_in_client.post(f"/admin/service-accounts/{sa_id}/toggle-active")
        with test_app.app_context():
            assert ServiceAccountRepository.get_by_id(sa_id).is_active is False

        logged_in_client.post(f"/admin/service-accounts/{sa_id}/toggle-active")
        with test_app.app_context():
            assert ServiceAccountRepository.get_by_id(sa_id).is_active is True


class TestDeleteServiceAccount:
    def test_requires_admin(self, test_app, non_admin_client):
        with test_app.app_context():
            sa, _ = ServiceAccountService.create_account("Zapier")
            db.session.commit()
            sa_id = sa.id

        resp = non_admin_client.post(
            f"/admin/service-accounts/delete/{sa_id}", follow_redirects=False
        )
        assert resp.status_code == 302

    def test_deletes_account(self, test_app, logged_in_client):
        with test_app.app_context():
            sa, _ = ServiceAccountService.create_account("Zapier")
            db.session.commit()
            sa_id = sa.id

        resp = logged_in_client.post(
            f"/admin/service-accounts/delete/{sa_id}", follow_redirects=True
        )
        assert resp.status_code == 200
        with test_app.app_context():
            assert ServiceAccount.query.count() == 0
