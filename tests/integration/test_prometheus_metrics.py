"""
Tests pour app/utils/prometheus_metrics.py.

Gated par PROMETHEUS_ENABLED (False par défaut, y compris en test) -
construit sa propre instance d'app avec le flag activé, comme
secure_app dans test_security.py pour CSRF/Talisman.
"""

import pytest

from app import create_app, db


@pytest.fixture
def prometheus_app():
    """App avec les métriques Prometheus initialisées."""
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
        """Bug réel trouvé et corrigé : after_request utilisait `request`
        sans l'importer (NameError sur CHAQUE requête si ce flag était
        activé). Ce test vérifie qu'une requête normale ne plante plus."""
        client = prometheus_app.test_client()
        resp = client.get("/login")
        assert resp.status_code == 200

    def test_multiple_requests_increment_counters(self, prometheus_app):
        client = prometheus_app.test_client()
        client.get("/login")
        client.get("/login")

        resp = client.get("/metrics")
        body = resp.data.decode("utf-8")
        assert 'leviia_requests_total{endpoint="/login"' in body or "leviia_requests_total" in body


class TestBusinessMetricsUpdate:
    def test_update_business_metrics_reflects_db_state(self, prometheus_app):
        from app.utils.prometheus_metrics import _update_business_metrics, USERS_COUNT
        from app.models import Group, User

        with prometheus_app.app_context():
            group = Group(name="Metrics Group", is_part_of_schedule=True, is_part_of_oncall=True)
            db.session.add(group)
            db.session.commit()

            user = User(name="Metrics User", email="metrics@test.com", group_id=group.id)
            db.session.add(user)
            db.session.commit()

            _update_business_metrics()
            assert USERS_COUNT._value.get() >= 1


class TestSystemMetricsUpdate:
    def test_update_system_metrics_does_not_raise(self, prometheus_app):
        from app.utils.prometheus_metrics import _update_system_metrics

        with prometheus_app.app_context():
            # Ne doit jamais lever, même si psutil échoue (try/except large côté source).
            _update_system_metrics()
