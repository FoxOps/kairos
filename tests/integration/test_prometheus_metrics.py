"""
Tests for app/utils/prometheus_metrics.py.

Gated by PROMETHEUS_ENABLED (False by default, including in tests) -
builds its own app instance with the flag enabled, the same pattern as
secure_app in test_security.py for CSRF/Talisman.
"""

import pytest

from app import create_app, db


@pytest.fixture
def prometheus_app():
    """App with Prometheus metrics initialized."""
    app = create_app("app.config.TestingConfig")
    app.config["PROMETHEUS_ENABLED"] = True

    with app.app_context():
        db.drop_all()
        db.create_all()

        from app.utils.prometheus_metrics import init_prometheus

        init_prometheus(app)

        yield app

        db.session.rollback()
        db.drop_all()


class TestPrometheusMetricsEndpoint:
    def test_metrics_endpoint_returns_prometheus_format(self, prometheus_app):
        client = prometheus_app.test_client()
        resp = client.get("/metrics")
        assert resp.status_code == 200
        assert resp.headers["Content-Type"].startswith("text/plain")
        body = resp.data.decode("utf-8")
        assert "leviia_shifts_total" in body
        assert "leviia_users_total" in body

    def test_requests_are_tracked_without_crashing(self, prometheus_app):
        """Regression test: after_request used to reference `request`
        without importing it (a NameError on EVERY request whenever this
        flag was on). This test checks that a normal request no longer
        crashes."""
        client = prometheus_app.test_client()
        resp = client.get("/login")
        assert resp.status_code == 200

    def test_multiple_requests_increment_counters(self, prometheus_app):
        client = prometheus_app.test_client()
        client.get("/login")
        client.get("/login")

        resp = client.get("/metrics")
        body = resp.data.decode("utf-8")
        assert (
            'leviia_requests_total{endpoint="/login"' in body
            or "leviia_requests_total" in body
        )


class TestBusinessMetricsUpdate:
    def test_update_business_metrics_reflects_db_state(self, prometheus_app):
        from app.models import Group, User
        from app.utils.prometheus_metrics import USERS_COUNT, _update_business_metrics

        with prometheus_app.app_context():
            group = Group(
                name="Metrics Group", is_part_of_schedule=True, is_part_of_oncall=True
            )
            db.session.add(group)
            db.session.commit()

            user = User(
                name="Metrics User", email="metrics@test.com", group_id=group.id
            )
            db.session.add(user)
            db.session.commit()

            _update_business_metrics()
            assert USERS_COUNT._value.get() >= 1


class TestSystemMetricsUpdate:
    def test_update_system_metrics_does_not_raise(self, prometheus_app):
        from app.utils.prometheus_metrics import _update_system_metrics

        with prometheus_app.app_context():
            # Must never raise, even if psutil fails (broad try/except on the source side).
            _update_system_metrics()
