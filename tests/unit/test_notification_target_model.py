"""
Tests for the NotificationTarget model (app/models/notification_target.py):
categories JSON round-trip and the "empty categories = all" rule.
"""

from app.models import NotificationTarget


class TestCategories:
    def test_get_categories_empty_by_default(self):
        target = NotificationTarget(name="Test", apprise_url="json://localhost")
        assert target.get_categories() == []

    def test_set_and_get_categories_round_trip(self):
        target = NotificationTarget(name="Test", apprise_url="json://localhost")
        target.set_categories(["swap", "backup"])
        assert target.get_categories() == ["swap", "backup"]

    def test_set_empty_list_stores_none(self):
        target = NotificationTarget(name="Test", apprise_url="json://localhost")
        target.set_categories([])
        assert target.categories is None
        assert target.get_categories() == []

    def test_get_categories_invalid_json_returns_empty(self):
        target = NotificationTarget(name="Test", apprise_url="json://localhost")
        target.categories = "not json"
        assert target.get_categories() == []


class TestSubscribesTo:
    def test_empty_categories_subscribes_to_everything(self):
        target = NotificationTarget(name="Test", apprise_url="json://localhost")
        assert target.subscribes_to("swap") is True
        assert target.subscribes_to("backup") is True
        assert target.subscribes_to("system") is True

    def test_matching_category(self):
        target = NotificationTarget(name="Test", apprise_url="json://localhost")
        target.set_categories(["swap"])
        assert target.subscribes_to("swap") is True

    def test_non_matching_category(self):
        target = NotificationTarget(name="Test", apprise_url="json://localhost")
        target.set_categories(["swap"])
        assert target.subscribes_to("backup") is False
