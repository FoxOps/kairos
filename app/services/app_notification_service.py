"""
AppNotificationService for Leviia Schedule.

In-app notifications (bell icon in the sidebar) - creation is triggered
synchronously by other services on domain events (currently only
SwapService: new request -> admins, decision -> requester/target). This
is a new pattern in this app: NotificationService (app/services/
notification_service.py) only sends weekly reminder *emails* from cron
scripts, never from a request/response cycle - don't confuse the two.
"""

from app import db
from app.models import AppNotification, SwapRequest, User
from app.repositories.app_notification_repository import AppNotificationRepository
from app.repositories.user_repository import UserRepository


class AppNotificationService:
    """Logique métier pour les notifications internes à l'app."""

    @staticmethod
    def list_for_user(user_id: int) -> list[AppNotification]:
        return AppNotificationRepository.list_for_user(user_id)

    @staticmethod
    def count_unread(user_id: int) -> int:
        return AppNotificationRepository.count_unread(user_id)

    @staticmethod
    def mark_read(notification: AppNotification, user: User) -> str | None:
        """Marque une notification comme lue. None si succès."""
        if notification.user_id != user.id:
            return "Cette notification ne vous appartient pas"
        notification.mark_read()
        db.session.commit()
        return None

    @staticmethod
    def mark_all_read(user: User) -> None:
        AppNotificationRepository.mark_all_read_for_user(user.id)
        db.session.commit()

    @staticmethod
    def purge_read(user: User) -> int:
        """Supprime les notifications déjà lues de l'utilisateur. Retourne le nombre supprimé."""
        count = AppNotificationRepository.purge_read_for_user(user.id)
        db.session.commit()
        return count

    @staticmethod
    def _notify(user_id: int, notification_type: str, message: str, link: str) -> None:
        AppNotificationRepository.create(
            user_id=user_id,
            notification_type=notification_type,
            message=message,
            link=link,
        )

    @staticmethod
    def notify_admins_new_swap_request(swap_request: SwapRequest) -> None:
        message = (
            f"{swap_request.requester.name} propose un échange de shift à "
            f"{swap_request.target_user.name}, en attente de validation."
        )
        for admin in UserRepository.list_admins():
            AppNotificationService._notify(
                admin.id, "swap_request_created", message, "/admin/swaps"
            )
        db.session.commit()

    @staticmethod
    def notify_swap_decision(swap_request: SwapRequest, decision: str) -> None:
        """decision: SwapRequest.APPROVED, REJECTED, ou REVERTED."""
        if decision == SwapRequest.APPROVED:
            requester_message = (
                f"Votre demande d'échange avec {swap_request.target_user.name} "
                "a été approuvée."
            )
            target_message = (
                f"{swap_request.requester.name} et vous avez échangé un shift "
                "(approuvé par l'administrateur)."
            )
            AppNotificationService._notify(
                swap_request.requester_id, "swap_approved", requester_message, "/swaps"
            )
            AppNotificationService._notify(
                swap_request.target_user_id, "swap_approved", target_message, "/swaps"
            )
        elif decision == SwapRequest.REJECTED:
            requester_message = (
                f"Votre demande d'échange avec {swap_request.target_user.name} "
                "a été rejetée."
            )
            if swap_request.admin_comment:
                requester_message += f" Motif : {swap_request.admin_comment}"
            AppNotificationService._notify(
                swap_request.requester_id, "swap_rejected", requester_message, "/swaps"
            )
        elif decision == SwapRequest.REVERTED:
            requester_message = (
                f"L'échange approuvé avec {swap_request.target_user.name} a été "
                "annulé par l'administrateur, vos shifts d'origine sont restaurés."
            )
            target_message = (
                f"L'échange avec {swap_request.requester.name} a été annulé par "
                "l'administrateur, vos shifts d'origine sont restaurés."
            )
            AppNotificationService._notify(
                swap_request.requester_id, "swap_reverted", requester_message, "/swaps"
            )
            AppNotificationService._notify(
                swap_request.target_user_id, "swap_reverted", target_message, "/swaps"
            )
        db.session.commit()
