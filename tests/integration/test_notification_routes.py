"""
Tests d'intégration pour les routes de notifications internes à l'app
(notification_routes.py).
"""

from app import db
from app.repositories.app_notification_repository import AppNotificationRepository


class TestNotificationsPage:
    def test_requires_login(self, test_app, client):
        resp = client.get("/notifications")
        assert resp.status_code in (302, 401)

    def test_lists_own_notifications(self, test_app, non_admin_client, test_user):
        with test_app.app_context():
            AppNotificationRepository.create(
                test_user.id, "swap_approved", "Votre échange a été approuvé", "/swaps"
            )
            db.session.commit()

        resp = non_admin_client.get("/notifications")
        assert resp.status_code == 200
        assert "Votre échange a été approuvé".encode() in resp.data

    def test_does_not_list_other_users_notifications(
        self, test_app, non_admin_client, second_user
    ):
        with test_app.app_context():
            AppNotificationRepository.create(
                second_user.id, "swap_approved", "Message privé à Second User"
            )
            db.session.commit()

        resp = non_admin_client.get("/notifications")
        assert resp.status_code == 200
        assert "Message privé à Second User".encode() not in resp.data


class TestMarkNotificationRead:
    def test_mark_read_redirects_to_link(self, test_app, non_admin_client, test_user):
        with test_app.app_context():
            notification = AppNotificationRepository.create(
                test_user.id, "swap_approved", "Test", link="/swaps"
            )
            db.session.commit()
            notification_id = notification.id

        resp = non_admin_client.post(
            f"/notifications/{notification_id}/read", follow_redirects=False
        )
        assert resp.status_code == 302
        assert resp.headers.get("Location") == "/swaps"

        with test_app.app_context():
            updated = AppNotificationRepository.get_by_id(notification_id)
            assert updated.read_at is not None

    def test_mark_read_nonexistent_404(self, test_app, non_admin_client):
        resp = non_admin_client.post("/notifications/999999/read")
        assert resp.status_code == 404

    def test_cannot_mark_other_users_notification_read(
        self, test_app, non_admin_client, second_user
    ):
        with test_app.app_context():
            notification = AppNotificationRepository.create(
                second_user.id, "swap_approved", "Pas à toi"
            )
            db.session.commit()
            notification_id = notification.id

        resp = non_admin_client.post(f"/notifications/{notification_id}/read")
        assert resp.status_code == 403
        with test_app.app_context():
            updated = AppNotificationRepository.get_by_id(notification_id)
            assert updated.read_at is None


class TestMarkAllNotificationsRead:
    def test_marks_all_own_unread(self, test_app, non_admin_client, test_user):
        with test_app.app_context():
            AppNotificationRepository.create(test_user.id, "swap_approved", "A")
            AppNotificationRepository.create(test_user.id, "swap_approved", "B")
            db.session.commit()

        resp = non_admin_client.post("/notifications/read-all", follow_redirects=True)
        assert resp.status_code == 200

        with test_app.app_context():
            from app.services import AppNotificationService

            assert AppNotificationService.count_unread(test_user.id) == 0


class TestPurgeNotifications:
    def test_purge_deletes_read_only(self, test_app, non_admin_client, test_user):
        with test_app.app_context():
            read_notif = AppNotificationRepository.create(
                test_user.id, "swap_approved", "Lue"
            )
            AppNotificationRepository.create(test_user.id, "swap_approved", "Non lue")
            db.session.commit()
            read_notif.mark_read()
            db.session.commit()

        resp = non_admin_client.post("/notifications/purge", follow_redirects=True)
        assert resp.status_code == 200

        with test_app.app_context():
            from app.models import AppNotification

            assert AppNotification.query.filter_by(user_id=test_user.id).count() == 1
