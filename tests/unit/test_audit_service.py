"""
Tests for AuditService (app/services/audit_service.py) - the single
write path for the audit trail (AuditLog table + logs/audit.log
dual-write).
"""

from unittest.mock import patch

from app.models import AuditLog
from app.services import AuditService


class TestLog:
    def test_writes_db_entry_with_explicit_actor(self, test_app, test_user):
        with test_app.app_context():
            AuditService.log(
                "shift.create",
                resource_type="Shift",
                resource_id=1,
                details="test",
                actor=test_user,
            )

            entries = AuditLog.query.all()
            assert len(entries) == 1
            assert entries[0].action == "shift.create"
            assert entries[0].actor_id == test_user.id
            assert entries[0].resource_type == "Shift"
            assert entries[0].resource_id == 1
            assert entries[0].details == "test"

    def test_no_actor_no_request_context_leaves_actor_null(self, test_app):
        with test_app.app_context():
            AuditService.log("setting.update")

            entries = AuditLog.query.all()
            assert len(entries) == 1
            assert entries[0].actor_id is None

    def test_resolves_actor_from_current_user_in_request_context(
        self, test_app, logged_in_client
    ):
        # logged_in_client performs a real login POST, establishing a
        # session current_user can resolve from within a request.
        with test_app.test_request_context("/"):
            from flask_login import login_user

            from app.models import User

            user = User.query.filter_by(email="login@example.com").first()
            login_user(user)

            AuditService.log("shift.create")

            entries = AuditLog.query.all()
            assert len(entries) == 1
            assert entries[0].actor_id == user.id

    def test_also_writes_to_file_audit_logger(self, test_app, test_user):
        with test_app.app_context():
            with patch("app.services.audit_service.log_audit_action") as mock_log:
                AuditService.log("shift.create", resource_type="Shift", actor=test_user)
                mock_log.assert_called_once()
                _, kwargs = mock_log.call_args
                assert kwargs["action"] == "shift.create"
                assert kwargs["user"] == test_user

    def test_failure_writing_entry_does_not_raise(self, test_app, test_user):
        with test_app.app_context():
            with patch(
                "app.services.audit_service.AuditLogRepository.create",
                side_effect=RuntimeError("db is down"),
            ):
                # Must not propagate - an audit trail bug must never
                # break the business action it's recording.
                AuditService.log("shift.create", actor=test_user)

            assert AuditLog.query.count() == 0
