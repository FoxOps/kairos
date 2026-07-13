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

    def test_automation_full_form_has_single_action_field(self, logged_in_client):
        """Régression : le formulaire avait un champ caché
        `name="action" value="generate"` statique EN PLUS du bouton
        "Générer" - deux champs `action` soumis, dont Werkzeug ne retient
        que le premier (request.form.get renvoie toujours "generate",
        jamais "save_order" ni "dry_run" quel que soit le bouton cliqué).
        Vérifie qu'il ne reste qu'un seul champ `action` par bouton, porté
        directement par le bouton (name="action" value="...") et non par
        un input caché séparé toujours présent."""
        response = logged_in_client.get("/admin/automation/full")
        assert response.status_code == 200
        html = response.data.decode()

        assert 'name="action" value="generate"' in html
        assert 'name="action" value="dry_run"' in html
        # Le seul endroit où "generate" doit apparaître comme valeur de
        # champ action est le bouton lui-même (pas un input hidden séparé
        # qui coexisterait avec les boutons dry_run/save_order).
        assert '<input type="hidden" name="action" value="generate">' not in html

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
        # Régression bug 1 : le dry-run rendait auparavant un template
        # inexistant (oncall_dry_run.html), silencieusement remplacé par
        # un flash d'erreur générique. Vérifie que la vraie page de
        # prévisualisation (astreintes + shifts) s'affiche.
        assert b"Pr\xc3\xa9visualisation" in response.data
        assert b"Astreintes" in response.data
        assert b"Shifts" in response.data
        # Le bouton de confirmation doit porter l'ordre de rotation soumis
        # (bug annexe : il était perdu au moment de confirmer).
        assert f'name="rotation_order_{test_user.id}"'.encode() in response.data

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
