"""
Tests pour les fonctions helpers (validation des conflits).
"""

from datetime import date, datetime, time, timedelta

from app import db
from app.models import Leave, OnCall, Shift
from app.utils.helpers import (
    _get_overlapping_leave,
    _get_overlapping_oncall,
    _get_overlapping_shift,
    _has_overlapping_oncall,
    can_add_leave,
    can_add_oncall,
    can_add_shift,
    format_date,
    format_datetime,
    format_time,
    get_bool,
    get_current_month,
    get_current_year,
    get_days_in_month,
    get_int,
    is_user_on_leave,
    is_user_on_shift,
    parse_date,
    parse_datetime,
)


class TestHelperFunctions:
    """Tests pour les fonctions helpers internes."""

    def test_is_user_on_shift_true(self, test_app, test_user, test_shift_type):
        """Test qu'un utilisateur a un shift à une date donnée."""
        with test_app.app_context():
            # Créer un shift pour l'utilisateur
            shift_date = datetime(2023, 12, 1).date()
            start_time = datetime(2023, 12, 1, 7, 0)
            end_time = datetime(2023, 12, 1, 15, 0)
            shift = Shift(
                user_id=test_user.id,
                shift_type_id=test_shift_type.id,
                start_time=start_time,
                end_time=end_time,
                date=shift_date,
            )
            db.session.add(shift)
            db.session.commit()

            result = is_user_on_shift(test_user.id, shift_date)
            assert result is True

    def test_is_user_on_shift_false(self, test_app, test_user):
        """Test qu'un utilisateur n'a pas de shift à une date donnée."""
        with test_app.app_context():
            shift_date = datetime(2023, 12, 1).date()
            result = is_user_on_shift(test_user.id, shift_date)
            assert result is False

    def test_is_user_on_leave_true(self, test_app, test_user):
        """Test qu'un utilisateur est en congé à une date donnée."""
        with test_app.app_context():
            # Créer un congé
            start_date = datetime(2023, 12, 10).date()
            end_date = datetime(2023, 12, 15).date()
            leave = Leave(
                user_id=test_user.id, start_date=start_date, end_date=end_date
            )
            db.session.add(leave)
            db.session.commit()

            # Vérifier au milieu du congé
            result = is_user_on_leave(test_user.id, datetime(2023, 12, 12).date())
            assert result is True

    def test_is_user_on_leave_false(self, test_app, test_user):
        """Test qu'un utilisateur n'est pas en congé à une date donnée."""
        with test_app.app_context():
            result = is_user_on_leave(test_user.id, datetime(2023, 12, 1).date())
            assert result is False

    def test_has_overlapping_oncall_true(self, test_app, test_user):
        """Test qu'un utilisateur a une astreinte chevauchante."""
        with test_app.app_context():
            # Créer une astreinte existante
            start_time = datetime(2023, 12, 1, 21, 0)
            end_time = start_time + timedelta(days=7, hours=-14)
            oncall = OnCall(
                user_id=test_user.id, start_time=start_time, end_time=end_time
            )
            db.session.add(oncall)
            db.session.commit()

            # Vérifier le chevauchement
            new_start = datetime(2023, 12, 2, 10, 0)
            new_end = datetime(2023, 12, 5, 10, 0)
            result = _has_overlapping_oncall(test_user.id, new_start, new_end)
            assert result is True

    def test_has_overlapping_oncall_false(self, test_app, test_user):
        """Test qu'un utilisateur n'a pas d'astreinte chevauchante."""
        with test_app.app_context():
            # Créer une astreinte existante
            start_time = datetime(2023, 12, 1, 21, 0)
            end_time = start_time + timedelta(days=7, hours=-14)
            oncall = OnCall(
                user_id=test_user.id, start_time=start_time, end_time=end_time
            )
            db.session.add(oncall)
            db.session.commit()

            # Vérifier sans chevauchement
            new_start = datetime(2023, 12, 15, 21, 0)
            new_end = new_start + timedelta(days=7, hours=-14)
            result = _has_overlapping_oncall(test_user.id, new_start, new_end)
            assert result is False

    def test_get_overlapping_leave(self, test_app, test_user):
        """Test la récupération d'un congé chevauchant."""
        with test_app.app_context():
            # Créer un congé
            start_date = datetime(2023, 12, 10).date()
            end_date = datetime(2023, 12, 15).date()
            leave = Leave(
                user_id=test_user.id, start_date=start_date, end_date=end_date
            )
            db.session.add(leave)
            db.session.commit()

            # Chercher un congé chevauchant
            result = _get_overlapping_leave(
                test_user.id,
                datetime(2023, 12, 12).date(),
                datetime(2023, 12, 14).date(),
            )
            assert result is not None
            assert result.id == leave.id

    def test_get_overlapping_leave_none(self, test_app, test_user):
        """Test qu'aucun congé chevauchant n'est trouvé."""
        with test_app.app_context():
            result = _get_overlapping_leave(
                test_user.id, datetime(2023, 12, 1).date(), datetime(2023, 12, 5).date()
            )
            assert result is None


