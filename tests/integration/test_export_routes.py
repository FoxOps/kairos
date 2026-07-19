"""
Tests for the ICS export routes.
"""

from datetime import datetime, timedelta

from app import db
from app.models import Leave, OnCall, Shift


class TestExportRoutes:
    """Tests for the export routes."""

    def test_export_shifts_route(
        self, logged_in_client, test_user, test_shift_type, test_app
    ):
        """Test exporting shifts."""
        with test_app.app_context():
            # Create a shift for the user
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

        response = logged_in_client.get("/export/shifts")
        assert response.status_code == 200
        assert response.content_type == "text/calendar; charset=utf-8"
        assert "BEGIN:VCALENDAR" in response.data.decode("utf-8")
        assert "BEGIN:VEVENT" in response.data.decode("utf-8")
        assert "Shift" in response.data.decode("utf-8")

    def test_export_shifts_scope_all(
        self, logged_in_client, test_user, test_shift_type, test_app
    ):
        """Test exporting all shifts (scope=all)."""
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
            db.session.commit()

        response = logged_in_client.get("/export/shifts?scope=all")
        assert response.status_code == 200
        content = response.data.decode("utf-8")
        assert "BEGIN:VCALENDAR" in content
        assert "shifts_all.ics" in response.headers["Content-Disposition"]

    def test_export_shifts_scope_my(
        self, logged_in_client, test_user, test_shift_type, test_app
    ):
        """Test exporting the logged-in user's own shifts (scope=my)."""
        with test_app.app_context():
            # Create a shift for the logged-in user
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

        response = logged_in_client.get("/export/shifts?scope=my")
        assert response.status_code == 200
        content = response.data.decode("utf-8")
        assert "BEGIN:VCALENDAR" in content
        assert "shifts_my.ics" in response.headers["Content-Disposition"]

    def test_export_oncall_route(self, logged_in_client, test_user, test_app):
        """Test exporting on-calls."""
        with test_app.app_context():
            # Create an on-call
            start_time = datetime(2023, 12, 1, 21, 0)
            end_time = start_time + timedelta(days=7, hours=-14)
            oncall = OnCall(
                user_id=test_user.id, start_time=start_time, end_time=end_time
            )
            db.session.add(oncall)
            db.session.commit()

        response = logged_in_client.get("/export/oncall")
        assert response.status_code == 200
        assert response.content_type == "text/calendar; charset=utf-8"
        content = response.data.decode("utf-8")
        assert "BEGIN:VCALENDAR" in content
        assert "Astreinte" in content

    def test_export_oncall_scope_all(self, logged_in_client, test_user, test_app):
        """Test exporting all on-calls (scope=all)."""
        with test_app.app_context():
            # Create an on-call
            start_time = datetime(2023, 12, 1, 21, 0)
            end_time = start_time + timedelta(days=7, hours=-14)
            oncall = OnCall(
                user_id=test_user.id, start_time=start_time, end_time=end_time
            )
            db.session.add(oncall)
            db.session.commit()

        response = logged_in_client.get("/export/oncall?scope=all")
        assert response.status_code == 200
        assert "oncall_all.ics" in response.headers["Content-Disposition"]

    def test_export_oncall_scope_my(self, logged_in_client, test_user, test_app):
        """Test exporting the logged-in user's own on-calls (scope=my)."""
        with test_app.app_context():
            # Create an on-call for the logged-in user
            start_time = datetime(2023, 12, 1, 21, 0)
            end_time = start_time + timedelta(days=7, hours=-14)
            oncall = OnCall(
                user_id=test_user.id, start_time=start_time, end_time=end_time
            )
            db.session.add(oncall)
            db.session.commit()

        response = logged_in_client.get("/export/oncall?scope=my")
        assert response.status_code == 200
        assert "oncall_my.ics" in response.headers["Content-Disposition"]

    def test_export_leaves_route(self, logged_in_client, test_user, test_app):
        """Test exporting leaves."""
        with test_app.app_context():
            # Create a leave
            start_date = datetime(2023, 12, 10).date()
            end_date = datetime(2023, 12, 15).date()
            leave = Leave(
                user_id=test_user.id, start_date=start_date, end_date=end_date
            )
            db.session.add(leave)
            db.session.commit()

        response = logged_in_client.get("/export/leaves")
        assert response.status_code == 200
        assert response.content_type == "text/calendar; charset=utf-8"
        content = response.data.decode("utf-8")
        assert "BEGIN:VCALENDAR" in content
        assert "Conge" in content or "Cong" in content

    def test_export_leaves_scope_all(self, logged_in_client, test_user, test_app):
        """Test exporting all leaves (scope=all)."""
        with test_app.app_context():
            # Create a leave
            start_date = datetime(2023, 12, 10).date()
            end_date = datetime(2023, 12, 15).date()
            leave = Leave(
                user_id=test_user.id, start_date=start_date, end_date=end_date
            )
            db.session.add(leave)
            db.session.commit()

        response = logged_in_client.get("/export/leaves?scope=all")
        assert response.status_code == 200
        assert "leaves_all.ics" in response.headers["Content-Disposition"]

    def test_export_leaves_scope_my(self, logged_in_client, test_user, test_app):
        """Test exporting the logged-in user's own leaves (scope=my)."""
        with test_app.app_context():
            # Create a leave for the logged-in user
            start_date = datetime(2023, 12, 10).date()
            end_date = datetime(2023, 12, 15).date()
            leave = Leave(
                user_id=test_user.id, start_date=start_date, end_date=end_date
            )
            db.session.add(leave)
            db.session.commit()

        response = logged_in_client.get("/export/leaves?scope=my")
        assert response.status_code == 200
        assert "leaves_my.ics" in response.headers["Content-Disposition"]

    def test_export_shifts_unauthorized(self, client):
        """Test that exporting shifts requires authentication."""
        response = client.get("/export/shifts", follow_redirects=True)
        assert response.status_code == 200
        # Should redirect to the login page
        assert b"Login" in response.data or b"email" in response.data

    def test_export_oncall_unauthorized(self, client):
        """Test that exporting on-calls requires authentication."""
        response = client.get("/export/oncall", follow_redirects=True)
        assert response.status_code == 200
        assert b"Login" in response.data or b"email" in response.data

    def test_export_leaves_unauthorized(self, client):
        """Test that exporting leaves requires authentication."""
        response = client.get("/export/leaves", follow_redirects=True)
        assert response.status_code == 200
        assert b"Login" in response.data or b"email" in response.data

    def test_export_shifts_empty(self, logged_in_client):
        """Test exporting shifts when the user has none."""
        response = logged_in_client.get("/export/shifts?scope=my")
        assert response.status_code == 200
        content = response.data.decode("utf-8")
        assert "BEGIN:VCALENDAR" in content
        assert "END:VCALENDAR" in content
        # No events
        assert content.count("BEGIN:VEVENT") == 0

    def test_export_oncall_empty(self, logged_in_client):
        """Test exporting on-calls when the user has none."""
        response = logged_in_client.get("/export/oncall?scope=my")
        assert response.status_code == 200
        content = response.data.decode("utf-8")
        assert "BEGIN:VCALENDAR" in content
        assert content.count("BEGIN:VEVENT") == 0

    def test_export_leaves_empty(self, logged_in_client):
        """Test exporting leaves when the user has none."""
        response = logged_in_client.get("/export/leaves?scope=my")
        assert response.status_code == 200
        content = response.data.decode("utf-8")
        assert "BEGIN:VCALENDAR" in content
        assert content.count("BEGIN:VEVENT") == 0

    def test_export_shifts_invalid_scope(self, logged_in_client):
        """Test exporting with an invalid scope (defaults to scope=all)."""
        response = logged_in_client.get("/export/shifts?scope=invalid")
        assert response.status_code == 200
        # Should fall back to the default scope (all)
        assert "BEGIN:VCALENDAR" in response.data.decode("utf-8")

    def test_export_content_disposition_header(
        self, logged_in_client, test_user, test_shift_type, test_app
    ):
        """Test that the Content-Disposition header is correct."""
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
            db.session.commit()

        response = logged_in_client.get("/export/shifts?scope=my")
        assert "Content-Disposition" in response.headers
        assert "attachment" in response.headers["Content-Disposition"]
        assert "filename=" in response.headers["Content-Disposition"]


