"""
Tests for the automation routes in admin.py.
"""

from datetime import date, timedelta

from app import db
from app.models import AppNotification, Group


class TestAutomationDashboard:
    """Tests for /admin/automation."""

    def test_automation_dashboard_get(self, logged_in_client):
        """Test rendering the automation dashboard."""
        response = logged_in_client.get("/admin/automation")
        assert response.status_code == 200
        assert b"Automatisation" in response.data or b"Automation" in response.data

    def test_automation_dashboard_unauthenticated(self, client):
        """Test that the automation dashboard requires authentication."""
        response = client.get("/admin/automation", follow_redirects=True)
        assert b"Connexion" in response.data


class TestAutomationFull:
    """Tests for /admin/automation/full."""

    def test_automation_full_get(self, logged_in_client):
        """Test rendering the full-automation page."""
        response = logged_in_client.get("/admin/automation/full")
        assert response.status_code == 200
        assert (
            b"astreintes" in response.data.lower()
            or b"oncall" in response.data.lower()
            or b"Automatisation" in response.data
        )

    def test_automation_full_post_save_order(self, logged_in_client, test_user):
        """Test saving the rotation order."""
        response = logged_in_client.post(
            "/admin/automation/full",
            data={
                "action": "save_order",
                f"rotation_order_{test_user.id}": "1",
                f"include_{test_user.id}": "1",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"ordre" in response.data.lower() or b"Order" in response.data

    def test_automation_full_form_has_single_action_field(self, logged_in_client):
        """Regression test: the form used to also have a static hidden
        field `name="action" value="generate"` alongside the "Generer"
        button - with two `action` fields submitted, Werkzeug only keeps
        the first one (request.form.get always returned "generate",
        never "save_order" or "dry_run" no matter which button was
        clicked). This checks that there is only one `action` field per
        button, carried directly by the button itself
        (name="action" value="...") rather than by a separate
        always-present hidden input."""
        response = logged_in_client.get("/admin/automation/full")
        assert response.status_code == 200
        html = response.data.decode()

        assert 'name="action" value="generate"' in html
        assert 'name="action" value="dry_run"' in html
        # The only place "generate" should appear as an action field
        # value is the button itself (not a separate hidden input that
        # would coexist with the dry_run/save_order buttons).
        assert '<input type="hidden" name="action" value="generate">' not in html

    def test_automation_full_post_dry_run(self, logged_in_client, test_user):
        """Test the dry run of the full automation."""
        today = date.today()
        # Find next Friday
        start_date = today
        while start_date.weekday() != 4:  # Friday
            start_date += timedelta(days=1)
        end_date = start_date + timedelta(days=7)

        response = logged_in_client.post(
            "/admin/automation/full",
            data={
                "action": "dry_run",
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
                f"rotation_order_{test_user.id}": "1",
                f"include_{test_user.id}": "1",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        # Regression test: the dry run used to render a nonexistent
        # template (oncall_dry_run.html), silently replaced by a generic
        # error flash. Checks that the real preview page (on-calls +
        # shifts) is actually rendered.
        assert b"Pr\xc3\xa9visualisation" in response.data
        assert b"Astreintes" in response.data
        assert b"Shifts" in response.data
        # The confirm button must carry the submitted rotation order
        # (a related bug: it used to get lost at confirmation time).
        assert f'name="rotation_order_{test_user.id}"'.encode() in response.data

    def test_automation_full_post_invalid_date(self, logged_in_client, test_user):
        """Test the full automation with invalid dates."""
        response = logged_in_client.post(
            "/admin/automation/full",
            data={
                "action": "generate",
                "start_date": "invalid-date",
                "end_date": "invalid-date",
                f"rotation_order_{test_user.id}": "1",
                f"include_{test_user.id}": "1",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert (
            b"invalide" in response.data
            or b"invalid" in response.data
            or b"Erreur" in response.data
        )

    def test_automation_full_post_generate_notifies_admins_on_gap(
        self, logged_in_client, test_user, second_user
    ):
        """Regression test: with only 2 rotating users, the legal 2-week
        on-call spacing constraint makes some weeks impossible to fill -
        generate_oncall_schedule() deliberately leaves them unassigned
        rather than violating the constraint, and every admin (here,
        logged_in_client's own "Login User") must get an in-app
        notification about the gap."""
        # logged_in_client's own admin ("Login User") is in an
        # oncall-eligible group too - excluded here so exactly
        # test_user/second_user rotate (a 3rd rotating user could sustain
        # the 2-week spacing indefinitely, masking the gap this test is
        # about).
        with logged_in_client.application.app_context():
            login_group = Group.query.filter_by(name="Test Group Login").first()
            login_group.is_part_of_oncall = False
            db.session.commit()

        today = date.today()
        start_date = today
        while start_date.weekday() != 4:  # Friday
            start_date += timedelta(days=1)
        end_date = start_date + timedelta(days=35)

        response = logged_in_client.post(
            "/admin/automation/full",
            data={
                "action": "generate",
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
                f"rotation_order_{test_user.id}": "1",
                f"include_{test_user.id}": "1",
                f"rotation_order_{second_user.id}": "2",
                f"include_{second_user.id}": "1",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200

        gap_notifs = AppNotification.query.filter_by(
            notification_type="oncall_generation_gap"
        ).all()
        assert len(gap_notifs) >= 1
        assert gap_notifs[0].link == "/admin/automation"


class TestAutomationStatus:
    """Tests for /admin/automation/status."""

    def test_automation_status_get(self, logged_in_client):
        """Test rendering the automation status."""
        response = logged_in_client.get("/admin/automation/status")
        assert response.status_code == 200
        # Just check that the page loads successfully
        assert b"<!DOCTYPE" in response.data or b"<html" in response.data

    def test_automation_status_unauthenticated(self, client):
        """Test that the status page requires authentication."""
        response = client.get("/admin/automation/status", follow_redirects=True)
        assert b"Connexion" in response.data


class TestRefreshShifts:
    """Tests for /admin/automation/refresh-shifts."""

    def test_refresh_shifts_get(self, logged_in_client):
        """Test rendering the shift-refresh page."""
        response = logged_in_client.get("/admin/automation/refresh-shifts")
        assert response.status_code == 200
        assert (
            b"rafra" in response.data.lower()
            or b"refresh" in response.data.lower()
            or b"shifts" in response.data.lower()
        )

    def test_refresh_shifts_post(self, logged_in_client):
        """Test refreshing shifts."""
        today = date.today()
        end_date = today + timedelta(days=7)

        response = logged_in_client.post(
            "/admin/automation/refresh-shifts",
            data={
                "start_date": today.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
            },
            follow_redirects=True,
        )
        assert response.status_code == 200

    def test_refresh_shifts_post_invalid_date(self, logged_in_client):
        """Test refreshing shifts with invalid dates."""
        response = logged_in_client.post(
            "/admin/automation/refresh-shifts",
            data={
                "start_date": "invalid-date",
                "end_date": "invalid-date",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert (
            b"invalide" in response.data
            or b"invalid" in response.data
            or b"Erreur" in response.data
        )

    def test_refresh_shifts_unauthenticated(self, client):
        """Test that the refresh page requires authentication."""
        response = client.get("/admin/automation/refresh-shifts", follow_redirects=True)
        assert b"Connexion" in response.data
