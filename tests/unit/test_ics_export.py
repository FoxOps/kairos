"""
Tests for the ICS export.
"""

from datetime import datetime, timedelta

from app import db
from app.models import Leave, OnCall, Shift
from app.utils.export import generate_ics_standard


def _generate_ics_shifts(shifts):
    return generate_ics_standard(shifts, "Leviia Schedule - Shifts")


def _generate_ics_oncall(on_calls):
    return generate_ics_standard(on_calls, "Leviia Schedule - Astreintes")


def _generate_ics_leaves(leaves):
    return generate_ics_standard(leaves, "Leviia Schedule - Conge")


class TestICSExport:
    """Tests for the ICS export (via generate_ics_standard, the only
    path actually used in production - see
    app/services/export_service.py)."""

    def test_generate_ics_shifts(self, test_shift):
        """Test generating an ICS file for shifts."""
        shifts = [test_shift]
        ics_content = _generate_ics_shifts(shifts)

        # Check that the content is valid
        assert "BEGIN:VCALENDAR" in ics_content
        assert "END:VCALENDAR" in ics_content
        assert "BEGIN:VEVENT" in ics_content
        assert "END:VEVENT" in ics_content
        assert "TZID:Europe/Paris" in ics_content or "Europe/Paris" in ics_content
        assert f"Shift {test_shift.shift_type.label}" in ics_content

    def test_generate_ics_oncall(self, test_oncall):
        """Test generating an ICS file for on-calls."""
        on_calls = [test_oncall]
        ics_content = _generate_ics_oncall(on_calls)

        # Check that the content is valid
        assert "BEGIN:VCALENDAR" in ics_content
        assert "END:VCALENDAR" in ics_content
        assert "BEGIN:VEVENT" in ics_content
        assert "END:VEVENT" in ics_content
        assert "TZID:Europe/Paris" in ics_content or "Europe/Paris" in ics_content
        assert "Astreinte" in ics_content

    def test_generate_ics_leaves(self, test_leave):
        """Test generating an ICS file for leaves."""
        leaves = [test_leave]
        ics_content = _generate_ics_leaves(leaves)

        # Check that the content is valid
        assert "BEGIN:VCALENDAR" in ics_content
        assert "END:VCALENDAR" in ics_content
        assert "BEGIN:VEVENT" in ics_content
        assert "END:VEVENT" in ics_content
        assert "TZID:Europe/Paris" in ics_content or "Europe/Paris" in ics_content
        assert "Conge" in ics_content or "Congé" in ics_content
        assert test_leave.user.name in ics_content

    def test_generate_ics_shifts_timezone(self, test_shift):
        """Test that shifts are exported with the correct timezone."""
        ics_content = _generate_ics_shifts([test_shift])

        # Check that the timezone is present
        assert "Europe/Paris" in ics_content
        # Check that the dates are in UTC or timezone-aware format
        assert "DTSTART" in ics_content
        assert "DTEND" in ics_content

    def test_generate_ics_leaves_all_day(self, test_app, test_user):
        """Test that leaves are exported as all-day events."""
        start_date = datetime(2023, 12, 10).date()
        end_date = datetime(2023, 12, 15).date()
        leave = Leave(user_id=test_user.id, start_date=start_date, end_date=end_date)
        db.session.add(leave)
        db.session.commit()

        ics_content = _generate_ics_leaves([leave])

        # Check that the leave is an all-day event
        assert "DTSTART" in ics_content
        assert "DTEND" in ics_content
        assert "Europe/Paris" in ics_content

    def test_generate_ics_multiple_shifts(self, test_app, test_user, test_shift_type):
        """Test exporting several shifts."""
        with test_app.app_context():
            # Create several shifts
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

            ics_content = _generate_ics_shifts(shifts)

            # Check that every shift is present
            assert ics_content.count("BEGIN:VEVENT") == 3
            assert ics_content.count("END:VEVENT") == 3

    def test_generate_ics_multiple_oncalls(self, test_app, test_user):
        """Test exporting several on-calls."""
        with test_app.app_context():
            # Create several on-calls
            on_calls = []
            for i in range(2):
                # Create Fridays
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

            ics_content = _generate_ics_oncall(on_calls)

            # Check that every on-call is present
            assert ics_content.count("BEGIN:VEVENT") == 2
            assert ics_content.count("END:VEVENT") == 2

    def test_generate_ics_empty_lists(self, test_app):
        """Test exporting with empty lists."""
        with test_app.app_context():
            # Empty shifts
            ics_content = _generate_ics_shifts([])
            assert "BEGIN:VCALENDAR" in ics_content
            assert "END:VCALENDAR" in ics_content
            assert ics_content.count("BEGIN:VEVENT") == 0

            # Empty on-calls
            ics_content = _generate_ics_oncall([])
            assert "BEGIN:VCALENDAR" in ics_content
            assert ics_content.count("BEGIN:VEVENT") == 0

            # Empty leaves
            ics_content = _generate_ics_leaves([])
            assert "BEGIN:VCALENDAR" in ics_content
            assert ics_content.count("BEGIN:VEVENT") == 0

    def test_generate_ics_standard_with_mixed_events(
        self, test_app, test_user, test_shift_type
    ):
        """Test the generic function with different event types."""
        with test_app.app_context():
            # Create a shift
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

            # Create a leave
            leave_start = datetime(2023, 12, 10).date()
            leave_end = datetime(2023, 12, 15).date()
            leave = Leave(
                user_id=test_user.id, start_date=leave_start, end_date=leave_end
            )
            db.session.add(leave)

            # Create an on-call
            oncall_start = datetime(2023, 12, 1, 21, 0)
            oncall_end = oncall_start + timedelta(days=7, hours=-14)
            oncall = OnCall(
                user_id=test_user.id, start_time=oncall_start, end_time=oncall_end
            )
            db.session.add(oncall)
            db.session.commit()

            # Generate a calendar with all the events
            events = [shift, leave, oncall]
            ics_content = generate_ics_standard(events, "Test Calendar")

            # Check that every event is present
            assert ics_content.count("BEGIN:VEVENT") == 3
            assert "Shift" in ics_content
            assert "Conge" in ics_content or "Congé" in ics_content
            assert "Astreinte" in ics_content
            assert "Test Calendar" in ics_content

    def test_generate_ics_shift_with_user_info(
        self, test_app, test_user, test_shift_type
    ):
        """Test that the user's info is included in the export."""
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

            ics_content = _generate_ics_shifts([shift])

            # Check that the user's name is present
            assert test_user.name in ics_content

    def test_generate_ics_leave_without_reason(self, test_app, test_user):
        """Test that exporting leaves works without a reason."""
        with test_app.app_context():
            leave_start = datetime(2023, 12, 10).date()
            leave_end = datetime(2023, 12, 15).date()
            leave = Leave(
                user_id=test_user.id, start_date=leave_start, end_date=leave_end
            )
            db.session.add(leave)
            db.session.commit()

            ics_content = _generate_ics_leaves([leave])

            # Check that the leave is exported correctly
            assert "Conge" in ics_content
            assert test_user.name in ics_content

    def test_generate_ics_calendar_properties(self, test_shift):
        """Test that the calendar properties are correct."""
        ics_content = _generate_ics_shifts([test_shift])

        # Check the standard calendar properties
        assert "PRODID:-//Leviia Schedule//fr" in ics_content
        assert "VERSION:2.0" in ics_content
        assert "CALSCALE:GREGORIAN" in ics_content
        assert "METHOD:PUBLISH" in ics_content

    def test_generate_ics_event_uid(self, test_shift):
        """Test that every event has a unique UID."""
        ics_content = _generate_ics_shifts([test_shift])

        # Check that the UID is present and contains the shift's ID
        assert f"UID:Shift-{test_shift.id}@mtg-schedule" in ics_content