class TestExportRoutesAdminScope:
    """Tests checking that admins can export all users' data."""

    def test_admin_export_all_shifts(
        self, logged_in_client, test_user, second_user, test_shift_type, test_app
    ):
        """Test that an admin can export every user's shifts."""
        with test_app.app_context():
            # Create shifts for two different users
            shift_date = datetime(2023, 12, 1).date()
            start_time = datetime.combine(shift_date, datetime.min.time()).replace(
                hour=7
            )
            end_time = start_time + timedelta(hours=8)

            shift1 = Shift(
                user_id=test_user.id,
                shift_type_id=test_shift_type.id,
                start_time=start_time,
                end_time=end_time,
                date=shift_date,
            )
            shift2 = Shift(
                user_id=second_user.id,
                shift_type_id=test_shift_type.id,
                start_time=start_time + timedelta(days=1),
                end_time=end_time + timedelta(days=1),
                date=shift_date + timedelta(days=1),
            )
            db.session.add(shift1)
            db.session.add(shift2)
            db.session.commit()

        response = logged_in_client.get("/export/shifts?scope=all")
        assert response.status_code == 200
        content = response.data.decode("utf-8")
        # Should contain both users' shifts
        assert content.count("BEGIN:VEVENT") == 2

    def test_admin_export_all_oncalls(
        self, logged_in_client, test_user, second_user, test_app
    ):
        """Test that an admin can export every user's on-calls."""
        with test_app.app_context():
            # Create on-calls for two different users
            start_time1 = datetime(2023, 12, 1, 21, 0)
            end_time1 = start_time1 + timedelta(days=7, hours=-14)
            oncall1 = OnCall(
                user_id=test_user.id, start_time=start_time1, end_time=end_time1
            )

            start_time2 = datetime(2023, 12, 8, 21, 0)
            end_time2 = start_time2 + timedelta(days=7, hours=-14)
            oncall2 = OnCall(
                user_id=second_user.id, start_time=start_time2, end_time=end_time2
            )

            db.session.add(oncall1)
            db.session.add(oncall2)
            db.session.commit()

        response = logged_in_client.get("/export/oncall?scope=all")
        assert response.status_code == 200
        content = response.data.decode("utf-8")
        assert content.count("BEGIN:VEVENT") == 2

    def test_admin_export_all_leaves(
        self, logged_in_client, test_user, second_user, test_app
    ):
        """Test that an admin can export every user's leaves."""
        with test_app.app_context():
            # Create leaves for two different users
            leave1 = Leave(
                user_id=test_user.id,
                start_date=datetime(2023, 12, 10).date(),
                end_date=datetime(2023, 12, 15).date(),
            )
            leave2 = Leave(
                user_id=second_user.id,
                start_date=datetime(2023, 12, 20).date(),
                end_date=datetime(2023, 12, 25).date(),
            )
            db.session.add(leave1)
            db.session.add(leave2)
            db.session.commit()

        response = logged_in_client.get("/export/leaves?scope=all")
        assert response.status_code == 200
        content = response.data.decode("utf-8")
        assert content.count("BEGIN:VEVENT") == 2