class TestCanAddShift:
    """Tests pour can_add_shift."""

    def test_can_add_shift_valid(self, test_app, test_user):
        """Test qu'un shift peut être ajouté sur une date valide."""
        with test_app.app_context():
            shift_date = datetime(2023, 12, 1).date()  # Lundi
            can_add = can_add_shift(test_user, shift_date, "morning")
            assert can_add is True

    def test_can_add_shift_weekend_saturday(self, test_app, test_user):
        """Test qu'un shift ne peut pas être ajouté un samedi."""
        with test_app.app_context():
            shift_date = datetime(2023, 12, 2).date()  # Samedi
            can_add = can_add_shift(test_user, shift_date, "morning")
            assert not can_add

    def test_can_add_shift_weekend_sunday(self, test_app, test_user):
        """Test qu'un shift ne peut pas être ajouté un dimanche."""
        with test_app.app_context():
            shift_date = datetime(2023, 12, 3).date()  # Dimanche
            can_add = can_add_shift(test_user, shift_date, "morning")
            assert not can_add

    def test_can_add_shift_user_on_leave(self, test_app, test_user):
        """Test qu'un shift ne peut pas être ajouté si l'utilisateur est en congé."""
        with test_app.app_context():
            # Créer un congé
            start_date = datetime(2023, 12, 10).date()
            end_date = datetime(2023, 12, 15).date()
            leave = Leave(
                user_id=test_user.id, start_date=start_date, end_date=end_date
            )
            db.session.add(leave)
            db.session.commit()

            shift_date = leave.start_date  # Date de début du congé
            can_add = can_add_shift(test_user, shift_date, "morning")
            assert not can_add

    def test_can_add_shift_user_already_has_shift(
        self, test_app, test_user, test_shift_type
    ):
        """Test qu'un shift ne peut pas être ajouté si l'utilisateur en a déjà un."""
        with test_app.app_context():
            # Créer un shift existant
            start_time = datetime(2023, 12, 1, 7, 0)
            end_time = datetime(2023, 12, 1, 15, 0)
            shift = Shift(
                user_id=test_user.id,
                shift_type_id=test_shift_type.id,
                start_time=start_time,
                end_time=end_time,
                date=start_time.date(),
            )
            db.session.add(shift)
            db.session.commit()

            shift_date = shift.date
            can_add = can_add_shift(test_user, shift_date, "morning")
            assert not can_add

    def test_can_add_shift_multiple_users_same_day(
        self, test_app, test_user, second_user
    ):
        """Test que plusieurs utilisateurs peuvent avoir des shifts le même jour."""
        with test_app.app_context():
            shift_date = datetime(2023, 12, 1).date()  # Lundi

            # Ajouter un shift pour le premier utilisateur
            can_add1 = can_add_shift(test_user, shift_date, "morning")
            assert can_add1 is True

            # Ajouter un shift pour le deuxième utilisateur le même jour
            can_add2 = can_add_shift(second_user, shift_date, "morning")
            assert can_add2 is True


