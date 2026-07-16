"""
Tests for the admin audit trail consultation page
(app/routes/admin_audit_routes.py): listing, filters, pagination,
admin-only permission, and the retention-based purge action.
"""

from datetime import datetime, timedelta

from app.models import AuditLog
from app.services import AuditService, SettingsService


class TestAuditLogRoute:
    def test_requires_admin(self, test_app, non_admin_client):
        resp = non_admin_client.get("/admin/audit-log", follow_redirects=False)
        assert resp.status_code == 302

    def test_lists_entries(self, test_app, logged_in_client, test_user):
        with test_app.app_context():
            AuditService.log("shift.create", actor=test_user)

        resp = logged_in_client.get("/admin/audit-log")
        assert resp.status_code == 200
        assert b"shift.create" in resp.data

    def test_filters_by_actor(self, test_app, logged_in_client, test_user):
        with test_app.app_context():
            AuditService.log("shift.create", actor=test_user)

        resp = logged_in_client.get(f"/admin/audit-log?actor_id={test_user.id}")
        assert resp.status_code == 200
        assert b"shift.create" in resp.data

    def test_filters_by_action_domain(self, test_app, logged_in_client, test_user):
        with test_app.app_context():
            AuditService.log("shift.create", actor=test_user)
            AuditService.log("user.update", actor=test_user)

        resp = logged_in_client.get("/admin/audit-log?action_domain=shift")
        assert resp.status_code == 200
        assert b"shift.create" in resp.data
        assert b"user.update" not in resp.data

    def test_filters_by_date_range_excludes_out_of_range_entries(
        self, test_app, logged_in_client, test_user
    ):
        with test_app.app_context():
            from app import db

            AuditService.log("shift.create", actor=test_user)
            old_entry = AuditLog.query.filter_by(action="shift.create").first()
            old_entry.created_at = datetime.utcnow() - timedelta(days=30)
            db.session.commit()

        far_future = (datetime.utcnow() + timedelta(days=1)).strftime("%Y-%m-%d")
        resp = logged_in_client.get(f"/admin/audit-log?date_from={far_future}")
        assert resp.status_code == 200
        assert b"Aucune entr" in resp.data


class TestPurgeAuditLog:
    def test_purge_without_retention_configured_refuses(
        self, test_app, logged_in_client, test_user
    ):
        with test_app.app_context():
            AuditService.log("shift.create", actor=test_user)

        resp = logged_in_client.post("/admin/audit-log/purge", follow_redirects=True)
        assert resp.status_code == 200
        with test_app.app_context():
            assert AuditLog.query.filter_by(action="shift.create").count() == 1

    def test_purge_with_retention_configured_deletes_old_entries(
        self, test_app, logged_in_client, test_user
    ):
        with test_app.app_context():
            SettingsService.set_audit_log_retention_days(7)
            AuditService.log("shift.create", actor=test_user)
            old_entry = AuditLog.query.filter_by(action="shift.create").first()
            old_entry.created_at = datetime.utcnow() - timedelta(days=30)
            from app import db

            db.session.commit()

        resp = logged_in_client.post("/admin/audit-log/purge", follow_redirects=True)
        assert resp.status_code == 200
        with test_app.app_context():
            assert AuditLog.query.filter_by(action="shift.create").count() == 0

    def test_purge_requires_admin(self, test_app, non_admin_client):
        resp = non_admin_client.post("/admin/audit-log/purge", follow_redirects=False)
        assert resp.status_code == 302