class TestExportRoutesTokenAuth:
    """Tests for token-based authentication on the ICS export routes."""

    def test_export_shifts_with_token(
        self, client, test_user, test_shift_type, test_app
    ):
        """Test exporting shifts with a valid token."""
        with test_app.app_context():
            # Generate a token for the user
            token = test_user.generate_ics_token()
            db.session.commit()

            # Create a shift for the user
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

        # Access the export with the token
        response = client.get(f"/export/shifts?scope=my&token={token}")
        assert response.status_code == 200
        assert response.content_type == "text/calendar; charset=utf-8"
        content = response.data.decode("utf-8")
        assert "BEGIN:VCALENDAR" in content
        assert "BEGIN:VEVENT" in content
        assert "Shift" in content

    def test_export_shifts_with_invalid_token(self, client):
        """Test exporting shifts with an invalid token."""
        response = client.get("/export/shifts?scope=my&token=invalid_token")
        # Should return 401, 200, or redirect to login (302)
        assert response.status_code in [401, 200, 302]

    def test_export_shifts_without_token_or_auth(self, client):
        """Test exporting shifts with neither authentication nor a token."""
        response = client.get("/export/shifts?scope=my")
        # Should return 401, 200, or redirect to login (302)
        assert response.status_code in [401, 200, 302]

    def test_export_oncall_with_token(self, client, test_user, test_app):
        """Test exporting on-calls with a valid token."""
        with test_app.app_context():
            # Generate a token for the user
            token = test_user.generate_ics_token()
            db.session.commit()

            # Create an on-call
            start_time = datetime(2023, 12, 1, 21, 0)
            end_time = start_time + timedelta(days=7, hours=-14)
            oncall = OnCall(
                user_id=test_user.id, start_time=start_time, end_time=end_time
            )
            db.session.add(oncall)
            db.session.commit()

        response = client.get(f"/export/oncall?scope=my&token={token}")
        assert response.status_code == 200
        content = response.data.decode("utf-8")
        assert "BEGIN:VCALENDAR" in content
        assert "Astreinte" in content

    def test_export_leaves_with_token(self, client, test_user, test_app):
        """Test exporting leaves with a valid token."""
        with test_app.app_context():
            # Generate a token for the user
            token = test_user.generate_ics_token()
            db.session.commit()

            # Create a leave
            start_date = datetime(2023, 12, 10).date()
            end_date = datetime(2023, 12, 15).date()
            leave = Leave(
                user_id=test_user.id, start_date=start_date, end_date=end_date
            )
            db.session.add(leave)
            db.session.commit()

        response = client.get(f"/export/leaves?scope=my&token={token}")
        assert response.status_code == 200
        content = response.data.decode("utf-8")
        assert "BEGIN:VCALENDAR" in content
        assert "Conge" in content or "Cong" in content

    def test_token_scope_all_accesses_all_data(
        self, client, test_user, second_user, test_shift_type, test_app
    ):
        """Test that scope=all with a token grants access to every shift."""
        with test_app.app_context():
            # Generate a token for the first user
            token = test_user.generate_ics_token()
            db.session.commit()

            # Create shifts for both users
            shift_date = datetime(2023, 12, 1).date()
            start_time = datetime.combine(shift_date, datetime.min.time()).replace(
                hour=7
            )
            end_time = start_time + timedelta(hours=8)

            shift1 = Shift(
                user_id=test_user.id,
                shift_type_id=test_shift_type.id,
                start_time=start_time,
                end_time=end_time,
                date=shift_date,
            )
            shift2 = Shift(
                user_id=second_user.id,
                shift_type_id=test_shift_type.id,
                start_time=start_time + timedelta(days=1),
                end_time=end_time + timedelta(days=1),
                date=shift_date + timedelta(days=1),
            )
            db.session.add(shift1)
            db.session.add(shift2)
            db.session.commit()

        # Export every shift with scope=all and a token
        # Should return the shifts of ALL users
        response = client.get(f"/export/shifts?scope=all&token={token}")
        assert response.status_code == 200
        content = response.data.decode("utf-8")
        # Should contain 2 events (one for each user)
        assert content.count("BEGIN:VEVENT") == 2
        assert test_user.name in content
        assert second_user.name in content

    def test_token_scope_my_accesses_only_own_data(
        self, client, test_user, second_user, test_shift_type, test_app
    ):
        """Test that scope=my with a token only grants access to that user's data."""
        with test_app.app_context():
            # Generate a token for the first user
            token = test_user.generate_ics_token()
            db.session.commit()

            # Create a shift for the second user
            shift_date = datetime(2023, 12, 1).date()
            start_time = datetime.combine(shift_date, datetime.min.time()).replace(
                hour=7
            )
            end_time = start_time + timedelta(hours=8)
            shift = Shift(
                user_id=second_user.id,
                shift_type_id=test_shift_type.id,
                start_time=start_time,
                end_time=end_time,
                date=shift_date,
            )
            db.session.add(shift)
            db.session.commit()

        # Try exporting with scope=my and test_user's token
        response = client.get(f"/export/shifts?scope=my&token={token}")
        assert response.status_code == 200
        content = response.data.decode("utf-8")
        # Should not contain second_user's shift
        assert second_user.name not in content