class TestCanAddOnCall:
    """Tests pour can_add_oncall."""

    def test_can_add_oncall_valid(self, test_app, test_user):
        """Test qu'une astreinte peut être ajoutée un vendredi à 21h."""
        with test_app.app_context():
            start_time = datetime(2023, 12, 1, 21, 0)  # Vendredi 21h
            end_time = start_time + timedelta(days=7, hours=-14)
            can_add = can_add_oncall(test_user, start_time, end_time)
            assert can_add is True

    def test_can_add_oncall_wrong_day_saturday(self, test_app, test_user):
        """Test qu'une astreinte ne peut pas être ajoutée un samedi."""
        with test_app.app_context():
            start_time = datetime(2023, 12, 2, 21, 0)  # Samedi 21h
            end_time = start_time + timedelta(days=7, hours=-14)
            can_add = can_add_oncall(test_user, start_time, end_time)
            assert not can_add

    def test_can_add_oncall_wrong_day_monday(self, test_app, test_user):
        """Test qu'une astreinte ne peut pas être ajoutée un lundi."""
        with test_app.app_context():
            start_time = datetime(2023, 12, 4, 21, 0)  # Lundi 21h
            end_time = start_time + timedelta(days=7, hours=-14)
            can_add = can_add_oncall(test_user, start_time, end_time)
            assert not can_add

    def test_can_add_oncall_wrong_hour_20h(self, test_app, test_user):
        """Test qu'une astreinte ne peut pas être ajoutée à 20h."""
        with test_app.app_context():
            start_time = datetime(2023, 12, 1, 20, 0)  # Vendredi 20h
            end_time = start_time + timedelta(days=7, hours=-14)
            can_add = can_add_oncall(test_user, start_time, end_time)
            assert not can_add

    def test_can_add_oncall_wrong_hour_22h(self, test_app, test_user):
        """Test qu'une astreinte ne peut pas être ajoutée à 22h."""
        with test_app.app_context():
            start_time = datetime(2023, 12, 1, 22, 0)  # Vendredi 22h
            end_time = start_time + timedelta(days=7, hours=-14)
            can_add = can_add_oncall(test_user, start_time, end_time)
            assert not can_add

    def test_can_add_oncall_user_on_leave(self, test_app, test_user):
        """Test qu'une astreinte ne peut pas être ajoutée si l'utilisateur est en congé."""
        with test_app.app_context():
            # Créer un congé
            start_date = datetime(2023, 12, 10).date()
            end_date = datetime(2023, 12, 15).date()
            leave = Leave(
                user_id=test_user.id, start_date=start_date, end_date=end_date
            )
            db.session.add(leave)
            db.session.commit()

            # Créer une astreinte qui chevauche le congé
            start_time = datetime(2023, 12, 8, 21, 0)  # Vendredi avant le congé
            end_time = start_time + timedelta(days=7, hours=-14)  # Chevauche le congé
            can_add = can_add_oncall(test_user, start_time, end_time)
            assert not can_add

    def test_can_add_oncall_overlapping(self, test_app, test_user):
        """Test qu'une astreinte ne peut pas être ajoutée si elle chevauche une autre."""
        with test_app.app_context():
            # Créer une astreinte existante
            start_time = datetime(2023, 12, 1, 21, 0)  # Vendredi 21h
            end_time = start_time + timedelta(days=7, hours=-14)
            oncall = OnCall(
                user_id=test_user.id, start_time=start_time, end_time=end_time
            )
            db.session.add(oncall)
            db.session.commit()

            # Essayer d'ajouter une astreinte qui chevauche
            new_start_time = datetime(2023, 12, 1, 21, 0)  # Même date
            new_end_time = new_start_time + timedelta(days=7, hours=-14)
            can_add = can_add_oncall(test_user, new_start_time, new_end_time)
            assert not can_add

    def test_can_add_oncall_different_users_same_period(
        self, test_app, test_user, second_user
    ):
        """Test que différents utilisateurs peuvent avoir des astreintes à la même période."""
        with test_app.app_context():
            start_time = datetime(2023, 12, 1, 21, 0)  # Vendredi 21h
            end_time = start_time + timedelta(days=7, hours=-14)

            # Ajouter une astreinte pour le premier utilisateur
            can_add1 = can_add_oncall(test_user, start_time, end_time)
            assert can_add1 is True

            # Ajouter une astreinte pour le deuxième utilisateur à la même période
            can_add2 = can_add_oncall(second_user, start_time, end_time)
            assert can_add2 is True


