"""
ServiceAccount model for Kairos.

Admin-generated bearer credentials for third-party integrations
consuming the public API (app/api/, /api/v1/*) - never a human login,
no session cookie/Flask-Login involved. See
app/auth/service_account_auth.py for the auth mechanism.
"""

import hashlib
import secrets
from datetime import datetime, timezone

from app import db
from app.models.base import BaseModel

TOKEN_PREFIX = (
    "ksak_"  # noqa: S105 # nosec B105 - "Kairos API Key", a public prefix, not a secret
)


class ServiceAccount(BaseModel):
    """
    Attributes:
        name: Human-readable label shown in the admin UI.
        description: Optional free-text note (e.g. "Zapier integration").
        token_prefix: The token's first characters (TOKEN_PREFIX + 8),
            stored in clear for UI identification (e.g.
            "ksak_a1b2c3d4...") - never enough entropy on its own to
            authenticate.
        token_hash: SHA-256 hex digest of the full token. Deliberately
            NOT werkzeug's generate_password_hash (PBKDF2, CPU-expensive
            by design against low-entropy human passwords): this token
            has 256 bits of entropy from secrets.token_urlsafe(32), so a
            fast deterministic hash is the correct trade-off for a
            credential checked on every API call.
        is_active: Revocation switch, independent of expires_at.
        expires_at: Optional hard expiry (nullable = never expires).
        last_used_at: Best-effort last-auth timestamp for the admin UI
            only, never part of the validity check itself.
    """

    __tablename__ = "service_account"

    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    token_prefix = db.Column(db.String(16), nullable=False, index=True)
    token_hash = db.Column(db.String(64), unique=True, nullable=False, index=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    expires_at = db.Column(db.DateTime, nullable=True)
    last_used_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self) -> dict:
        """Never expose token_hash - same discipline as User.to_dict()
        popping password_hash/ics_token."""
        data = super().to_dict()
        data.pop("token_hash", None)
        return data

    @staticmethod
    def generate_token() -> tuple[str, str, str]:
        """Returns (full_token, token_prefix, token_hash). full_token is
        shown to the admin exactly once (create/regenerate) and never
        persisted anywhere."""
        raw = secrets.token_urlsafe(32)
        full_token = f"{TOKEN_PREFIX}{raw}"
        token_hash = hashlib.sha256(full_token.encode()).hexdigest()
        prefix = full_token[: len(TOKEN_PREFIX) + 8]
        return full_token, prefix, token_hash

    @staticmethod
    def hash_token(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    def is_valid(self) -> bool:
        if not self.is_active:
            return False
        if self.expires_at is not None and self.expires_at < datetime.now(
            timezone.utc
        ).replace(tzinfo=None):
            return False
        return True

    def __repr__(self) -> str:
        return f"<ServiceAccount {self.name} active={self.is_active}>"
