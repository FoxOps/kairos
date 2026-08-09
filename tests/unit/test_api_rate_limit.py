"""Tests for app/api/rate_limit.py::service_account_key() - the
Flask-Limiter key function for the public API, keyed by ServiceAccount
identity rather than IP (see the module's own docstring)."""

from types import SimpleNamespace

from app.api.rate_limit import service_account_key


class TestServiceAccountKey:
    def test_uses_service_account_id_when_present(self, test_app):
        with test_app.test_request_context("/"):
            from flask import g

            g.service_account = SimpleNamespace(id=42)
            assert service_account_key() == "service_account:42"

    def test_falls_back_to_remote_address_without_service_account(self, test_app):
        with test_app.test_request_context(
            "/", environ_base={"REMOTE_ADDR": "203.0.113.5"}
        ):
            assert service_account_key() == "203.0.113.5"
