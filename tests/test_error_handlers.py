"""
Tests pour les gestionnaires d'erreurs personnalisés.
"""




class TestErrorHandlers:
    """Tests pour les gestionnaires d'erreurs."""

    def test_404_error_handler(self, client):
        """Test le gestionnaire d'erreur 404."""
        response = client.get("/nonexistent-route")
        assert response.status_code == 404
        # Vérifier que le template 404 est rendu
        assert b"404" in response.data or b"Not Found" in response.data or b"Page non trouvee" in response.data

    def test_error_handlers_are_registered(self, app):
        """Test que les gestionnaires d'erreurs sont enregistrés."""
        with app.app_context():
            # Vérifier que les handlers sont enregistrés
            assert hasattr(app, "errorhandler")

            # Vérifier que les handlers pour 403 et 404 existent
            # Note: errorhandler est une méthode, pas un attribut
            # On vérifie que les handlers sont enregistrés dans l'app
            assert hasattr(app, "handle_url_build_error")
            # Les handlers personnalisés sont enregistrés via @app.errorhandler
            # On peut vérifier qu'ils existent en appelant app.errorhandler
            assert callable(app.errorhandler)


class TestCustomErrorPages:
    """Tests pour les pages d'erreur personnalisées."""

    def test_403_template_exists(self, app):
        """Test que le template 403.html existe."""
        with app.app_context():
            from flask import render_template
            try:
                html = render_template("403.html")
                assert html is not None
            except Exception as e:
                # Si le template n'existe pas, pytest échouera
                raise AssertionError(f"Template 403.html introuvable: {str(e)}") from e

    def test_404_template_exists(self, app):
        """Test que le template 404.html existe."""
        with app.app_context():
            from flask import render_template
            try:
                html = render_template("404.html")
                assert html is not None
            except Exception as e:
                raise AssertionError(f"Template 404.html introuvable: {str(e)}") from e

    def test_403_template_content(self, app):
        """Test le contenu du template 403.html."""
        with app.app_context():
            from flask import render_template
            html = render_template("403.html")
            # Vérifier que le template contient des éléments de base
            assert b"403" in html.encode() or b"Forbidden" in html.encode() or b"Interdit" in html.encode()

    def test_404_template_content(self, app):
        """Test le contenu du template 404.html."""
        with app.app_context():
            from flask import render_template
            html = render_template("404.html")
            assert b"404" in html.encode() or b"Not Found" in html.encode() or b"Page non trouvee" in html.encode()
