"""
Tests pour le thème sombre de Leviia Schedule.

Ces tests vérifient que :
1. Le CSS du thème sombre est correctement chargé
2. Le bouton de toggle est présent pour les utilisateurs authentifiés
3. Le JavaScript du thème sombre est présent
4. Les bonnes pratiques d'accessibilité sont respectées
5. Les variables CSS sont correctement mappées vers Bulma
6. Les styles spécifiques pour FullCalendar sont présents

Depuis la Phase 3 (restructuration frontend), ce qui vivait dans un seul
fichier `dark-theme.css` est réparti entre `variables.css` (variables de
couleur), `base.css` (skip-link, focus-visible générique, .is-sr-only),
`components/forms.css` (indicateur de champ requis),
`vendor/fullcalendar-overrides.css` (styles FullCalendar par défaut) et
`themes/dark.css` (règles [data-theme="dark"]/.dark-mode uniquement).
"""

import os

from flask import current_app


def read_css(*parts: str) -> str:
    """Lit le contenu d'un fichier CSS sous app/static/css/."""
    assert current_app.static_folder is not None
    css_path = os.path.join(current_app.static_folder, "css", *parts)
    with open(css_path) as f:
        return f.read()


class TestDarkThemeCSS:
    """Tests pour les fichiers CSS du thème sombre."""

    def test_dark_theme_css_exists(self, test_app):
        """Test que le fichier CSS du thème sombre existe."""
        with test_app.app_context():
            css_path = os.path.join(
                current_app.static_folder, "css", "themes", "dark.css"
            )
            assert os.path.exists(css_path), f"Le fichier {css_path} n'existe pas"

    def test_dark_theme_css_content(self, test_app):
        """Test que les variables et sélecteurs nécessaires sont présents."""
        with test_app.app_context():
            variables = read_css("variables.css")
            dark = read_css("themes", "dark.css")

            # Variables CSS dans :root (variables.css)
            assert ":root" in variables
            assert "--color-primary" in variables
            assert "--color-info" in variables
            assert "--color-success" in variables
            assert "--color-warning" in variables
            assert "--color-danger" in variables

            # Mappage vers les variables Bulma
            assert "var(--bulma-primary)" in variables
            assert "var(--bulma-info)" in variables
            assert "var(--bulma-success)" in variables
            assert "var(--bulma-warning)" in variables
            assert "var(--bulma-danger)" in variables

            # Variables de fond et texte
            assert "--bg-primary" in variables
            assert "--text-primary" in variables
            assert "var(--bulma-background)" in variables
            assert "var(--bulma-text)" in variables

            # Sélecteurs pour le thème sombre
            assert '[data-theme="dark"]' in dark
            assert ".dark-mode" in dark

    def test_bulma_variable_mapping(self, test_app):
        """Test que les variables Leviia sont correctement mappées vers Bulma."""
        with test_app.app_context():
            content = read_css("variables.css")

            assert "--color-primary: var(--bulma-primary);" in content
            assert "--color-info: var(--bulma-info);" in content
            assert "--color-success: var(--bulma-success);" in content
            assert "--color-warning: var(--bulma-warning);" in content
            assert "--color-danger: var(--bulma-danger);" in content

            assert "--color-primary-light: var(--bulma-primary-light);" in content
            assert "--color-info-light: var(--bulma-info-light);" in content
            assert "--color-success-light: var(--bulma-success-light);" in content
            assert "--color-warning-light: var(--bulma-warning-light);" in content
            assert "--color-danger-light: var(--bulma-danger-light);" in content

            assert "--bg-primary: var(--bulma-background);" in content
            assert "--text-primary: var(--bulma-text);" in content

    def test_utility_classes_present(self, test_app):
        """Test que les classes utilitaires sont présentes."""
        with test_app.app_context():
            content = read_css("utilities.css")

            assert ".gap-0" in content
            assert ".gap-1" in content
            assert ".gap-2" in content

            assert ".min-w-140" in content
            assert ".min-w-150" in content

    def test_fullcalendar_styles_present(self, test_app):
        """Test que les styles spécifiques pour FullCalendar sont présents."""
        with test_app.app_context():
            overrides = read_css("vendor", "fullcalendar-overrides.css")
            dark = read_css("themes", "dark.css")

            assert ".fc-event-shift" in overrides
            assert ".fc-event-oncall" in overrides
            assert ".fc-event-leave" in overrides

            assert '[data-theme="dark"] .fc' in dark
            assert "background-color: var(--bulma-background)" in dark

    def test_contrast_fixes_present(self, test_app):
        """Test que les corrections de contraste pour les boutons warning sont présentes."""
        with test_app.app_context():
            content = read_css("themes", "dark.css")

            assert '[data-theme="dark"] .button.is-warning' in content
            assert "color: #000 !important;" in content
            assert '[data-theme="dark"] .tag.is-warning' in content

    def test_skip_link_styles_present(self, test_app):
        """Test que les styles pour le skip link sont présents."""
        with test_app.app_context():
            content = read_css("base.css")

            assert ".skip-link" in content
            assert "position: absolute" in content
            assert "top: -40px" in content

    def test_required_field_indicator_present(self, test_app):
        """Test que l'indicateur de champ obligatoire est présent."""
        with test_app.app_context():
            content = read_css("components", "forms.css")

            assert ".label.required::after" in content
            assert 'content: " *"' in content
            assert "color: var(--color-danger)" in content

    def test_sr_only_class_present(self, test_app):
        """Test que la classe .is-sr-only pour l'accessibilité est présente."""
        with test_app.app_context():
            content = read_css("base.css")

            assert ".is-sr-only" in content
            assert "position: absolute" in content
            assert "width: 1px" in content
            assert "height: 1px" in content

    def test_focus_visible_styles_present(self, test_app):
        """Test que les styles pour focus-visible sont présents (thème sombre)."""
        with test_app.app_context():
            content = read_css("themes", "dark.css")

            assert "focus-visible" in content
            assert "outline: 2px solid var(--color-primary)" in content
            assert "outline-offset: 2px" in content


