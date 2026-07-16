"""
ServiceAccountService for Leviia Schedule.

Business logic for admin-managed service accounts (bearer credentials
for the public REST API, app/api/) - creation, revocation, secret
regeneration, deletion. Every mutation logs to the audit trail via
AuditService, following the same post-commit placement rule as the
rest of the app - the token itself is never passed to `details`, only
`id`/`name`, same discipline as NotificationTarget.apprise_url.
"""

from datetime import datetime

from app import db
from app.models import ServiceAccount
from app.repositories.service_account_repository import ServiceAccountRepository
from app.services.audit_service import AuditService


class ServiceAccountService:
    """Business logic for service accounts."""

    @staticmethod
    def create_account(
        name: str, description: str | None = None, expires_at: datetime | None = None
    ) -> tuple[ServiceAccount, str]:
        """Returns (service_account, full_token) - full_token is shown
        to the admin exactly once and never persisted anywhere."""
        full_token, prefix, token_hash = ServiceAccount.generate_token()
        service_account = ServiceAccountRepository.create(
            name, description, prefix, token_hash, expires_at
        )
        db.session.commit()

        AuditService.log(
            "service_account.create",
            resource_type="ServiceAccount",
            resource_id=service_account.id,
            details=name,
        )
        return service_account, full_token

    @staticmethod
    def rename(
        service_account: ServiceAccount,
        name: str,
        description: str | None,
        expires_at: datetime | None,
    ) -> None:
        service_account.name = name
        service_account.description = description
        service_account.expires_at = expires_at
        db.session.commit()

        AuditService.log(
            "service_account.update",
            resource_type="ServiceAccount",
            resource_id=service_account.id,
            details=name,
        )

    @staticmethod
    def revoke(service_account: ServiceAccount) -> None:
        service_account.is_active = False
        db.session.commit()

        AuditService.log(
            "service_account.revoke",
            resource_type="ServiceAccount",
            resource_id=service_account.id,
            details=service_account.name,
        )

    @staticmethod
    def reactivate(service_account: ServiceAccount) -> None:
        service_account.is_active = True
        db.session.commit()

        AuditService.log(
            "service_account.reactivate",
            resource_type="ServiceAccount",
            resource_id=service_account.id,
            details=service_account.name,
        )

    @staticmethod
    def regenerate_secret(service_account: ServiceAccount) -> str:
        """Returns the new full_token, shown to the admin exactly once.
        The previous token is invalidated immediately (its hash is
        overwritten)."""
        full_token, prefix, token_hash = ServiceAccount.generate_token()
        service_account.token_prefix = prefix
        service_account.token_hash = token_hash
        db.session.commit()

        AuditService.log(
            "service_account.regenerate_secret",
            resource_type="ServiceAccount",
            resource_id=service_account.id,
            details=service_account.name,
        )
        return full_token

    @staticmethod
    def delete(service_account: ServiceAccount) -> None:
        name = service_account.name
        service_account_id = service_account.id
        ServiceAccountRepository.delete(service_account)
        db.session.commit()

        AuditService.log(
            "service_account.delete",
            resource_type="ServiceAccount",
            resource_id=service_account_id,
            details=name,
        )