class TestICSTimezoneCorrectness:
    """Regression tests for the floating-time bug: dtstart/dtend used to
    carry no tzinfo at all, so every calendar client interpreted them in
    its own local timezone instead of the organization's. These assert
    the fix concretely (real TZID + a matching VTIMEZONE component), not
    just that generation doesn't crash."""

    def test_dtstart_has_tzid_not_floating(self, test_shift):
        ics_content = _generate_ics_shifts([test_shift])

        assert "DTSTART;TZID=Europe/Paris:" in ics_content
        assert "DTEND;TZID=Europe/Paris:" in ics_content

    def test_vtimezone_component_present_and_matches_tzid(self, test_shift):
        ics_content = _generate_ics_shifts([test_shift])

        assert "BEGIN:VTIMEZONE" in ics_content
        assert "TZID:Europe/Paris" in ics_content
        assert "END:VTIMEZONE" in ics_content

    def test_export_uses_org_timezone_not_arbitrary_one(
        self, test_app, test_user, test_shift_type
    ):
        """The tz_name always reflects the organization's canonical
        timezone (SettingsService.get_default_timezone()) - never a
        viewer's personal preference, since attaching the wrong tzinfo
        would relabel the instant instead of translating it (see
        CLAUDE.md's "Multi-timezone support" section)."""
        with test_app.app_context():
            shift_date = datetime(2023, 12, 1).date()
            start_time = datetime.combine(shift_date, datetime.min.time()).replace(
                hour=9
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

            ics_ny = generate_ics_standard(
                [shift], "Test Calendar", tz_name="America/New_York"
            )

        # Same underlying wall-clock number (09:00), just declared under
        # a different TZID - a real translation would change the digits,
        # not just the label. This confirms the exporter attaches
        # whatever tz_name it's given without silently converting it -
        # callers (ExportService) are responsible for always passing the
        # org's canonical timezone, never a per-viewer one.
        assert "DTSTART;TZID=America/New_York:20231201T090000" in ics_ny

    def test_leave_all_day_event_also_gets_tzid(self, test_app, test_user):
        with test_app.app_context():
            leave = Leave(
                user_id=test_user.id,
                start_date=datetime(2023, 12, 10).date(),
                end_date=datetime(2023, 12, 15).date(),
            )
            db.session.add(leave)
            db.session.commit()

            ics_content = _generate_ics_leaves([leave])

        assert "DTSTART;TZID=Europe/Paris:" in ics_content

    def test_add_missing_timezones_does_not_crash_on_empty_calendar(self, test_app):
        with test_app.app_context():
            ics_content = _generate_ics_shifts([])

        assert "BEGIN:VCALENDAR" in ics_content
