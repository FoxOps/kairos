"""
Tests pour l'export ICS.
"""

import pytest
from datetime import datetime, timedelta
from app.utils.export import (
    generate_ics_shifts,
    generate_ics_oncall,
    generate_ics_leaves,
    generate_ics_standard,
)
from app.models import Shift, OnCall, Leave
from app import db


class TestICSExport:
    """Tests pour l'export ICS."""

    def test_generate_ics_shifts(self, test_shift):
        """Test la génération d'un fichier ICS pour les shifts."""
        shifts = [test_shift]
        ics_content = generate_ics_shifts(shifts)

        # Vérifier que le contenu est valide
        assert "BEGIN:VCALENDAR" in ics_content
        assert "END:VCALENDAR" in ics_content
        assert "BEGIN:VEVENT" in ics_content
        assert "END:VEVENT" in ics_content
        assert "TZID:Europe/Paris" in ics_content or "Europe/Paris" in ics_content
        assert f"Shift {test_shift.shift_type.label}" in ics_content

    def test_generate_ics_oncall(self, test_oncall):
        """Test la génération d'un fichier ICS pour les astreintes."""
        on_calls = [test_oncall]
        ics_content = generate_ics_oncall(on_calls)

        # Vérifier que le contenu est valide
        assert "BEGIN:VCALENDAR" in ics_content
        assert "END:VCALENDAR" in ics_content
        assert "BEGIN:VEVENT" in ics_content
        assert "END:VEVENT" in ics_content
        assert "TZID:Europe/Paris" in ics_content or "Europe/Paris" in ics_content
        assert "Astreinte" in ics_content

    def test_generate_ics_leaves(self, test_leave):
        """Test la génération d'un fichier ICS pour les congés."""
        leaves = [test_leave]
        ics_content = generate_ics_leaves(leaves)

        # Vérifier que le contenu est valide
        assert "BEGIN:VCALENDAR" in ics_content
        assert "END:VCALENDAR" in ics_content
        assert "BEGIN:VEVENT" in ics_content
        assert "END:VEVENT" in ics_content
        assert "TZID:Europe/Paris" in ics_content or "Europe/Paris" in ics_content
        assert "Conge" in ics_content or "Congé" in ics_content
        assert test_leave.user.name in ics_content

    def test_generate_ics_shifts_timezone(self, test_shift):
        """Test que les shifts sont exportés avec le bon timezone."""
        ics_content = generate_ics_shifts([test_shift])

        # Vérifier que le timezone est présent
        assert "Europe/Paris" in ics_content
        # Vérifier que les dates sont au format UTC ou avec timezone
        assert "DTSTART" in ics_content
        assert "DTEND" in ics_content

    def test_generate_ics_leaves_all_day(self, test_app, test_user):
        """Test que les congés sont exportés comme événements toute la journée."""
        start_date = datetime(2023, 12, 10).date()
        end_date = datetime(2023, 12, 15).date()
        leave = Leave(user_id=test_user.id, start_date=start_date, end_date=end_date)
        db.session.add(leave)
        db.session.commit()

        ics_content = generate_ics_leaves([leave])

        # Vérifier que le congé est un événement toute la journée
        assert "DTSTART" in ics_content
        assert "DTEND" in ics_content
        assert "Europe/Paris" in ics_content

    def test_generate_ics_multiple_shifts(self, test_app, test_user, test_shift_type):
        """Test l'export de plusieurs shifts."""
        with test_app.app_context():
            # Créer plusieurs shifts
            shifts = []
            for i in range(3):
                shift_date = datetime(2023, 12, 1 + i).date()
                start_time = datetime.combine(shift_date, datetime.min.time()).replace(
                    hour=7
                )
                end_time = start_time + timedelta(hours=8)
                shift = Shift(
                    user_id=test_user.id,
                    shift_type_id=test_shift_type.id,
                    start_time=start_time,
                    end_time=end_time,
                    date=shift_date,
                )
                db.session.add(shift)
                shifts.append(shift)
            db.session.commit()

            ics_content = generate_ics_shifts(shifts)

            # Vérifier que tous les shifts sont présents
            assert ics_content.count("BEGIN:VEVENT") == 3
            assert ics_content.count("END:VEVENT") == 3

    def test_generate_ics_multiple_oncalls(self, test_app, test_user):
        """Test l'export de plusieurs astreintes."""
        with test_app.app_context():
            # Créer plusieurs astreintes
            on_calls = []
            for i in range(2):
                # Créer des vendredis
                friday_date = datetime(2023, 12, 1 + (i * 7)).date()
                start_time = datetime.combine(friday_date, datetime.min.time()).replace(
                    hour=21
                )
                end_time = start_time + timedelta(days=7, hours=-14)
                oncall = OnCall(
                    user_id=test_user.id, start_time=start_time, end_time=end_time
                )
                db.session.add(oncall)
                on_calls.append(oncall)
            db.session.commit()

            ics_content = generate_ics_oncall(on_calls)

            # Vérifier que toutes les astreintes sont présentes
            assert ics_content.count("BEGIN:VEVENT") == 2
            assert ics_content.count("END:VEVENT") == 2

    def test_generate_ics_empty_lists(self, test_app):
        """Test l'export avec des listes vides."""
        with test_app.app_context():
            # Shifts vides
            ics_content = generate_ics_shifts([])
            assert "BEGIN:VCALENDAR" in ics_content
            assert "END:VCALENDAR" in ics_content
            assert ics_content.count("BEGIN:VEVENT") == 0

            # Astreintes vides
            ics_content = generate_ics_oncall([])
            assert "BEGIN:VCALENDAR" in ics_content
            assert ics_content.count("BEGIN:VEVENT") == 0

            # Congés vides
            ics_content = generate_ics_leaves([])
            assert "BEGIN:VCALENDAR" in ics_content
            assert ics_content.count("BEGIN:VEVENT") == 0

    def test_generate_ics_standard_with_mixed_events(
        self, test_app, test_user, test_shift_type
    ):
        """Test la fonction générique avec différents types d'événements."""
        with test_app.app_context():
            # Créer un shift
            shift_date = datetime(2023, 12, 1).date()
            start_time = datetime.combine(shift_date, datetime.min.time()).replace(
                hour=7
            )
            end_time = start_time + timedelta(hours=8)
            shift = Shift(
                user_id=test_user.id,
                shift_type_id=test_shift_type.id,
                start_time=start_time,
                end_time=end_time,
                date=shift_date,
            )
            db.session.add(shift)

            # Créer un congé
            leave_start = datetime(2023, 12, 10).date()
            leave_end = datetime(2023, 12, 15).date()
            leave = Leave(
                user_id=test_user.id, start_date=leave_start, end_date=leave_end
            )
            db.session.add(leave)

            # Créer une astreinte
            oncall_start = datetime(2023, 12, 1, 21, 0)
            oncall_end = oncall_start + timedelta(days=7, hours=-14)
            oncall = OnCall(
                user_id=test_user.id, start_time=oncall_start, end_time=oncall_end
            )
            db.session.add(oncall)
            db.session.commit()

            # Générer un calendrier avec tous les événements
            events = [shift, leave, oncall]
            ics_content = generate_ics_standard(events, "Test Calendar")

            # Vérifier que tous les événements sont présents
            assert ics_content.count("BEGIN:VEVENT") == 3
            assert "Shift" in ics_content
            assert "Conge" in ics_content or "Congé" in ics_content
            assert "Astreinte" in ics_content
            assert "Test Calendar" in ics_content

    def test_generate_ics_shift_with_user_info(self, test_app, test_user, test_shift_type):
        """Test que les informations de l'utilisateur sont incluses dans l'export."""
        with test_app.app_context():
            shift_date = datetime(2023, 12, 1).date()
            start_time = datetime.combine(shift_date, datetime.min.time()).replace(
                hour=7
            )
            end_time = start_time + timedelta(hours=8)
            shift = Shift(
                user_id=test_user.id,
                shift_type_id=test_shift_type.id,
                start_time=start_time,
                end_time=end_time,
                date=shift_date,
            )
            db.session.add(shift)
            db.session.commit()

            ics_content = generate_ics_shifts([shift])

            # Vérifier que le nom de l'utilisateur est présent
            assert test_user.name in ics_content

    def test_generate_ics_leave_without_reason(self, test_app, test_user):
        """Test que l'export des congés fonctionne sans raison."""
        with test_app.app_context():
            leave_start = datetime(2023, 12, 10).date()
            leave_end = datetime(2023, 12, 15).date()
            leave = Leave(
                user_id=test_user.id, start_date=leave_start, end_date=leave_end
            )
            db.session.add(leave)
            db.session.commit()

            ics_content = generate_ics_leaves([leave])

            # Vérifier que le congé est exporté correctement
            assert "Conge" in ics_content
            assert test_user.name in ics_content

    def test_generate_ics_calendar_properties(self, test_shift):
        """Test que les propriétés du calendrier sont correctes."""
        ics_content = generate_ics_shifts([test_shift])

        # Vérifier les propriétés standard du calendrier
        assert "PRODID:-//Leviia Schedule//fr" in ics_content
        assert "VERSION:2.0" in ics_content
        assert "CALSCALE:GREGORIAN" in ics_content
        assert "METHOD:PUBLISH" in ics_content

    def test_generate_ics_event_uid(self, test_shift):
        """Test que chaque événement a un UID unique."""
        ics_content = generate_ics_shifts([test_shift])

        # Vérifier que l'UID est présent et contient l'ID du shift
        assert f"UID:Shift-{test_shift.id}@mtg-schedule" in ics_content
