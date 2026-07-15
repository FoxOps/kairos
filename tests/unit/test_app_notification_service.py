"""
Tests for AppNotificationService: in-app notifications created by
SwapService on shift-swap events.
"""

from app import db
from app.models import AppNotification
from app.repositories.app_notification_repository import AppNotificationRepository
from app.services import AppNotificationService, SwapService


class TestNotifyAdminsNewSwapRequest:
    def test_notifies_all_admins(
        self, test_app, test_user, second_user, admin_user, test_swap_shift
    ):
        with test_app.app_context():
            swap_request, error = SwapService.request_swap(
                test_user, test_swap_shift, second_user
            )
            assert error is None

            notifications = AppNotification.query.filter_by(user_id=admin_user.id).all()
            assert len(notifications) == 1
            assert notifications[0].notification_type == "swap_request_created"
            assert notifications[0].link == "/admin/swaps"
            assert test_user.name in notifications[0].message

    def test_target_and_requester_not_notified_on_creation(
        self, test_app, test_user, second_user, admin_user, test_swap_shift
    ):
        with test_app.app_context():
            SwapService.request_swap(test_user, test_swap_shift, second_user)

            assert AppNotification.query.filter_by(user_id=test_user.id).count() == 0
            assert AppNotification.query.filter_by(user_id=second_user.id).count() == 0


class TestNotifySwapDecision:
    def test_approve_notifies_requester_and_target(
        self, test_app, test_swap_request, admin_user, test_user, second_user
    ):
        with test_app.app_context():
            SwapService.approve_swap(test_swap_request, admin_user)

            requester_notif = AppNotification.query.filter_by(
                user_id=test_user.id, notification_type="swap_approved"
            ).first()
            target_notif = AppNotification.query.filter_by(
                user_id=second_user.id, notification_type="swap_approved"
            ).first()
            assert requester_notif is not None
            assert target_notif is not None
            assert requester_notif.link == "/swaps"

    def test_reject_notifies_only_requester(
        self, test_app, test_swap_request, admin_user, test_user, second_user
    ):
        with test_app.app_context():
            SwapService.reject_swap(test_swap_request, admin_user, reason="Non")

            assert (
                AppNotification.query.filter_by(
                    user_id=test_user.id, notification_type="swap_rejected"
                ).count()
                == 1
            )
            assert (
                AppNotification.query.filter_by(
                    user_id=second_user.id, notification_type="swap_rejected"
                ).count()
                == 0
            )

    def test_reject_message_includes_reason(
        self, test_app, test_swap_request, admin_user, test_user
    ):
        with test_app.app_context():
            SwapService.reject_swap(
                test_swap_request, admin_user, reason="Effectif insuffisant"
            )
            notif = AppNotification.query.filter_by(user_id=test_user.id).first()
            assert "Effectif insuffisant" in notif.message

    def test_revert_notifies_requester_and_target(
        self, test_app, test_swap_request, admin_user, test_user, second_user
    ):
        with test_app.app_context():
            SwapService.approve_swap(test_swap_request, admin_user)
            SwapService.revert_swap(test_swap_request, admin_user)

            assert (
                AppNotification.query.filter_by(
                    user_id=test_user.id, notification_type="swap_reverted"
                ).count()
                == 1
            )
            assert (
                AppNotification.query.filter_by(
                    user_id=second_user.id, notification_type="swap_reverted"
                ).count()
                == 1
            )


class TestReadState:
    def test_count_unread(self, test_app, test_user):
        with test_app.app_context():
            AppNotificationRepository.create(test_user.id, "swap_approved", "A")
            AppNotificationRepository.create(test_user.id, "swap_approved", "B")
            db.session.commit()

            assert AppNotificationService.count_unread(test_user.id) == 2

    def test_mark_read_by_owner(self, test_app, test_user):
        with test_app.app_context():
            notification = AppNotificationRepository.create(
                test_user.id, "swap_approved", "A"
            )
            db.session.commit()

            error = AppNotificationService.mark_read(notification, test_user)
            assert error is None
            assert notification.read_at is not None

    def test_mark_read_by_non_owner_denied(self, test_app, test_user, second_user):
        with test_app.app_context():
            notification = AppNotificationRepository.create(
                test_user.id, "swap_approved", "A"
            )
            db.session.commit()

            error = AppNotificationService.mark_read(notification, second_user)
            assert error is not None
            assert notification.read_at is None

    def test_mark_all_read(self, test_app, test_user):
        with test_app.app_context():
            AppNotificationRepository.create(test_user.id, "swap_approved", "A")
            AppNotificationRepository.create(test_user.id, "swap_approved", "B")
            db.session.commit()

            AppNotificationService.mark_all_read(test_user)
            assert AppNotificationService.count_unread(test_user.id) == 0


class TestPurgeRead:
    def test_purge_deletes_only_read(self, test_app, test_user):
        with test_app.app_context():
            read_notif = AppNotificationRepository.create(
                test_user.id, "swap_approved", "Lue"
            )
            AppNotificationRepository.create(test_user.id, "swap_approved", "Non lue")
            db.session.commit()
            read_notif.mark_read()
            db.session.commit()

            count = AppNotificationService.purge_read(test_user)
            assert count == 1
            assert AppNotification.query.filter_by(user_id=test_user.id).count() == 1
            assert AppNotificationService.count_unread(test_user.id) == 1

    def test_purge_ignores_other_users(self, test_app, test_user, second_user):
        with test_app.app_context():
            notif = AppNotificationRepository.create(
                second_user.id, "swap_approved", "Lue"
            )
            db.session.commit()
            notif.mark_read()
            db.session.commit()

            count = AppNotificationService.purge_read(test_user)
            assert count == 0
            assert AppNotification.query.filter_by(user_id=second_user.id).count() == 1
