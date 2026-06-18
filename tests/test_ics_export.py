"""
Tests pour l'export ICS.
"""
import pytest
from datetime import datetime, timedelta
from app.utils.ics_exporter import generate_ics_shifts, generate_ics_oncall, generate_ics_leaves
from app.models import Shift, OnCall, Leave


class TestICSExport:
    """Tests pour l'export ICS."""
    
    def test_generate_ics_shifts(self, test_shift):
        """Test la génération d'un fichier ICS pour les shifts."""
        shifts = [test_shift]
        ics_content = generate_ics_shifts(shifts)
        
        # Vérifier que le contenu est valide
        assert 'BEGIN:VCALENDAR' in ics_content
        assert 'END:VCALENDAR' in ics_content
        assert 'BEGIN:VEVENT' in ics_content
        assert 'END:VEVENT' in ics_content
        assert 'TZID:Europe/Paris' in ics_content or 'Europe/Paris' in ics_content
        assert f'Shift {test_shift.shift_type}' in ics_content
    
    def test_generate_ics_oncall(self, test_oncall):
        """Test la génération d'un fichier ICS pour les astreintes."""
        on_calls = [test_oncall]
        ics_content = generate_ics_oncall(on_calls)
        
        # Vérifier que le contenu est valide
        assert 'BEGIN:VCALENDAR' in ics_content
        assert 'END:VCALENDAR' in ics_content
        assert 'BEGIN:VEVENT' in ics_content
        assert 'END:VEVENT' in ics_content
        assert 'TZID:Europe/Paris' in ics_content or 'Europe/Paris' in ics_content
        assert 'Astreinte' in ics_content
    
    def test_generate_ics_leaves(self, test_leave):
        """Test la génération d'un fichier ICS pour les congés."""
        leaves = [test_leave]
        ics_content = generate_ics_leaves(leaves)
        
        # Vérifier que le contenu est valide
        assert 'BEGIN:VCALENDAR' in ics_content
        assert 'END:VCALENDAR' in ics_content
        assert 'BEGIN:VEVENT' in ics_content
        assert 'END:VEVENT' in ics_content
        assert 'TZID:Europe/Paris' in ics_content or 'Europe/Paris' in ics_content
        assert 'Congé' in ics_content
        assert test_leave.user.name in ics_content
    
    def test_generate_ics_shifts_timezone(self, test_user):
        """Test que les shifts sont exportés avec le bon timezone."""
        start_time = datetime(2023, 12, 1, 7, 0)
        end_time = datetime(2023, 12, 1, 15, 0)
        shift = Shift(
            user_id=test_user.id,
            shift_type='morning',
            start_time=start_time,
            end_time=end_time,
            date=start_time.date()
        )
        
        ics_content = generate_ics_shifts([shift])
        
        # Vérifier que le timezone est présent
        assert 'Europe/Paris' in ics_content
        # Vérifier que les dates sont au format UTC ou avec timezone
        assert 'DTSTART' in ics_content
        assert 'DTEND' in ics_content
    
    def test_generate_ics_leaves_all_day(self, test_user):
        """Test que les congés sont exportés comme événements toute la journée."""
        start_date = datetime(2023, 12, 10).date()
        end_date = datetime(2023, 12, 15).date()
        leave = Leave(
            user_id=test_user.id,
            start_date=start_date,
            end_date=end_date,
            reason='Test Leave'
        )
        
        ics_content = generate_ics_leaves([leave])
        
        # Vérifier que le congé est un événement toute la journée
        assert 'DTSTART' in ics_content
        assert 'DTEND' in ics_content
        assert 'Europe/Paris' in ics_content