class TestCanAddLeave:
    """Tests pour can_add_leave."""

    def test_can_add_leave_valid(self, test_app, test_user, second_user):
        """Test qu'un congé peut être ajouté sur une période valide."""
        with test_app.app_context():
            start_date = datetime(2023, 12, 20).date()
            end_date = datetime(2023, 12, 25).date()
            can_add = can_add_leave(test_user, start_date, end_date)
            assert can_add is True

    def test_can_add_leave_invalid_dates(self, test_app, test_user):
        """Test qu'un congé ne peut pas être ajouté si la date de fin est avant la date de début."""
        with test_app.app_context():
            start_date = datetime(2023, 12, 25).date()
            end_date = datetime(
                2023, 12, 20
            ).date()  # Date de fin avant la date de début
            can_add = can_add_leave(test_user, start_date, end_date)
            assert not can_add

    def test_can_add_leave_same_day(self, test_app, test_user, second_user):
        """Test qu'un congé peut être ajouté pour un seul jour."""
        with test_app.app_context():
            start_date = datetime(2023, 12, 20).date()
            end_date = datetime(2023, 12, 20).date()
            can_add = can_add_leave(test_user, start_date, end_date)
            assert can_add is True

    def test_can_add_leave_overlapping(self, test_app, test_user):
        """Test qu'un congé ne peut pas être ajouté s'il chevauche un autre congé."""
        with test_app.app_context():
            # Créer un congé existant
            start_date = datetime(2023, 12, 10).date()
            end_date = datetime(2023, 12, 15).date()
            leave = Leave(
                user_id=test_user.id, start_date=start_date, end_date=end_date
            )
            db.session.add(leave)
            db.session.commit()

            can_add = can_add_leave(test_user, start_date, end_date)
            assert not can_add

    def test_can_add_leave_user_has_shift(
        self, test_app, test_user, second_user, test_shift_type
    ):
        """Test qu'un congé peut être ajouté même si l'utilisateur a un shift (les congés sont prioritaires)."""
        with test_app.app_context():
            # Créer un shift
            start_time = datetime(2023, 12, 1, 7, 0)
            end_time = datetime(2023, 12, 1, 15, 0)
            shift = Shift(
                user_id=test_user.id,
                shift_type_id=test_shift_type.id,
                start_time=start_time,
                end_time=end_time,
                date=start_time.date(),
            )
            db.session.add(shift)
            db.session.commit()

            start_date = shift.date
            end_date = shift.date + timedelta(days=1)
            can_add = can_add_leave(test_user, start_date, end_date)
            # Les congés sont prioritaires, donc cela doit être autorisé
            assert can_add is True

    def test_can_add_leave_user_has_oncall(self, test_app, test_user, second_user):
        """Test qu'un congé peut être ajouté même si l'utilisateur a une astreinte (les congés sont prioritaires)."""
        with test_app.app_context():
            # Créer une astreinte
            start_time = datetime(2023, 12, 1, 21, 0)  # Vendredi 21h
            end_time = start_time + timedelta(days=7, hours=-14)
            oncall = OnCall(
                user_id=test_user.id, start_time=start_time, end_time=end_time
            )
            db.session.add(oncall)
            db.session.commit()

            start_date = oncall.start_time.date()
            end_date = oncall.end_time.date()
            can_add = can_add_leave(test_user, start_date, end_date)
            # Les congés sont prioritaires, donc cela doit être autorisé
            assert can_add is True

    def test_can_add_leave_rejected_when_dropping_headcount_to_zero(
        self, test_app, test_user
    ):
        """Règle 6 : un congé qui ferait tomber l'effectif disponible à 0
        (seul utilisateur schedule-eligible) doit être refusé."""
        with test_app.app_context():
            # Mercredi ouvré, test_user est le seul utilisateur du groupe schedule
            start_date = date(2023, 12, 20)
            end_date = date(2023, 12, 20)
            can_add = can_add_leave(test_user, start_date, end_date)
            assert can_add is False

    def test_can_add_leave_allowed_when_headcount_stays_above_zero(
        self, test_app, test_user, second_user
    ):
        """Règle 6 : avec un deuxième utilisateur schedule-eligible
        disponible, le congé du premier reste autorisé."""
        with test_app.app_context():
            start_date = date(2023, 12, 20)
            end_date = date(2023, 12, 20)
            can_add = can_add_leave(test_user, start_date, end_date)
            assert can_add is True

    def test_can_add_leave_rejected_when_last_remaining_user_takes_leave(
        self, test_app, test_user, second_user
    ):
        """Règle 6 : si second_user est déjà en congé ce jour, test_user
        (dernier disponible) ne peut plus partir en congé le même jour."""
        with test_app.app_context():
            target_date = date(2023, 12, 20)
            existing_leave = Leave(
                user_id=second_user.id, start_date=target_date, end_date=target_date
            )
            db.session.add(existing_leave)
            db.session.commit()

            can_add = can_add_leave(test_user, target_date, target_date)
            assert can_add is False

    def test_can_add_leave_different_users_overlapping(
        self, test_app, test_user, second_user
    ):
        """Test que différents utilisateurs peuvent avoir des congés qui se chevauchent."""
        with test_app.app_context():
            start_date = datetime(2023, 12, 20).date()
            end_date = datetime(2023, 12, 25).date()

            # Ajouter un congé pour le premier utilisateur
            can_add1 = can_add_leave(test_user, start_date, end_date)
            assert can_add1 is True

            # Ajouter un congé pour le deuxième utilisateur à la même période
            can_add2 = can_add_leave(second_user, start_date, end_date)
            assert can_add2 is True


