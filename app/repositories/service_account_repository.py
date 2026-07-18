"""
ServiceAccount repository for Kairos.

Data access layer for the ServiceAccount model - no business logic, no
Flask request/response handling, just queries. See
app/services/service_account_service.py for the business logic and
app/auth/service_account_auth.py for the auth lookup call site.
"""

from datetime import datetime, timezone

from app import db
from app.models import ServiceAccount


class ServiceAccountRepository:
    """Data access for the ServiceAccount model."""

    @staticmethod
    def get_by_id(service_account_id: int) -> ServiceAccount | None:
        return db.session.get(ServiceAccount, service_account_id)

    @staticmethod
    def get_by_token_hash(token_hash: str) -> ServiceAccount | None:
        return ServiceAccount.query.filter_by(token_hash=token_hash).first()

    @staticmethod
    def get_all() -> list[ServiceAccount]:
        return ServiceAccount.query.order_by(ServiceAccount.name).all()

    @staticmethod
    def create(
        name: str,
        description: str | None,
        token_prefix: str,
        token_hash: str,
        expires_at: datetime | None = None,
    ) -> ServiceAccount:
        service_account = ServiceAccount(
            name=name,
            description=description,
            token_prefix=token_prefix,
            token_hash=token_hash,
            is_active=True,
            expires_at=expires_at,
        )
        db.session.add(service_account)
        return service_account

    @staticmethod
    def delete(service_account: ServiceAccount) -> None:
        db.session.delete(service_account)

    @staticmethod
    def touch_last_used(service_account: ServiceAccount) -> None:
        """Best-effort, own commit - a failure here must never fail the
        API request being authenticated. Called from
        app/auth/service_account_auth.py on every successful auth."""
        service_account.last_used_at = datetime.now(timezone.utc)
        db.session.commit()
