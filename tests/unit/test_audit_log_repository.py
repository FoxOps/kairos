"""
Tests for AuditLogRepository (app/repositories/audit_log_repository.py).
"""

from datetime import date, datetime, timedelta

from app import db
from app.models import AuditLog
from app.repositories.audit_log_repository import AuditLogRepository


class TestCreate:
    def test_creates_entry_with_all_fields(self, test_app, test_user):
        with test_app.app_context():
            entry = AuditLogRepository.create(
                actor_id=test_user.id,
                action="shift.create",
                resource_type="Shift",
                resource_id=1,
                details="test details",
                ip_address="127.0.0.1",
            )
            db.session.commit()

            assert entry.id is not None
            fetched = db.session.get(AuditLog, entry.id)
            assert fetched.actor_id == test_user.id
            assert fetched.action == "shift.create"
            assert fetched.resource_type == "Shift"
            assert fetched.resource_id == 1
            assert fetched.details == "test details"
            assert fetched.ip_address == "127.0.0.1"

    def test_creates_entry_with_null_actor(self, test_app):
        with test_app.app_context():
            entry = AuditLogRepository.create(actor_id=None, action="setting.update")
            db.session.commit()

            fetched = db.session.get(AuditLog, entry.id)
            assert fetched.actor_id is None


class TestListPaginated:
    def test_orders_newest_first(self, test_app, test_user):
        with test_app.app_context():
            AuditLogRepository.create(actor_id=test_user.id, action="shift.create")
            AuditLogRepository.create(actor_id=test_user.id, action="shift.delete")
            db.session.commit()

            page = AuditLogRepository.list_paginated(page=1, per_page=10)
            assert page.total == 2
            assert page.items[0].action == "shift.delete"
            assert page.items[1].action == "shift.create"

    def test_filters_by_actor_id(self, test_app, test_user, second_user):
        with test_app.app_context():
            AuditLogRepository.create(actor_id=test_user.id, action="shift.create")
            AuditLogRepository.create(actor_id=second_user.id, action="shift.delete")
            db.session.commit()

            page = AuditLogRepository.list_paginated(
                page=1, per_page=10, actor_id=test_user.id
            )
            assert page.total == 1
            assert page.items[0].actor_id == test_user.id

    def test_filters_by_action_prefix(self, test_app, test_user):
        with test_app.app_context():
            AuditLogRepository.create(actor_id=test_user.id, action="shift.create")
            AuditLogRepository.create(actor_id=test_user.id, action="user.create")
            db.session.commit()

            page = AuditLogRepository.list_paginated(
                page=1, per_page=10, action_prefix="shift."
            )
            assert page.total == 1
            assert page.items[0].action == "shift.create"

    def test_filters_by_date_range(self, test_app, test_user):
        with test_app.app_context():
            entry = AuditLogRepository.create(
                actor_id=test_user.id, action="shift.create"
            )
            db.session.commit()
            # Force created_at to a known past date to test the boundary.
            entry.created_at = datetime(2020, 1, 1, 12, 0, 0)
            db.session.commit()

            in_range = AuditLogRepository.list_paginated(
                page=1,
                per_page=10,
                date_from=date(2020, 1, 1),
                date_to=date(2020, 1, 1),
            )
            assert in_range.total == 1

            out_of_range = AuditLogRepository.list_paginated(
                page=1,
                per_page=10,
                date_from=date(2020, 1, 2),
            )
            assert out_of_range.total == 0


class TestDeleteOlderThan:
    def test_deletes_only_older_entries(self, test_app, test_user):
        with test_app.app_context():
            old_entry = AuditLogRepository.create(
                actor_id=test_user.id, action="shift.create"
            )
            recent_entry = AuditLogRepository.create(
                actor_id=test_user.id, action="shift.delete"
            )
            db.session.commit()
            old_entry_id = old_entry.id
            recent_entry_id = recent_entry.id
            old_entry.created_at = datetime.now() - timedelta(days=100)
            db.session.commit()

            deleted = AuditLogRepository.delete_older_than(
                datetime.now() - timedelta(days=30)
            )
            db.session.commit()

            assert deleted == 1
            assert AuditLog.query.filter_by(id=old_entry_id).first() is None
            assert AuditLog.query.filter_by(id=recent_entry_id).first() is not None
