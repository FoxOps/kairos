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
from app.utils.helpers import is_user_on_leave
from app.utils.logging import get_logger

logger = get_logger(__name__)


class SwapService:
    """Logique métier pour les échanges de shifts entre utilisateurs."""

    @staticmethod
    def list_pending() -> list[SwapRequest]:
        return SwapRequestRepository.list_pending()

    @staticmethod
    def list_approved() -> list[SwapRequest]:
        return SwapRequestRepository.list_by_status(SwapRequest.APPROVED)

    @staticmethod
    def list_for_user(user_id: int) -> list[SwapRequest]:
        return SwapRequestRepository.list_for_user(user_id)

    @staticmethod
    def _other_shift_on_date(user_id: int, target_date, exclude_shift_id) -> bool:
        """True si user_id a un shift à target_date autre que exclude_shift_id."""
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
        """Revalide les règles métier d'un échange. None si valide, sinon message d'erreur."""
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
        """Crée une demande d'échange, en attente de validation admin.

        Returns:
            (swap_request, None) si succès, (None, error_message) sinon.
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
        return swap_request, None

    @staticmethod
    def cancel_swap(swap_request: SwapRequest, user: User) -> str | None:
        """Annule une demande (par son auteur, ou un admin). None si succès."""
        if not swap_request.is_pending():
            return "Cette demande n'est plus en attente"
        if swap_request.requester_id != user.id and not user.is_admin:
            return "Seul le demandeur ou un administrateur peut annuler cette demande"

        swap_request.status = SwapRequest.CANCELLED
        db.session.commit()
        return None

    @staticmethod
    def approve_swap(swap_request: SwapRequest, admin: User) -> str | None:
        """Valide une demande : réassigne les shifts, ou None si succès."""
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
        logger.info(
            "Échange de shift id=%s approuvé par admin id=%s", swap_request.id, admin.id
        )
        return None

    @staticmethod
    def revert_swap(swap_request: SwapRequest, admin: User) -> str | None:
        """Annule un échange déjà approuvé : réassigne les shifts à leurs
        propriétaires d'origine. None si succès.

        Contrairement à approve_swap, ne revalide pas les règles métier
        habituelles (congé, autre shift ce jour) : on remet juste chaque
        shift à son propriétaire d'avant l'échange, ce qui était par
        définition une situation valide.
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
        """Rejette une demande. None si succès."""
        if not swap_request.is_pending():
            return "Cette demande n'est plus en attente"

        swap_request.mark_reviewed(admin.id, SwapRequest.REJECTED, comment=reason)
        db.session.commit()
        return None
