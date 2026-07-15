"""
Tests for the k8s health endpoints (app/utils/health.py).

These routes are registered unconditionally in create_app() (no
feature flag), so they're testable directly via the standard test
client, with no special fixture.
"""

from unittest.mock import patch

from app.utils.health import check_database


class TestHealthEndpoint:
    def test_health_returns_ok(self, test_app, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "ok"
        assert data["application"] == "Leviia Schedule"
        assert "timestamp" in data


class TestReadyEndpoint:
    def test_ready_returns_ok_when_database_healthy(self, test_app, client):
        resp = client.get("/ready")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "ok"
        assert data["checks"]["database"] is True

    def test_ready_returns_503_when_database_unreachable(self, test_app, client):
        with patch("app.utils.health.check_database", return_value=False):
            resp = client.get("/ready")
        assert resp.status_code == 503
        data = resp.get_json()
        assert data["status"] == "not_ready"
        assert data["checks"]["database"] is False


class TestVersionEndpoint:
    def test_version_returns_info(self, test_app, client):
        resp = client.get("/version")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["application"] == "Leviia Schedule"
        assert "version" in data
        assert "environment" in data


class TestCheckDatabase:
    def test_check_database_true_on_healthy_connection(self, test_app):
        with test_app.app_context():
            assert check_database(test_app) is True

    def test_check_database_false_on_exception(self, test_app):
        with test_app.app_context():
            with patch("app.db.session.execute", side_effect=Exception("boom")):
                assert check_database(test_app) is False
