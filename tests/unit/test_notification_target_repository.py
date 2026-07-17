"""
Tests for NotificationTargetRepository
(app/repositories/notification_target_repository.py).
"""

from app import db
from app.models import NotificationTarget
from app.repositories.notification_target_repository import (
    NotificationTargetRepository,
)


class TestCreate:
    def test_creates_target_with_categories(self, test_app):
        with test_app.app_context():
            target = NotificationTargetRepository.create(
                name="Slack",
                apprise_url="json://localhost",
                enabled=True,
                categories=["swap", "backup"],
            )
            db.session.commit()

            fetched = db.session.get(NotificationTarget, target.id)
            assert fetched.name == "Slack"
            assert fetched.apprise_url == "json://localhost"
            assert fetched.enabled is True
            assert fetched.get_categories() == ["swap", "backup"]

    def test_creates_target_with_no_categories(self, test_app):
        with test_app.app_context():
            target = NotificationTargetRepository.create(
                name="Discord",
                apprise_url="json://localhost",
                enabled=True,
                categories=[],
            )
            db.session.commit()

            fetched = db.session.get(NotificationTarget, target.id)
            assert fetched.categories is None


class TestGetAll:
    def test_orders_by_name(self, test_app):
        with test_app.app_context():
            NotificationTargetRepository.create("Zeta", "json://localhost", True, [])
            NotificationTargetRepository.create("Alpha", "json://localhost", True, [])
            db.session.commit()

            targets = NotificationTargetRepository.get_all()
            assert [t.name for t in targets] == ["Alpha", "Zeta"]


class TestGetByIds:
    def test_returns_matching_targets_in_one_bulk_query(self, test_app):
        with test_app.app_context():
            first = NotificationTargetRepository.create(
                "Slack", "json://localhost", True, []
            )
            second = NotificationTargetRepository.create(
                "Discord", "json://localhost", True, []
            )
            NotificationTargetRepository.create(
                "Not requested", "json://localhost", True, []
            )
            db.session.commit()

            targets = NotificationTargetRepository.get_by_ids([first.id, second.id])
            assert {t.id for t in targets} == {first.id, second.id}

    def test_empty_list_returns_empty_list_without_querying(self, test_app):
        with test_app.app_context():
            assert NotificationTargetRepository.get_by_ids([]) == []


class TestDelete:
    def test_deletes_target(self, test_app):
        with test_app.app_context():
            target = NotificationTargetRepository.create(
                "Slack", "json://localhost", True, []
            )
            db.session.commit()
            target_id = target.id

            NotificationTargetRepository.delete(target)
            db.session.commit()

            assert NotificationTargetRepository.get_by_id(target_id) is None


class TestListEnabledForCategory:
    def test_disabled_target_excluded(self, test_app):
        with test_app.app_context():
            NotificationTargetRepository.create(
                "Slack", "json://localhost", False, ["swap"]
            )
            db.session.commit()

            assert NotificationTargetRepository.list_enabled_for_category("swap") == []

    def test_matching_category_included(self, test_app):
        with test_app.app_context():
            NotificationTargetRepository.create(
                "Slack", "json://localhost", True, ["swap"]
            )
            db.session.commit()

            targets = NotificationTargetRepository.list_enabled_for_category("swap")
            assert len(targets) == 1

    def test_non_matching_category_excluded(self, test_app):
        with test_app.app_context():
            NotificationTargetRepository.create(
                "Slack", "json://localhost", True, ["backup"]
            )
            db.session.commit()

            assert NotificationTargetRepository.list_enabled_for_category("swap") == []

    def test_empty_categories_matches_everything(self, test_app):
        with test_app.app_context():
            NotificationTargetRepository.create("Slack", "json://localhost", True, [])
            db.session.commit()

            assert (
                len(NotificationTargetRepository.list_enabled_for_category("swap")) == 1
            )
            assert (
                len(NotificationTargetRepository.list_enabled_for_category("backup"))
                == 1
            )
