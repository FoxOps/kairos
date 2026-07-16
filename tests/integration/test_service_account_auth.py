"""
Tests for app/auth/service_account_auth.py::resolve_service_account -
the bearer-token auth hook used by every public API blueprint
(app/api/). Exercised directly against a request context here; full
end-to-end coverage through a real /api/v1/* route lives in
tests/integration/test_api_v1_routes.py once resources exist.
"""

from datetime import datetime, timedelta, timezone

import pytest
from flask import g
from werkzeug.exceptions import Unauthorized

from app import db
from app.auth.service_account_auth import resolve_service_account
from app.services.service_account_service import ServiceAccountService


class TestResolveServiceAccount:
    def test_missing_header_aborts_401(self, test_app):
        with test_app.test_request_context("/api/v1/shifts"):
            with pytest.raises(Unauthorized) as exc_info:
                resolve_service_account()
            assert exc_info.value.data["message"].startswith("Missing")

    def test_malformed_header_aborts_401(self, test_app):
        with test_app.test_request_context(
            "/api/v1/shifts", headers={"Authorization": "Basic xxx"}
        ):
            with pytest.raises(Unauthorized):
                resolve_service_account()

    def test_unknown_token_aborts_401(self, test_app):
        with test_app.test_request_context(
            "/api/v1/shifts", headers={"Authorization": "Bearer lsak_doesnotexist"}
        ):
            with pytest.raises(Unauthorized) as exc_info:
                resolve_service_account()
            assert "Invalid" in exc_info.value.data["message"]

    def test_valid_token_sets_g_service_account(self, test_app):
        with test_app.app_context():
            sa, full_token = ServiceAccountService.create_account("Zapier")
            db.session.commit()

        with test_app.test_request_context(
            "/api/v1/shifts", headers={"Authorization": f"Bearer {full_token}"}
        ):
            resolve_service_account()
            assert g.service_account.name == "Zapier"

    def test_valid_token_updates_last_used_at(self, test_app):
        with test_app.app_context():
            sa, full_token = ServiceAccountService.create_account("Zapier")
            db.session.commit()
            assert sa.last_used_at is None
            sa_id = sa.id

        with test_app.test_request_context(
            "/api/v1/shifts", headers={"Authorization": f"Bearer {full_token}"}
        ):
            resolve_service_account()

        with test_app.app_context():
            from app.repositories.service_account_repository import (
                ServiceAccountRepository,
            )

            refreshed = ServiceAccountRepository.get_by_id(sa_id)
            assert refreshed.last_used_at is not None

    def test_revoked_token_aborts_401(self, test_app):
        with test_app.app_context():
            sa, full_token = ServiceAccountService.create_account("Zapier")
            db.session.commit()
            ServiceAccountService.revoke(sa)
            db.session.commit()

        with test_app.test_request_context(
            "/api/v1/shifts", headers={"Authorization": f"Bearer {full_token}"}
        ):
            with pytest.raises(Unauthorized):
                resolve_service_account()

    def test_expired_token_aborts_401(self, test_app):
        with test_app.app_context():
            sa, full_token = ServiceAccountService.create_account(
                "Zapier",
                expires_at=datetime.now(timezone.utc).replace(tzinfo=None)
                - timedelta(days=1),
            )
            db.session.commit()

        with test_app.test_request_context(
            "/api/v1/shifts", headers={"Authorization": f"Bearer {full_token}"}
        ):
            with pytest.raises(Unauthorized):
                resolve_service_account()