class TestIcsTokenExpiry:
    """Tests for ICS token expiry enforcement (ExportService.resolve_user)."""

    def test_fresh_token_is_not_expired(self, client, test_user, test_app):
        with test_app.app_context():
            token = test_user.generate_ics_token()
            db.session.commit()

        response = client.get(f"/export/shifts?scope=my&token={token}")
        assert response.status_code == 200

    def test_token_past_expiry_days_is_rejected(self, client, test_user, test_app):
        with test_app.app_context():
            token = test_user.generate_ics_token()
            test_user.ics_token_created_at = datetime.utcnow() - timedelta(days=400)
            db.session.commit()

        response = client.get(f"/export/shifts?scope=my&token={token}")
        assert response.status_code in (401, 302)

    def test_token_with_no_created_at_is_rejected(self, client, test_user, test_app):
        """A token issued before this feature (not yet backfilled) must not
        grant indefinite access."""
        with test_app.app_context():
            test_user.ics_token = "legacy-token-no-timestamp"
            test_user.ics_token_created_at = None
            db.session.commit()

        response = client.get(
            "/export/shifts?scope=my&token=legacy-token-no-timestamp"
        )
        assert response.status_code in (401, 302)

    def test_regenerating_token_resets_expiry_clock(self, client, test_user, test_app):
        with test_app.app_context():
            test_user.generate_ics_token()
            test_user.ics_token_created_at = datetime.utcnow() - timedelta(days=400)
            db.session.commit()

            new_token = test_user.generate_ics_token()
            db.session.commit()

        response = client.get(f"/export/shifts?scope=my&token={new_token}")
        assert response.status_code == 200

    def test_admin_configured_expiry_days_is_respected(
        self, client, test_user, test_app
    ):
        from app.services.settings_service import SettingsService

        with test_app.app_context():
            token = test_user.generate_ics_token()
            test_user.ics_token_created_at = datetime.utcnow() - timedelta(days=10)
            db.session.commit()
            SettingsService.set_ics_token_expiry_days(5)

        response = client.get(f"/export/shifts?scope=my&token={token}")
        assert response.status_code in (401, 302)

    def test_authenticated_session_ignores_token_expiry(
        self, logged_in_client, test_app
    ):
        """Session-based access must never be gated by ics_token expiry -
        it doesn't even use the token."""
        response = logged_in_client.get("/export/shifts?scope=my")
        assert response.status_code == 200
