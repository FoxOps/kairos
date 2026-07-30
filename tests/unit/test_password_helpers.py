"""
Tests for app/utils/helpers/password_helpers.py - the password-strength
policy required by ANSSI-PG-078 section 4 (see the module's own
docstring for exactly which recommendations map to which check).
"""

from app.utils.helpers.password_helpers import (
    MAX_LENGTH,
    MIN_LENGTH,
    check_password_strength,
)


class TestMinimumLength:
    def test_rejects_too_short(self):
        error = check_password_strength("Ab1!Ab1!Ab1")  # 11 chars
        assert error is not None

    def test_accepts_exactly_min_length(self):
        password = "Ab1!" * 3  # 12 chars, 3+ classes
        assert len(password) == MIN_LENGTH
        assert check_password_strength(password) is None

    def test_rejects_too_long(self):
        error = check_password_strength("Ab1!" * (MAX_LENGTH // 4 + 1))
        assert error is not None


class TestComplexity:
    def test_rejects_only_lowercase(self):
        error = check_password_strength("onlylowercaseletters")
        assert error is not None

    def test_rejects_only_two_classes(self):
        # lowercase + digits only - 2 of the 4 classes
        error = check_password_strength("onlylowercase123456")
        assert error is not None

    def test_accepts_three_of_four_classes(self):
        # lowercase + uppercase + digits, no special character
        assert check_password_strength("CorrectHorse9Battery") is None

    def test_accepts_all_four_classes(self):
        assert check_password_strength("Correct-Horse-9!Batt") is None


class TestCommonWeakPasswords:
    def test_rejects_common_password_even_if_long_enough(self):
        # "administrateur" is 14 chars (passes length) but on the
        # blocklist and single-case (would also fail complexity, but
        # the blocklist check exists specifically to catch cases like
        # this even if complexity were somehow satisfied).
        error = check_password_strength("administrateur")
        assert error is not None

    def test_rejects_kairos_own_past_example_default(self):
        """Regression guard: docker/.env.example and .env.example both
        document DEFAULT_ADMIN_PASSWORD=admin123 as an example value -
        must never be accepted as a real password choice, even though
        it's no longer used as run.py's own internal fallback."""
        error = check_password_strength("admin123")
        assert error is not None

    def test_blocklist_check_itself_fires_independently_of_earlier_checks(
        self, monkeypatch
    ):
        """Every real _COMMON_WEAK_PASSWORDS entry is simple enough
        (single case, no digits/specials) to already fail the length
        or complexity check first - this module's own blocklist-
        specific error message is therefore never actually reached
        through any real entry today. Monkeypatches the set with an
        otherwise-compliant password to prove the blocklist check
        itself works, independent of that pre-existing gap."""
        import app.utils.helpers.password_helpers as password_helpers_module

        monkeypatch.setattr(
            password_helpers_module,
            "_COMMON_WEAK_PASSWORDS",
            {"correcthorse9!batt"},
        )
        error = check_password_strength("Correct-Horse-9!Batt".replace("-", ""))
        assert error is not None
        assert "courant" in error


class TestSequentialPatterns:
    def test_rejects_ascending_digit_sequence(self):
        error = check_password_strength("Xyz!0123456789")
        assert error is not None

    def test_rejects_azerty_pattern(self):
        error = check_password_strength("Xyz!123azertyuiop")
        assert error is not None

    def test_accepts_password_without_sequential_pattern(self):
        assert check_password_strength("Correct-Horse-9!Batt") is None


class TestPersonalInformation:
    def test_rejects_password_containing_name(self):
        """ "1234" would itself be flagged by the sequential-pattern
        check first (see TestSequentialPatterns) - digits chosen here
        specifically avoid that, so this actually exercises the name
        check's own branch, not an earlier one that happens to also
        return non-None."""
        error = check_password_strength(
            "Benjamin29!Zq", name="Benjamin Dupont", email="other@test.com"
        )
        assert error is not None
        assert "nom" in error

    def test_rejects_password_containing_email_local_part(self):
        error = check_password_strength(
            "Jdupont29!Zq", name="Someone Else", email="jdupont@test.com"
        )
        assert error is not None
        assert "email" in error

    def test_accepts_unrelated_password(self):
        assert (
            check_password_strength(
                "Correct-Horse-9!Batt",
                name="Benjamin Dupont",
                email="benjamin@test.com",
            )
            is None
        )

    def test_short_name_parts_not_falsely_flagged(self):
        """Name-substring matching only applies to parts >= 3
        characters - a 2-letter name part shouldn't false-positive on
        an unrelated password that happens to contain that substring."""
        assr = check_password_strength(
            "Correct-Horse-9!Batt", name="Jo Xi", email="jo@test.com"
        )
        assert assr is None
