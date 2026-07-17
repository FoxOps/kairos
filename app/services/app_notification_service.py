"""
AppNotificationService for Leviia Schedule.

In-app notifications (bell icon in the sidebar) - creation is triggered
synchronously by other services on domain events (SwapService: new
request -> admins, decision -> requester/target; on-call automation:
generation gap -> admins, see notify_admins_oncall_gap()). This is a
pattern distinct from NotificationService (app/services/
notification_service.py), which only sends weekly reminder *emails*
from cron scripts, never from a request/response cycle - don't confuse
the two.
"""

from datetime import date

from flask_babel import force_locale
from flask_babel import gettext as _

from app import db
from app.models import AppNotification, SwapRequest, User
from app.repositories.app_notification_repository import AppNotificationRepository
from app.repositories.user_repository import UserRepository


class AppNotificationService:
    """Business logic for in-app notifications."""

    @staticmethod
    def list_for_user(user_id: int) -> list[AppNotification]:
        return AppNotificationRepository.list_for_user(user_id)

    @staticmethod
    def count_unread(user_id: int) -> int:
        return AppNotificationRepository.count_unread(user_id)

    @staticmethod
    def mark_read(notification: AppNotification, user: User) -> str | None:
        """Mark a notification as read. None on success."""
        if notification.user_id != user.id:
            return _("Cette notification ne vous appartient pas")
        notification.mark_read()
        db.session.commit()
        return None

    @staticmethod
    def mark_all_read(user: User) -> None:
        AppNotificationRepository.mark_all_read_for_user(user.id)
        db.session.commit()

    @staticmethod
    def purge_read(user: User) -> int:
        """Delete the user's already-read notifications. Returns the number deleted."""
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
    def notify_target_confirmation_needed(swap_request: SwapRequest) -> None:
        """A new request needs the target's own confirmation before it can
        even reach the admin - notifies only the target, not admins (see
        notify_admins_new_swap_request(), now triggered later, once the
        target has confirmed)."""
        with force_locale(swap_request.target_user.effective_language()):
            message = _(
                "%(requester)s vous propose un échange de shift, à confirmer.",
                requester=swap_request.requester.name,
            )
        AppNotificationService._notify(
            swap_request.target_user_id, "swap_confirmation_needed", message, "/swaps"
        )
        db.session.commit()

    @staticmethod
    def notify_target_rejection(swap_request: SwapRequest) -> None:
        """The target declined the exchange before it ever reached the
        admin - notifies only the requester (nothing changed for the
        target, same reasoning as the REJECTED branch of
        notify_swap_decision() below, which only fires for an admin
        rejection)."""
        with force_locale(swap_request.requester.effective_language()):
            message = _(
                "%(name)s n'a pas retenu votre proposition d'échange.",
                name=swap_request.target_user.name,
            )
            if swap_request.admin_comment:
                message += _(" Motif : %(comment)s", comment=swap_request.admin_comment)
        AppNotificationService._notify(
            swap_request.requester_id, "swap_target_rejected", message, "/swaps"
        )
        db.session.commit()

    @staticmethod
    def notify_admins_new_swap_request(swap_request: SwapRequest) -> None:
        # Persisted message, read later by potentially a different user
        # than whoever triggered this event - each admin may have their
        # own language preference, so build the message per-recipient
        # inside force_locale() rather than once upfront (unlike a plain
        # flash(), which renders immediately in the acting request's own
        # locale and needs no such per-recipient handling).
        for admin in UserRepository.list_admins():
            with force_locale(admin.effective_language()):
                message = _(
                    "%(requester)s propose un échange de shift à %(target)s, en "
                    "attente de validation.",
                    requester=swap_request.requester.name,
                    target=swap_request.target_user.name,
                )
            AppNotificationService._notify(
                admin.id, "swap_request_created", message, "/admin/swaps"
            )
        db.session.commit()

    @staticmethod
    def notify_swap_decision(swap_request: SwapRequest, decision: str) -> None:
        """decision: SwapRequest.APPROVED, REJECTED, or REVERTED."""
        if decision == SwapRequest.APPROVED:
            with force_locale(swap_request.requester.effective_language()):
                requester_message = _(
                    "Votre demande d'échange avec %(name)s a été approuvée.",
                    name=swap_request.target_user.name,
                )
            with force_locale(swap_request.target_user.effective_language()):
                target_message = _(
                    "%(name)s et vous avez échangé un shift (approuvé par "
                    "l'administrateur).",
                    name=swap_request.requester.name,
                )
            AppNotificationService._notify(
                swap_request.requester_id, "swap_approved", requester_message, "/swaps"
            )
            AppNotificationService._notify(
                swap_request.target_user_id, "swap_approved", target_message, "/swaps"
            )
        elif decision == SwapRequest.REJECTED:
            with force_locale(swap_request.requester.effective_language()):
                requester_message = _(
                    "Votre demande d'échange avec %(name)s a été rejetée.",
                    name=swap_request.target_user.name,
                )
                if swap_request.admin_comment:
                    requester_message += _(
                        " Motif : %(comment)s", comment=swap_request.admin_comment
                    )
            AppNotificationService._notify(
                swap_request.requester_id, "swap_rejected", requester_message, "/swaps"
            )
        elif decision == SwapRequest.REVERTED:
            with force_locale(swap_request.requester.effective_language()):
                requester_message = _(
                    "L'échange approuvé avec %(name)s a été annulé par "
                    "l'administrateur, vos shifts d'origine sont restaurés.",
                    name=swap_request.target_user.name,
                )
            with force_locale(swap_request.target_user.effective_language()):
                target_message = _(
                    "L'échange avec %(name)s a été annulé par l'administrateur, "
                    "vos shifts d'origine sont restaurés.",
                    name=swap_request.requester.name,
                )
            AppNotificationService._notify(
                swap_request.requester_id, "swap_reverted", requester_message, "/swaps"
            )
            AppNotificationService._notify(
                swap_request.target_user_id, "swap_reverted", target_message, "/swaps"
            )
        db.session.commit()

    @staticmethod
    def notify_admins_oncall_gap(dates: list[date]) -> None:
        """No user satisfies the legal 2-week on-call spacing constraint
        (or is free of leave/overlap) for these Fridays - automatic
        generation (OnCallAutomation.generate_oncall_schedule(), called
        either interactively from /admin/automation or automatically by
        AdvancedShiftAutomation.rebalance_after_leave()) deliberately
        leaves them unassigned rather than assigning someone in
        violation of the legal constraint. Manual admin assignment is
        needed. Call only after the triggering generation's own commit
        has actually succeeded (same rule as every other call site in
        this app - see CLAUDE.md "In-app notifications")."""
        if not dates:
            return
        dates_str = ", ".join(d.strftime("%d/%m/%Y") for d in dates)
        for admin in UserRepository.list_admins():
            with force_locale(admin.effective_language()):
                message = _(
                    "Astreinte(s) non générée(s) automatiquement (aucun utilisateur "
                    "ne respecte le délai légal de 2 semaines) : %(dates)s. "
                    "Assignation manuelle nécessaire.",
                    dates=dates_str,
                )
            AppNotificationService._notify(
                admin.id, "oncall_generation_gap", message, "/admin/automation"
            )
        db.session.commit()
