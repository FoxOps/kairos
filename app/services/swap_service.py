"""
SwapRequest service for Leviia Schedule.

Business logic for shift exchange requests between users: a requester
proposes to give up one of their shifts (optionally in return for one of
the target user's shifts), and an administrator must approve the request
before the underlying Shift rows are actually reassigned. Routes stay
thin: they parse the request, call this service, and turn the result
into a flash message / redirect / JSON response.
"""

from app import db
from app.models import Shift, SwapRequest, User
from app.repositories.swap_request_repository import SwapRequestRepository
from app.services.app_notification_service import AppNotificationService
from app.utils.helpers import is_user_on_leave
from app.utils.logging import get_logger

logger = get_logger(__name__)


class SwapService:
    """Business logic for shift exchanges between users."""

    @staticmethod
    def list_pending() -> list[SwapRequest]:
        return SwapRequestRepository.list_pending()

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
            return "Shift introuvable"
        if target_user is None:
            return "Utilisateur cible introuvable"
        if shift.user_id != requester.id:
            return "Ce shift ne vous appartient plus"
        if target_user.id == requester.id:
            return "Impossible de proposer un échange à vous-même"
        if target_shift is not None and target_shift.user_id != target_user.id:
            return "Le shift proposé en retour n'appartient plus à cet utilisateur"

        if is_user_on_leave(target_user.id, shift.date):
            return f"{target_user.name} est en congé le {shift.date}"
        if SwapService._other_shift_on_date(
            target_user.id,
            shift.date,
            exclude_shift_id=target_shift.id if target_shift else None,
        ):
            return f"{target_user.name} a déjà un autre shift le {shift.date}"

        if target_shift is not None:
            if is_user_on_leave(requester.id, target_shift.date):
                return f"Vous êtes en congé le {target_shift.date}"
            if SwapService._other_shift_on_date(
                requester.id, target_shift.date, exclude_shift_id=shift.id
            ):
                return f"Vous avez déjà un autre shift le {target_shift.date}"

        return None

    @staticmethod
    def request_swap(
        requester: User,
        shift: Shift,
        target_user: User,
        target_shift: Shift | None = None,
    ) -> tuple[SwapRequest | None, str | None]:
        """Create an exchange request, pending admin approval.

        Returns:
            (swap_request, None) on success, (None, error_message) otherwise.
        """
        if SwapRequestRepository.has_pending_for_shift(shift.id):
            return None, "Une demande est déjà en attente pour ce shift"

        error = SwapService._validation_error(
            requester, shift, target_user, target_shift
        )
        if error:
            return None, error

        swap_request = SwapRequestRepository.create(
            requester_id=requester.id,
            shift_id=shift.id,
            target_user_id=target_user.id,
            target_shift_id=target_shift.id if target_shift else None,
        )
        db.session.commit()
        AppNotificationService.notify_admins_new_swap_request(swap_request)
        return swap_request, None

    @staticmethod
    def cancel_swap(swap_request: SwapRequest, user: User) -> str | None:
        """Cancel a request (by its author, or an admin). None on success."""
        if not swap_request.is_pending():
            return "Cette demande n'est plus en attente"
        if swap_request.requester_id != user.id and not user.is_admin:
            return "Seul le demandeur ou un administrateur peut annuler cette demande"

        swap_request.status = SwapRequest.CANCELLED
        db.session.commit()
        return None

    @staticmethod
    def approve_swap(swap_request: SwapRequest, admin: User) -> str | None:
        """Approve a request: reassigns the shifts. None on success."""
        if not swap_request.is_pending():
            return "Cette demande n'est plus en attente"

        error = SwapService._validation_error(
            swap_request.requester,
            swap_request.shift,
            swap_request.target_user,
            swap_request.target_shift,
        )
        if error:
            return f"Échange invalide, réessayez de le rejeter : {error}"

        swap_request.shift.user_id = swap_request.target_user_id
        if swap_request.target_shift is not None:
            swap_request.target_shift.user_id = swap_request.requester_id

        swap_request.mark_reviewed(admin.id, SwapRequest.APPROVED)
        db.session.commit()
        AppNotificationService.notify_swap_decision(swap_request, SwapRequest.APPROVED)
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
            return "Seul un échange approuvé peut être annulé"

        shift = swap_request.shift
        if shift is None or shift.user_id != swap_request.target_user_id:
            return "Le shift a changé depuis l'approbation, annulation impossible automatiquement"

        target_shift = swap_request.target_shift
        if (
            target_shift is not None
            and target_shift.user_id != swap_request.requester_id
        ):
            return "Le shift retourné a changé depuis l'approbation, annulation impossible automatiquement"

        shift.user_id = swap_request.requester_id
        if target_shift is not None:
            target_shift.user_id = swap_request.target_user_id

        swap_request.mark_reviewed(admin.id, SwapRequest.REVERTED)
        db.session.commit()
        AppNotificationService.notify_swap_decision(swap_request, SwapRequest.REVERTED)
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
        """Reject a request. None on success."""
        if not swap_request.is_pending():
            return "Cette demande n'est plus en attente"

        swap_request.mark_reviewed(admin.id, SwapRequest.REJECTED, comment=reason)
        db.session.commit()
        AppNotificationService.notify_swap_decision(swap_request, SwapRequest.REJECTED)
        return None

    @staticmethod
    def purge_resolved_for_user(user: User) -> int:
        """Delete the user's resolved (non-pending) requests (as either
        requester or target). Returns the number deleted."""
        count = SwapRequestRepository.purge_resolved_for_user(user.id)
        db.session.commit()
        return count

    @staticmethod
    def purge_all_resolved() -> int:
        """Delete all resolved (non-pending) requests, admin only (checked
        by the route). Returns the number deleted."""
        count = SwapRequestRepository.purge_all_resolved()
        db.session.commit()
        return count
