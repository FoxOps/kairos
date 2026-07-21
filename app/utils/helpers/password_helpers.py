"""
Password strength policy for Kairos.

Based on the ANSSI guide "Recommandations relatives à l'authentification
multifacteur et aux mots de passe" (ANSSI-PG-078, section 4):
- R21 (table 3): minimum length by sensitivity tier - this app uses the
  "moyen à fort" tier (12 characters minimum) as its baseline, the same
  policy for every account (admin or not) rather than maintaining two
  tiers for a modest gain in complexity.
- R22: no maximum length restriction - MAX_LENGTH below is a DoS guard
  (unbounded input to werkzeug's password hasher), not a complexity cap.
- R23: complexity rules while keeping the widest practical character
  set - requires 3 of the 4 usual classes (lower/upper/digit/special)
  rather than all 4, since a long password already carries most of the
  entropy (per the guide's own point: length matters more than
  complexity for equal entropy).
- R27: automated robustness control at creation/renewal - rejected
  against a common-password/weak-pattern list and the account's own
  name/email, so a password that's merely long enough is still refused
  if it's trivially guessable.

This module only applies to Kairos' own local (basic-auth) password
store. OIDC-authenticated users never have a local password at all
(see app/auth/user_manager.py::sync_user_from_oidc - a new OIDC user is
created with no password_hash, an existing one's is left untouched) -
password policy for them is delegated entirely to the upstream
identity provider, and none of this module is ever invoked on that
path.
"""

import re

from flask_babel import gettext as _

MIN_LENGTH = 12
# Not a complexity cap (see R22 above) - just keeps a maliciously huge
# input from making generate_password_hash() take arbitrarily long.
MAX_LENGTH = 128

# A small, deliberately non-exhaustive list of the most common/weak
# passwords (including this project's own past example defaults) - the
# full-scale version of this control (R27) would compare against a real
# breached-password corpus (e.g. Have I Been Pwned's range API), which
# is out of scope here (no outbound network call from a synchronous
# password-change request); this catches the obvious cases without one.
_COMMON_WEAK_PASSWORDS = {
    "password",
    "password1",
    "password123",
    "azerty",
    "azerty123",
    "123456",
    "1234567890",
    "123456789",
    "12345678",
    "qwerty",
    "qwerty123",
    "admin",
    "admin123",
    "administrateur",
    "motdepasse",
    "motdepasse1",
    "welcome",
    "welcome1",
    "letmein",
    "iloveyou",
    "sunshine",
    "princess",
    "dragon",
    "monkey123",
    "football",
    "baseball",
    "master",
    "shadow",
    "superman",
    "trustno1",
    "changeme",
    "change123",
    "kairos",
    "kairos123",
}

# Checked as any 4+ character substring, both forward and reversed, so
# "6543" (part of a reversed 0123456789) and "trepza" (reversed azerty)
# are caught too, not just the exact forward sequence.
_SEQUENTIAL_PATTERNS = [
    "0123456789",
    "abcdefghijklmnopqrstuvwxyz",
    "azertyuiop",
    "qwertyuiop",
]


def _contains_sequential_pattern(password: str) -> bool:
    lowered = password.lower()
    for pattern in _SEQUENTIAL_PATTERNS:
        for variant in (pattern, pattern[::-1]):
            for start in range(len(variant) - 3):
                if variant[start : start + 4] in lowered:
                    return True
    return False


def check_password_strength(
    password: str, *, name: str = "", email: str = ""
) -> str | None:
    """Validates a password against Kairos' strength policy.

    Args:
        password: The candidate plain-text password.
        name: The account holder's name, if known - rejects the
            password if it contains it (checked word-by-word, ≥3
            characters, to avoid false positives on short names).
        email: The account holder's email, if known - rejects the
            password if it contains the local part (before the @).

    Returns:
        A ready-to-flash French error message if the password fails
        the policy, or None if it's acceptable.
    """
    if len(password) < MIN_LENGTH:
        return _(
            "Le mot de passe doit contenir au moins %(min_length)s caractères.",
            min_length=MIN_LENGTH,
        )
    if len(password) > MAX_LENGTH:
        return _(
            "Le mot de passe ne doit pas dépasser %(max_length)s caractères.",
            max_length=MAX_LENGTH,
        )

    has_lower = any(c.islower() for c in password)
    has_upper = any(c.isupper() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(not c.isalnum() for c in password)
    if sum([has_lower, has_upper, has_digit, has_special]) < 3:
        return _(
            "Le mot de passe doit contenir au moins 3 des 4 types de "
            "caractères suivants : minuscules, majuscules, chiffres, "
            "caractères spéciaux."
        )

    lowered = password.lower()

    if lowered in _COMMON_WEAK_PASSWORDS:
        return _(
            "Ce mot de passe est trop courant et facilement devinable. "
            "Choisissez-en un autre."
        )

    if _contains_sequential_pattern(password):
        return _(
            "Le mot de passe ne doit pas contenir de suite de caractères "
            "évidente (ex : 1234, azerty, abcd)."
        )

    if name:
        name_parts = [part for part in re.split(r"\s+", name.lower()) if len(part) >= 3]
        if any(part in lowered for part in name_parts):
            return _("Le mot de passe ne doit pas contenir votre nom.")

    if email:
        local_part = email.split("@")[0].lower()
        if len(local_part) >= 3 and local_part in lowered:
            return _("Le mot de passe ne doit pas contenir votre adresse email.")

    return None
