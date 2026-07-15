"""
Tests for the "Actions rapides" (quick actions) on the home page
(index.html) for a non-admin user: ICS export (my + all + the "Plus
d'options" link) - a regression test for a redesign that had made these
links disappear from the panel.
"""

from app import db


class TestQuickActionsExportNonAdmin:
    def test_no_token_shows_generate_link(self, test_app, non_admin_client):
        resp = non_admin_client.get("/")
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        assert "Générer mon export ICS" in body
        assert "/profile/ics-token" in body

    def test_with_token_shows_export_links(self, test_app, non_admin_client, test_user):
        with test_app.app_context():
            test_user.generate_ics_token()
            db.session.commit()

        resp = non_admin_client.get("/")
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)

        assert "Exporter mes shifts" in body
        assert "Exporter le calendrier complet" in body
        assert "scope=all" in body
        assert "Exporter mes astreintes" in body
        assert "Exporter mes congés" in body
        assert "Plus d'options" in body
        assert "/profile/ics-token" in body

    def test_no_double_slash_in_export_links(
        self, test_app, non_admin_client, test_user
    ):
        with test_app.app_context():
            test_user.generate_ics_token()
            db.session.commit()

        resp = non_admin_client.get("/")
        body = resp.get_data(as_text=True)
        assert "//export/" not in body


class TestQuickActionsAdmin:
    def test_admin_index_still_renders(self, test_app, logged_in_client):
        """No regression on the admin side (admin panel unchanged)."""
        resp = logged_in_client.get("/")
        assert resp.status_code == 200
        assert b"Ajouter un shift" in resp.data