class TestGetBool:
    def test_true_variants(self, monkeypatch):
        for v in ("true", "1", "yes", "y", "on", "TRUE", "On"):
            monkeypatch.setenv("TEST_BOOL", v)
            assert get_bool("TEST_BOOL") is True

    def test_false_variants(self, monkeypatch):
        for v in ("false", "0", "no", "n", "off", "FALSE"):
            monkeypatch.setenv("TEST_BOOL", v)
            assert get_bool("TEST_BOOL") is False

    def test_missing_var_returns_default(self, monkeypatch):
        monkeypatch.delenv("TEST_BOOL_MISSING", raising=False)
        assert get_bool("TEST_BOOL_MISSING", default=True) is True
        assert get_bool("TEST_BOOL_MISSING", default=False) is False

    def test_unrecognized_value_returns_default(self, monkeypatch):
        monkeypatch.setenv("TEST_BOOL", "bogus")
        assert get_bool("TEST_BOOL", default=True) is True


class TestGetInt:
    def test_valid_int(self, monkeypatch):
        monkeypatch.setenv("TEST_INT", "42")
        assert get_int("TEST_INT") == 42

    def test_missing_var_returns_default(self, monkeypatch):
        monkeypatch.delenv("TEST_INT_MISSING", raising=False)
        assert get_int("TEST_INT_MISSING", default=7) == 7

    def test_invalid_value_returns_default(self, monkeypatch):
        monkeypatch.setenv("TEST_INT", "not-a-number")
        assert get_int("TEST_INT", default=99) == 99


class TestFormatFunctions:
    def test_format_date(self):
        assert format_date(date(2026, 7, 12)) == "2026-07-12"

    def test_format_date_none(self):
        assert format_date(None) == ""

    def test_format_datetime(self):
        assert format_datetime(datetime(2026, 7, 12, 9, 30, 0)) == "2026-07-12 09:30:00"

    def test_format_datetime_none(self):
        assert format_datetime(None) == ""

    def test_format_time(self):
        assert format_time(time(9, 30)) == "09:30"

    def test_format_time_none(self):
        assert format_time(None) == ""


class TestParseFunctions:
    def test_parse_date_valid(self):
        assert parse_date("2026-07-12") == date(2026, 7, 12)

    def test_parse_date_invalid(self):
        assert parse_date("not-a-date") is None

    def test_parse_date_none(self):
        assert parse_date(None) is None

    def test_parse_datetime_valid(self):
        assert parse_datetime("2026-07-12 09:30:00") == datetime(2026, 7, 12, 9, 30, 0)

    def test_parse_datetime_invalid(self):
        assert parse_datetime("not-a-datetime") is None


class TestDateHelpers:
    def test_get_current_year(self):
        assert get_current_year() == datetime.now().year

    def test_get_current_month(self):
        assert get_current_month() == datetime.now().month

    def test_get_days_in_month_regular(self):
        assert get_days_in_month(2026, 4) == 30

    def test_get_days_in_month_december(self):
        assert get_days_in_month(2026, 12) == 31

    def test_get_days_in_month_leap_february(self):
        assert get_days_in_month(2024, 2) == 29


class TestOverlappingShiftAndOnCallHelpers:
    def test_get_overlapping_shift_found(self, test_app, test_user, test_shift_type):
        with test_app.app_context():
            shift_date = date(2026, 7, 13)
            shift = Shift(
                user_id=test_user.id,
                shift_type_id=test_shift_type.id,
                start_time=datetime.combine(shift_date, datetime.min.time()),
                end_time=datetime.combine(shift_date, datetime.max.time()),
                date=shift_date,
            )
            db.session.add(shift)
            db.session.commit()

            result = _get_overlapping_shift(
                test_user.id, date(2026, 7, 10), date(2026, 7, 15)
            )
            assert result is not None
            assert result.id == shift.id

    def test_get_overlapping_shift_none(self, test_app, test_user):
        with test_app.app_context():
            result = _get_overlapping_shift(
                test_user.id, date(2026, 7, 10), date(2026, 7, 15)
            )
            assert result is None

    def test_get_overlapping_oncall_found(self, test_app, test_user):
        with test_app.app_context():
            start = datetime(2026, 7, 10, 21, 0)
            end = start + timedelta(days=7, hours=-14)
            oncall = OnCall(user_id=test_user.id, start_time=start, end_time=end)
            db.session.add(oncall)
            db.session.commit()

            result = _get_overlapping_oncall(
                test_user.id, date(2026, 7, 9), date(2026, 7, 16)
            )
            assert result is not None
            assert result.id == oncall.id

    def test_get_overlapping_oncall_none(self, test_app, test_user):
        with test_app.app_context():
            result = _get_overlapping_oncall(
                test_user.id, date(2026, 7, 9), date(2026, 7, 16)
            )
            assert result is None
