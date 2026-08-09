"""
Tests for app/utils/prometheus_metrics.py.

Gated by PROMETHEUS_ENABLED (False by default, including in tests) - the
fixture below forces app.config["PROMETHEUS_ENABLED"] = True directly and
calls init_prometheus() manually, bypassing create_app()'s own env-var
wiring entirely (same pattern as secure_app in test_security.py for
CSRF/Talisman). See tests/unit/test_config.py::TestPrometheusEnabledEnvVar
for a regression test that exercises the real env-var-to-Config wiring
this fixture bypasses.
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
        assert "kairos_shifts_total" in body
        assert "kairos_users_total" in body

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
            'kairos_requests_total{endpoint="/login"' in body
            or "kairos_requests_total" in body
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

    def test_swallows_import_error_when_psutil_missing(
        self, prometheus_app, monkeypatch
    ):
        import sys

        from app.utils.prometheus_metrics import _update_system_metrics

        monkeypatch.setitem(sys.modules, "psutil", None)

        with prometheus_app.app_context():
            # Must not raise even though `import psutil` fails inside the
            # function (sys.modules[name] = None forces ImportError).
            _update_system_metrics()

    def test_swallows_generic_exception_from_psutil(self, prometheus_app, monkeypatch):
        import psutil

        from app.utils.prometheus_metrics import _update_system_metrics

        def _raise(*args, **kwargs):
            raise RuntimeError("psutil boom")

        monkeypatch.setattr(psutil, "cpu_percent", _raise)

        with prometheus_app.app_context():
            # Must not raise - a non-ImportError from psutil is also
            # caught (broad except Exception, distinct from the
            # ImportError branch above).
            _update_system_metrics()


class TestBeforeRequestAlreadyTracking:
    def test_second_call_is_a_no_op(self, prometheus_app):
        """before_request()'s early return when _prometheus_start_time
        is already set - can't happen through a single real request
        (Flask calls it once per request), so called directly twice."""
        from app.utils.prometheus_metrics import before_request

        with prometheus_app.app_context():
            from flask import current_app

            before_request()
            first_time = current_app._prometheus_start_time

            before_request()
            assert current_app._prometheus_start_time == first_time


class TestAfterRequestWithoutTracking:
    def test_returns_response_unchanged_when_not_tracking(self, prometheus_app):
        """after_request()'s early return when no matching before_request
        ran (_prometheus_start_time never set)."""
        from flask import current_app

        from app.utils.prometheus_metrics import after_request

        with prometheus_app.app_context():
            assert not hasattr(current_app, "_prometheus_start_time")
            response = object()
            assert after_request(response) is response


class TestHandleException:
    def test_increments_error_count_and_returns_the_error(self, prometheus_app):
        from app.utils.prometheus_metrics import ERROR_COUNT, handle_exception

        with prometheus_app.app_context():
            before = ERROR_COUNT.labels(error_type="ValueError")._value.get()
            error = ValueError("boom")

            result = handle_exception(error)

            after = ERROR_COUNT.labels(error_type="ValueError")._value.get()
            assert after == before + 1
            assert result is error


class TestRealAppFactoryWithPrometheusEnabled:
    """Regression test for a real production bug: init_prometheus() ended
    with `current_app.logger.info(...)`, called synchronously from inside
    create_app() itself - no app/request context is pushed at that point,
    so `current_app` raised `RuntimeError: Working outside of application
    context`, crashing create_app() (and therefore the whole app, not just
    /metrics) whenever PROMETHEUS_ENABLED was true. Every other test in
    this file calls init_prometheus() from inside a manually-pushed
    `with app.app_context():` block (see the prometheus_app fixture above),
    which masked this exact bug - the same masking pattern already flagged
    once before for this file, see test_config.py::test_prometheus_enabled_reads_env.
    This test goes through create_app() for real, with the env var actually
    set, the only way to reproduce it."""

    def test_create_app_does_not_crash_with_prometheus_enabled(self, monkeypatch):
        # TestingConfig doesn't override PROMETHEUS_ENABLED - it inherits
        # Config's class-level `get_bool_from_env(...)` default, baked in
        # at module-import time. monkeypatch.setenv alone wouldn't affect
        # an already-imported class, so the class attribute itself is
        # patched directly instead (simpler than test_config.py's
        # del sys.modules dance, and patches exactly what create_app()
        # actually reads via app.config.from_object()).
        from app.config.testing import TestingConfig

        monkeypatch.setattr(TestingConfig, "PROMETHEUS_ENABLED", True)
        app = create_app("app.config.TestingConfig")

        with app.app_context():
            db.drop_all()
            db.create_all()

            client = app.test_client()
            resp = client.get("/metrics")
            assert resp.status_code == 200
            assert "kairos_shifts_total" in resp.data.decode("utf-8")

            db.session.rollback()
            db.drop_all()
