"""
Tests pour les routes d'automatisation dans admin.py.
"""

from datetime import date, timedelta


class TestAutomationDashboard:
    """Tests pour /admin/automation."""

    def test_automation_dashboard_get(self, logged_in_client):
        """Test l'affichage du tableau de bord d'automatisation."""
        response = logged_in_client.get("/admin/automation")
        assert response.status_code == 200
        assert b"Automatisation" in response.data or b"Automation" in response.data

    def test_automation_dashboard_unauthenticated(self, client):
        """Test que le dashboard d'automatisation nécessite une authentification."""
        response = client.get("/admin/automation", follow_redirects=True)
        assert b"Connexion" in response.data


class TestAutomationShifts:
    """Tests pour /admin/automation/shifts."""

    def test_automation_shifts_get(self, logged_in_client):
        """Test l'affichage de la page de configuration des shifts automatiques."""
        response = logged_in_client.get("/admin/automation/shifts")
        assert response.status_code == 200
        assert (
            b"shifts" in response.data.lower()
            or b"automatisation" in response.data.lower()
        )

    def test_automation_shifts_post_generate(
        self, logged_in_client, test_user, test_group
    ):
        """Test la génération de shifts automatiques."""
        today = date.today()
        end_date = today + timedelta(days=7)

        response = logged_in_client.post(
            "/admin/automation/shifts",
            data={
                "action": "generate",
                "start_date": today.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
                "monday_morning": "1",
                "tuesday_morning": "1",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200

    def test_automation_shifts_post_dry_run(self, logged_in_client):
        """Test le dry run de la génération de shifts."""
        today = date.today()
        end_date = today + timedelta(days=7)

        response = logged_in_client.post(
            "/admin/automation/shifts",
            data={
                "action": "dry_run",
                "start_date": today.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
                "monday_morning": "1",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200

    def test_automation_shifts_post_invalid_date(self, logged_in_client):
        """Test la génération avec des dates invalides."""
        response = logged_in_client.post(
            "/admin/automation/shifts",
            data={
                "action": "generate",
                "start_date": "invalid-date",
                "end_date": "invalid-date",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        # Should show error message
        assert (
            b"invalide" in response.data
            or b"invalid" in response.data
            or b"Erreur" in response.data
        )


class TestAutomationFull:
    """Tests pour /admin/automation/full."""

    def test_automation_full_get(self, logged_in_client):
        """Test l'affichage de la page d'automatisation complète."""
        response = logged_in_client.get("/admin/automation/full")
        assert response.status_code == 200
        assert (
            b"astreintes" in response.data.lower()
            or b"oncall" in response.data.lower()
            or b"Automatisation" in response.data
        )

    def test_automation_full_post_save_order(self, logged_in_client, test_user):
        """Test la sauvegarde de l'ordre de rotation."""
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

    def test_automation_full_post_dry_run(self, logged_in_client, test_user):
        """Test le dry run de l'automatisation complète."""
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

    def test_automation_full_post_invalid_date(self, logged_in_client, test_user):
        """Test l'automatisation complète avec des dates invalides."""
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


class TestAutomationStatus:
    """Tests pour /admin/automation/status."""

    def test_automation_status_get(self, logged_in_client):
        """Test l'affichage de l'état de l'automatisation."""
        response = logged_in_client.get("/admin/automation/status")
        assert response.status_code == 200
        # Just check that the page loads successfully
        assert b"<!DOCTYPE" in response.data or b"<html" in response.data

    def test_automation_status_unauthenticated(self, client):
        """Test que la page de statut nécessite une authentification."""
        response = client.get("/admin/automation/status", follow_redirects=True)
        assert b"Connexion" in response.data


class TestRefreshShifts:
    """Tests pour /admin/automation/refresh-shifts."""

    def test_refresh_shifts_get(self, logged_in_client):
        """Test l'affichage de la page de rafraîchissement des shifts."""
        response = logged_in_client.get("/admin/automation/refresh-shifts")
        assert response.status_code == 200
        assert (
            b"rafra" in response.data.lower()
            or b"refresh" in response.data.lower()
            or b"shifts" in response.data.lower()
        )

    def test_refresh_shifts_post(self, logged_in_client):
        """Test le rafraîchissement des shifts."""
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
        """Test le rafraîchissement avec des dates invalides."""
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
        """Test que la page de rafraîchissement nécessite une authentification."""
        response = client.get("/admin/automation/refresh-shifts", follow_redirects=True)
        assert b"Connexion" in response.data
