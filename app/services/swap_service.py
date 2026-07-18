"""
SwapRequest service for Kairos.

Business logic for shift exchange requests between users: a requester
proposes to give up one of their shifts (optionally in return for one of
the target user's shifts), and an administrator must approve the request
before the underlying Shift rows are actually reassigned. Routes stay
thin: they parse the request, call this service, and turn the result
into a flash message / redirect / JSON response.
"""

from flask_babel import gettext as _

from app import db
from app.models import Shift, SwapRequest, User
from app.repositories.swap_request_repository import SwapRequestRepository
from app.services.app_notification_service import AppNotificationService
from app.services.apprise_notification_service import AppriseNotificationService
from app.services.audit_service import AuditService
from app.utils.helpers import is_user_on_leave
from app.utils.logging import get_logger

logger = get_logger(__name__)


class SwapService:
    """Business logic for shift exchanges between users."""

    @staticmethod
    def list_pending() -> list[SwapRequest]:
        """Requests still awaiting the target's own confirmation - read-only
        visibility, see list_awaiting_admin() for the admin's actionable
        queue."""
        return SwapRequestRepository.list_pending()

    @staticmethod
    def list_awaiting_admin() -> list[SwapRequest]:
        """Requests the target has confirmed - the admin's actionable
        queue."""
        return SwapRequestRepository.list_awaiting_admin()

    @staticmethod
    def list_approved() -> list[SwapRequest]:
        return SwapRequestRepository.list_by_status(SwapRequest.APPROVED)

    @staticmethod
    def _other_shift_on_date(user_id: int, target_date, exclude_shift_id) -> bool:
        """True if user_id has a shift on target_date other than exclude_shift_id."""
        query = Shift.query.filter(Shift.user_id == user_id, Shift.date == target_date)
        if exclude_shift_id is not None:
            query = query.filter(Shift.id != exclude_shift_id)
        return query.first() is not None

    @staticmethod
    def _validation_error(
        requester: User,
        shift: Shift | None,
        target_user: User | None,
        target_shift: Shift | None,
    ) -> str | None:
        """Re-validate the business rules for an exchange. None if valid, otherwise an error message."""
        if shift is None:
            return _("Shift introuvable")
        if target_user is None:
            return _("Utilisateur cible introuvable")
        if shift.user_id != requester.id:
            return _("Ce shift ne vous appartient plus")
        if target_user.id == requester.id:
            return _("Impossible de proposer un échange à vous-même")
        if target_shift is not None and target_shift.user_id != target_user.id:
            return _("Le shift proposé en retour n'appartient plus à cet utilisateur")

        if is_user_on_leave(target_user.id, shift.date):
            return _(
                "%(name)s est en congé le %(date)s",
                name=target_user.name,
                date=shift.date,
            )
        if SwapService._other_shift_on_date(
            target_user.id,
            shift.date,
            exclude_shift_id=target_shift.id if target_shift else None,
        ):
            return _(
                "%(name)s a déjà un autre shift le %(date)s",
                name=target_user.name,
                date=shift.date,
            )

        if target_shift is not None:
            if is_user_on_leave(requester.id, target_shift.date):
                return _("Vous êtes en congé le %(date)s", date=target_shift.date)
            if SwapService._other_shift_on_date(
                requester.id, target_shift.date, exclude_shift_id=shift.id
            ):
                return _(
                    "Vous avez déjà un autre shift le %(date)s", date=target_shift.date
                )

        return None

    @staticmethod
    def request_swap(
        requester: User,
        shift: Shift,
        target_user: User,
    ) -> tuple[SwapRequest | None, str | None]:
        """Create an exchange request, pending the target's own
        confirmation (they pick which of their shifts to offer back, or
        decline - see confirm_swap()/target_reject_swap()). The requester
        never picks target_shift themselves.

        Returns:
            (swap_request, None) on success, (None, error_message) otherwise.
        """
        if SwapRequestRepository.has_pending_for_shift(shift.id):
            return None, _("Une demande est déjà en attente pour ce shift")

        error = SwapService._validation_error(requester, shift, target_user, None)
        if error:
            return None, error

        swap_request = SwapRequestRepository.create(
            requester_id=requester.id,
            shift_id=shift.id,
            target_user_id=target_user.id,
        )
        db.session.commit()
        AuditService.log(
            "swap.request",
            resource_type="SwapRequest",
            resource_id=swap_request.id,
            details=f"{requester.name} -> {target_user.name}",
            actor=requester,
        )
        AppNotificationService.notify_target_confirmation_needed(swap_request)
        AppriseNotificationService.notify(
            "swap",
            _("Nouvelle demande d'échange de shift"),
            _(
                "%(requester)s propose un échange de shift à %(target)s, en "
                "attente de sa confirmation.",
                requester=requester.name,
                target=target_user.name,
            ),
        )
        return swap_request, None

    @staticmethod
    def confirm_swap(
        swap_request: SwapRequest,
        target_user: User,
        target_shift: Shift | None = None,
    ) -> str | None:
        """The target confirms the exchange and picks which of their own
        shifts to offer back (or leaves it a one-way give-away). Moves the
        request into the admin's queue. None on success.

        Returns:
            error_message on failure, None on success.
        """
        if not swap_request.is_awaiting_target():
            return _("Cette demande n'est plus en attente de votre confirmation")
        if swap_request.target_user_id != target_user.id:
            return _("Cette demande ne vous est pas destinée")

        error = SwapService._validation_error(
            swap_request.requester, swap_request.shift, target_user, target_shift
        )
        if error:
            return error

        swap_request.target_shift_id = target_shift.id if target_shift else None
        swap_request.status = SwapRequest.AWAITING_ADMIN
        db.session.commit()
        AuditService.log(
            "swap.confirm",
            resource_type="SwapRequest",
            resource_id=swap_request.id,
            details=f"{swap_request.requester.name} -> {target_user.name}",
            actor=target_user,
        )
        AppNotificationService.notify_admins_new_swap_request(swap_request)
        AppriseNotificationService.notify(
            "swap",
            _("Échange de shift confirmé par le destinataire"),
            _(
                "%(target)s a confirmé l'échange proposé par %(requester)s, "
                "en attente de validation admin.",
                target=target_user.name,
                requester=swap_request.requester.name,
            ),
        )
        return None

    @staticmethod
    def target_reject_swap(
        swap_request: SwapRequest, target_user: User, reason: str | None = None
    ) -> str | None:
        """The target declines the exchange outright, before it ever
        reaches the admin. None on success.

        Returns:
            error_message on failure, None on success.
        """
        if not swap_request.is_awaiting_target():
            return _("Cette demande n'est plus en attente de votre confirmation")
        if swap_request.target_user_id != target_user.id:
            return _("Cette demande ne vous est pas destinée")

        swap_request.mark_reviewed(target_user.id, SwapRequest.REJECTED, comment=reason)
        db.session.commit()
        AuditService.log(
            "swap.reject",
            resource_type="SwapRequest",
            resource_id=swap_request.id,
            details=reason,
            actor=target_user,
        )
        AppNotificationService.notify_target_rejection(swap_request)
        AppriseNotificationService.notify(
            "swap",
            _("Échange de shift décliné par le destinataire"),
            _(
                "%(target)s a décliné la proposition d'échange de %(requester)s.",
                target=target_user.name,
                requester=swap_request.requester.name,
            ),
        )
        return None

    @staticmethod
    def cancel_swap(swap_request: SwapRequest, user: User) -> str | None:
        """Cancel a request (by its author, or an admin). Allowed while
        awaiting the target's confirmation or the admin's decision - not
        just the original PENDING stage. None on success."""
        if not swap_request.is_active():
            return _("Cette demande n'est plus en attente")
        if swap_request.requester_id != user.id and not user.is_admin:
            return _(
                "Seul le demandeur ou un administrateur peut annuler cette demande"
            )

        swap_request.status = SwapRequest.CANCELLED
        db.session.commit()
        AuditService.log(
            "swap.cancel",
            resource_type="SwapRequest",
            resource_id=swap_request.id,
            actor=user,
        )
        return None

    @staticmethod
    def approve_swap(swap_request: SwapRequest, admin: User) -> str | None:
        """Approve a request: reassigns the shifts. Only once the target
        has confirmed (AWAITING_ADMIN) - an admin can no longer act on a
        request the target hasn't seen yet. None on success."""
        if not swap_request.is_awaiting_admin():
            return _("Cette demande n'est pas en attente de validation admin")

        error = SwapService._validation_error(
            swap_request.requester,
            swap_request.shift,
            swap_request.target_user,
            swap_request.target_shift,
        )
        if error:
            return _(
                "Échange invalide, réessayez de le rejeter : %(error)s", error=error
            )

        swap_request.shift.user_id = swap_request.target_user_id
        if swap_request.target_shift is not None:
            swap_request.target_shift.user_id = swap_request.requester_id

        swap_request.mark_reviewed(admin.id, SwapRequest.APPROVED)
        db.session.commit()
        AuditService.log(
            "swap.approve",
            resource_type="SwapRequest",
            resource_id=swap_request.id,
            details=f"{swap_request.requester.name} <-> {swap_request.target_user.name}",
            actor=admin,
        )
        AppNotificationService.notify_swap_decision(swap_request, SwapRequest.APPROVED)
        AppriseNotificationService.notify(
            "swap",
            _("Échange de shift approuvé"),
            _(
                "%(requester)s <-> %(target)s : échange approuvé par %(admin)s.",
                requester=swap_request.requester.name,
                target=swap_request.target_user.name,
                admin=admin.name,
            ),
        )
        logger.info(
            "Échange de shift id=%s approuvé par admin id=%s", swap_request.id, admin.id
        )
        return None

    @staticmethod
    def revert_swap(swap_request: SwapRequest, admin: User) -> str | None:
        """Revert an already-approved exchange: reassigns the shifts back
        to their original owners. None on success.

        Unlike approve_swap, this does not re-validate the usual business
        rules (leave, another shift that day): it just puts each shift
        back with its pre-exchange owner, which was by definition a valid
        situation.
        """
        if swap_request.status != SwapRequest.APPROVED:
            return _("Seul un échange approuvé peut être annulé")

        shift = swap_request.shift
        if shift is None or shift.user_id != swap_request.target_user_id:
            return _(
                "Le shift a changé depuis l'approbation, annulation impossible "
                "automatiquement"
            )

        target_shift = swap_request.target_shift
        if (
            target_shift is not None
            and target_shift.user_id != swap_request.requester_id
        ):
            return _(
                "Le shift retourné a changé depuis l'approbation, annulation "
                "impossible automatiquement"
            )

        shift.user_id = swap_request.requester_id
        if target_shift is not None:
            target_shift.user_id = swap_request.target_user_id

        swap_request.mark_reviewed(admin.id, SwapRequest.REVERTED)
        db.session.commit()
        AuditService.log(
            "swap.revert",
            resource_type="SwapRequest",
            resource_id=swap_request.id,
            details=f"{swap_request.requester.name} <-> {swap_request.target_user.name}",
            actor=admin,
        )
        AppNotificationService.notify_swap_decision(swap_request, SwapRequest.REVERTED)
        AppriseNotificationService.notify(
            "swap",
            _("Échange de shift annulé"),
            _(
                "%(requester)s <-> %(target)s : échange approuvé annulé par "
                "%(admin)s, shifts d'origine restaurés.",
                requester=swap_request.requester.name,
                target=swap_request.target_user.name,
                admin=admin.name,
            ),
        )
        logger.info(
            "Échange de shift id=%s annulé après approbation par admin id=%s",
            swap_request.id,
            admin.id,
        )
        return None

    @staticmethod
    def reject_swap(
        swap_request: SwapRequest, admin: User, reason: str | None = None
    ) -> str | None:
        """Reject a request. Only once the target has confirmed
        (AWAITING_ADMIN) - see approve_swap(). None on success."""
        if not swap_request.is_awaiting_admin():
            return _("Cette demande n'est pas en attente de validation admin")

        swap_request.mark_reviewed(admin.id, SwapRequest.REJECTED, comment=reason)
        db.session.commit()
        AuditService.log(
            "swap.reject",
            resource_type="SwapRequest",
            resource_id=swap_request.id,
            details=reason,
            actor=admin,
        )
        AppNotificationService.notify_swap_decision(swap_request, SwapRequest.REJECTED)
        AppriseNotificationService.notify(
            "swap",
            _("Échange de shift rejeté"),
            _(
                "%(requester)s <-> %(target)s : demande rejetée par %(admin)s.",
                requester=swap_request.requester.name,
                target=swap_request.target_user.name,
                admin=admin.name,
            ),
        )
        return None

    @staticmethod
    def purge_resolved_for_user(user: User) -> int:
        """Delete the user's resolved requests (as either requester or
        target) - excludes both PENDING and AWAITING_ADMIN, not just
        PENDING. Returns the number deleted."""
        count = SwapRequestRepository.purge_resolved_for_user(user.id)
        db.session.commit()
        if count:
            AuditService.log(
                "swap.purge",
                details=f"{count} resolved request(s), own history",
                actor=user,
            )
        return count

    @staticmethod
    def purge_all_resolved() -> int:
        """Delete all resolved (non-pending) requests, admin only (checked
        by the route). Returns the number deleted."""
        count = SwapRequestRepository.purge_all_resolved()
        db.session.commit()
        if count:
            AuditService.log(
                "swap.purge", details=f"{count} resolved request(s), all users"
            )
        return count