class TestDarkThemeTemplate:
    """Tests pour l'intégration du thème sombre dans les templates."""

    def test_dark_theme_css_included_in_base_template(self, client):
        """Test que le CSS du thème sombre est inclus dans le template base."""
        response = client.get("/login")
        assert response.status_code == 200
        assert "themes/dark.css" in response.data.decode("utf-8")

    def test_theme_toggle_button_present_for_authenticated_user(self, logged_in_client):
        """Test que le bouton de toggle est présent pour les utilisateurs authentifiés."""
        response = logged_in_client.get("/")
        assert response.status_code == 200
        html_content = response.data.decode("utf-8")

        assert "theme-toggle" in html_content
        assert 'aria-label="Basculer entre le thème clair et sombre"' in html_content

    def test_theme_toggle_button_not_present_for_anonymous(self, client):
        """Test que le bouton de toggle n'est PAS présent pour les utilisateurs non authentifiés."""
        response = client.get("/login")
        assert response.status_code == 200
        html_content = response.data.decode("utf-8")

        assert '<button id="theme-toggle"' not in html_content

    def test_theme_javascript_present(self, logged_in_client):
        """Test que le JavaScript du thème sombre est présent."""
        response = logged_in_client.get("/")
        assert response.status_code == 200
        html_content = response.data.decode("utf-8")

        assert "js/main.js" in html_content
        assert 'type="module"' in html_content

        assert "function applyTheme" not in html_content

    def test_skip_link_present(self, client):
        """Test que le skip link pour l'accessibilité est présent."""
        response = client.get("/login")
        assert response.status_code == 200
        html_content = response.data.decode("utf-8")

        assert "skip-link" in html_content
        assert "Sauter la navigation" in html_content


class TestDarkThemeAccessibility:
    """Tests pour l'accessibilité du thème sombre."""

    def test_theme_toggle_has_aria_attributes(self, logged_in_client):
        """Test que le bouton toggle a les attributs ARIA nécessaires."""
        response = logged_in_client.get("/")
        assert response.status_code == 200
        html_content = response.data.decode("utf-8")

        assert 'aria-label="Basculer entre le thème clair et sombre"' in html_content
        assert "aria-pressed" in html_content

    def test_main_content_has_id(self, client):
        """Test que le contenu principal a un ID pour le skip link."""
        response = client.get("/login")
        assert response.status_code == 200
        html_content = response.data.decode("utf-8")

        assert 'id="main-content"' in html_content

    def test_navbar_has_role(self, client):
        """Test que la navbar a un rôle ARIA."""
        response = client.get("/login")
        assert response.status_code == 200
        html_content = response.data.decode("utf-8")

        assert 'role="navigation"' in html_content


class TestDarkThemeVariables:
    """Tests pour les variables CSS du thème sombre."""

    def test_bulma_variables_used(self, test_app):
        """Test que les variables Bulma sont utilisées dans variables.css."""
        with test_app.app_context():
            content = read_css("variables.css")

            bulma_variables = [
                "var(--bulma-primary)",
                "var(--bulma-info)",
                "var(--bulma-success)",
                "var(--bulma-warning)",
                "var(--bulma-danger)",
                "var(--bulma-background)",
                "var(--bulma-text)",
                "var(--bulma-border)",
            ]

            for var in bulma_variables:
                assert (
                    var in content
                ), f"Variable Bulma {var} non trouvée dans variables.css"

    def test_dark_theme_uses_data_attribute(self, test_app):
        """Test que le thème sombre utilise l'attribut data-theme."""
        with test_app.app_context():
            content = read_css("themes", "dark.css")

            assert '[data-theme="dark"]' in content
            assert ".dark-mode" in content


class TestDarkThemeWCAGCompliance:
    """Tests pour la conformité WCAG du thème sombre."""

    def test_contrast_fixes_for_warning_elements(self, test_app):
        """Test que les corrections de contraste pour les éléments warning sont présentes."""
        with test_app.app_context():
            content = read_css("themes", "dark.css")

            # Le jaune #ffdd57 a besoin de texte noir pour un ratio de 7.5:1
            assert "color: #000 !important;" in content

            dark_section = content[content.find('[data-theme="dark"]') :]
            assert ".button.is-warning" in dark_section
            assert ".tag.is-warning" in dark_section

    def test_focus_styles_present(self, test_app):
        """Test que les styles de focus pour l'accessibilité sont présents."""
        with test_app.app_context():
            content = read_css("themes", "dark.css")

            assert "focus-visible" in content
            assert "outline: 2px solid" in content

            assert "a:focus-visible" in content
            assert "button:focus-visible" in content
            assert "input:focus-visible" in content
