"""
Tests for the admin notification targets UI
(app/routes/admin_notification_target_routes.py): CRUD, master toggle,
admin-only permission, and the test-send action.
"""

from unittest.mock import patch

from app import db
from app.models import AuditLog, NotificationTarget
from app.repositories.notification_target_repository import (
    NotificationTargetRepository,
)


class TestListRoute:
    def test_requires_admin(self, test_app, non_admin_client):
        resp = non_admin_client.get(
            "/admin/notification-targets", follow_redirects=False
        )
        assert resp.status_code == 302

    def test_lists_targets(self, test_app, logged_in_client):
        with test_app.app_context():
            NotificationTargetRepository.create("Slack", "json://localhost", True, [])
            db.session.commit()

        resp = logged_in_client.get("/admin/notification-targets")
        assert resp.status_code == 200
        assert b"Slack" in resp.data


class TestToggleMasterSwitch:
    def test_requires_admin(self, test_app, non_admin_client):
        resp = non_admin_client.post(
            "/admin/notification-targets/toggle", follow_redirects=False
        )
        assert resp.status_code == 302

    def test_enables_and_disables(self, test_app, logged_in_client):
        from app.services import SettingsService

        resp = logged_in_client.post(
            "/admin/notification-targets/toggle",
            data={"enabled": "on"},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        with test_app.app_context():
            assert SettingsService.get_apprise_notifications_enabled() is True

        resp = logged_in_client.post(
            "/admin/notification-targets/toggle", data={}, follow_redirects=True
        )
        assert resp.status_code == 200
        with test_app.app_context():
            assert SettingsService.get_apprise_notifications_enabled() is False


class TestAddTarget:
    def test_requires_admin(self, test_app, non_admin_client):
        resp = non_admin_client.get(
            "/admin/notification-targets/add", follow_redirects=False
        )
        assert resp.status_code == 302

    def test_creates_target(self, test_app, logged_in_client):
        resp = logged_in_client.post(
            "/admin/notification-targets/add",
            data={
                "name": "Discord",
                "apprise_url": "json://localhost",
                "categories": ["swap"],
                "enabled": "on",
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        with test_app.app_context():
            target = NotificationTarget.query.filter_by(name="Discord").first()
            assert target is not None
            assert target.get_categories() == ["swap"]

    def test_writes_audit_log_entry(self, test_app, logged_in_client):
        logged_in_client.post(
            "/admin/notification-targets/add",
            data={"name": "Discord", "apprise_url": "json://localhost"},
            follow_redirects=True,
        )
        with test_app.app_context():
            entry = AuditLog.query.filter_by(
                action="notification_target.create"
            ).first()
            assert entry is not None
            assert entry.details == "Discord"

    def test_missing_fields_rejected(self, test_app, logged_in_client):
        resp = logged_in_client.post(
            "/admin/notification-targets/add", data={}, follow_redirects=True
        )
        assert resp.status_code == 200
        with test_app.app_context():
            assert NotificationTarget.query.count() == 0


class TestEditTarget:
    def test_requires_admin(self, test_app, non_admin_client):
        with test_app.app_context():
            target = NotificationTargetRepository.create(
                "Slack", "json://localhost", True, []
            )
            db.session.commit()
            target_id = target.id

        resp = non_admin_client.get(
            f"/admin/notification-targets/edit/{target_id}", follow_redirects=False
        )
        assert resp.status_code == 302

    def test_updates_target(self, test_app, logged_in_client):
        with test_app.app_context():
            target = NotificationTargetRepository.create(
                "Slack", "json://localhost", True, []
            )
            db.session.commit()
            target_id = target.id

        resp = logged_in_client.post(
            f"/admin/notification-targets/edit/{target_id}",
            data={
                "name": "Slack renamed",
                "apprise_url": "json://localhost",
                "categories": ["backup"],
                "enabled": "on",
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        with test_app.app_context():
            updated = NotificationTargetRepository.get_by_id(target_id)
            assert updated.name == "Slack renamed"
            assert updated.get_categories() == ["backup"]

    def test_nonexistent_404(self, test_app, logged_in_client):
        resp = logged_in_client.get("/admin/notification-targets/edit/999999")
        assert resp.status_code == 404


class TestDeleteTarget:
    def test_requires_admin(self, test_app, non_admin_client):
        with test_app.app_context():
            target = NotificationTargetRepository.create(
                "Slack", "json://localhost", True, []
            )
            db.session.commit()
            target_id = target.id

        resp = non_admin_client.post(
            f"/admin/notification-targets/delete/{target_id}", follow_redirects=False
        )
        assert resp.status_code == 302

    def test_deletes_target(self, test_app, logged_in_client):
        with test_app.app_context():
            target = NotificationTargetRepository.create(
                "Slack", "json://localhost", True, []
            )
            db.session.commit()
            target_id = target.id

        resp = logged_in_client.post(
            f"/admin/notification-targets/delete/{target_id}", follow_redirects=True
        )
        assert resp.status_code == 200
        with test_app.app_context():
            assert NotificationTargetRepository.get_by_id(target_id) is None


class TestToggleEnabled:
    def test_toggles(self, test_app, logged_in_client):
        with test_app.app_context():
            target = NotificationTargetRepository.create(
                "Slack", "json://localhost", True, []
            )
            db.session.commit()
            target_id = target.id

        logged_in_client.post(
            f"/admin/notification-targets/{target_id}/toggle-enabled",
            follow_redirects=True,
        )
        with test_app.app_context():
            assert NotificationTargetRepository.get_by_id(target_id).enabled is False


class TestSendTest:
    def test_requires_admin(self, test_app, non_admin_client):
        with test_app.app_context():
            target = NotificationTargetRepository.create(
                "Slack", "json://localhost", True, []
            )
            db.session.commit()
            target_id = target.id

        resp = non_admin_client.post(
            f"/admin/notification-targets/{target_id}/test", follow_redirects=False
        )
        assert resp.status_code == 302

    def test_success_flashes_success(self, test_app, logged_in_client):
        with test_app.app_context():
            target = NotificationTargetRepository.create(
                "Slack", "json://localhost", True, []
            )
            db.session.commit()
            target_id = target.id

        with patch(
            "app.routes.admin_notification_target_routes."
            "AppriseNotificationService.send_test",
            return_value=(True, None),
        ):
            resp = logged_in_client.post(
                f"/admin/notification-targets/{target_id}/test",
                follow_redirects=True,
            )
        assert resp.status_code == 200
        assert "succès".encode() in resp.data

    def test_failure_flashes_error(self, test_app, logged_in_client):
        with test_app.app_context():
            target = NotificationTargetRepository.create(
                "Slack", "json://localhost", True, []
            )
            db.session.commit()
            target_id = target.id

        with patch(
            "app.routes.admin_notification_target_routes."
            "AppriseNotificationService.send_test",
            return_value=(False, "boom"),
        ):
            resp = logged_in_client.post(
                f"/admin/notification-targets/{target_id}/test",
                follow_redirects=True,
            )
        assert resp.status_code == 200
        assert b"boom" in resp.data
