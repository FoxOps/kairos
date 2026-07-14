"""
Tests pour le thème sombre de Leviia Schedule.

Ces tests vérifient que :
1. Le CSS du thème sombre est correctement chargé
2. Le bouton de toggle est présent pour les utilisateurs authentifiés
3. Le JavaScript du thème sombre est présent
4. Les bonnes pratiques d'accessibilité sont respectées
5. Les variables CSS sont correctement mappées vers daisyUI
6. Les styles spécifiques pour FullCalendar sont présents

Depuis la refonte Tailwind/daisyUI (Phase 7 - retrait de Bulma) :
daisyUI gère lui-même la bascule clair/sombre de ses propres composants
via ses variables --color-* et [data-theme] - variables.css ne fait que
mapper ces variables vers des noms d'application stables (utilisés par
dashboard.css/rotation-order.css/fullcalendar-overrides.css),
`themes/dark.css` ne contient plus que les surcharges FullCalendar (lib
externe non-daisyUI-aware) et des réglages d'accessibilité génériques -
plus de correctifs de contraste Bulma (.button.is-warning, etc.),
devenus inutiles puisque daisyUI gère déjà son propre contraste. Le
mécanisme de bascule n'utilise plus que l'attribut data-theme (la classe
.dark-mode, redondante, a été retirée de theme-manager.js).
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

            # Variables CSS dans :root (variables.css) - primary/info/
            # success/warning préfixées "app-" (collision avec les
            # variables --color-* réservées de daisyUI sinon,
            # danger/error ne collisionnait pas donc reste tel quel).
            assert ":root" in variables
            assert "--app-color-primary" in variables
            assert "--app-color-info" in variables
            assert "--app-color-success" in variables
            assert "--app-color-warning" in variables
            assert "--color-danger" in variables

            # Mappage vers les variables daisyUI
            assert "var(--color-primary)" in variables
            assert "var(--color-info)" in variables
            assert "var(--color-success)" in variables
            assert "var(--color-warning)" in variables
            assert "var(--color-error)" in variables

            # Variables de fond et texte
            assert "--bg-primary" in variables
            assert "--text-primary" in variables
            assert "var(--color-base-100)" in variables
            assert "var(--color-base-content)" in variables

            # Sélecteur pour le thème sombre
            assert '[data-theme="dark"]' in dark

    def test_daisyui_variable_mapping(self, test_app):
        """Test que les variables Leviia sont correctement mappées vers daisyUI."""
        with test_app.app_context():
            content = read_css("variables.css")

            assert "--app-color-primary: var(--color-primary);" in content
            assert "--app-color-info: var(--color-info);" in content
            assert "--app-color-success: var(--color-success);" in content
            assert "--app-color-warning: var(--color-warning);" in content
            assert "--color-danger: var(--color-error);" in content

            assert "--bg-primary: var(--color-base-100);" in content
            assert "--text-primary: var(--color-base-content);" in content

    def test_utility_classes_present(self, test_app):
        """Test que les classes utilitaires min-w-* sont présentes (les
        classes d'espacement/affichage mt-*/mb-*/gap-*/d-* ont été
        retirées en Phase 7 - Tailwind (JIT) génère déjà des classes du
        même nom, garder une définition maison en doublon, non-layer,
        gagnait toujours sur les utilitaires Tailwind avec des valeurs
        parfois différentes - bug réel découvert et corrigé)."""
        with test_app.app_context():
            content = read_css("utilities.css")

            assert ".min-w-140" in content
            assert ".min-w-150" in content
            assert ".min-w-180" in content
            assert ".min-w-200" in content

    def test_fullcalendar_styles_present(self, test_app):
        """Test que les styles spécifiques pour FullCalendar sont présents."""
        with test_app.app_context():
            overrides = read_css("vendor", "fullcalendar-overrides.css")
            dark = read_css("themes", "dark.css")

            assert ".fc-event-shift" in overrides
            assert ".fc-event-oncall" in overrides
            assert ".fc-event-leave" in overrides

            assert '[data-theme="dark"] .fc' in dark
            assert "background-color: var(--bg-primary)" in dark

    def test_focus_visible_styles_present(self, test_app):
        """Test que les styles pour focus-visible sont présents (thème sombre)."""
        with test_app.app_context():
            content = read_css("themes", "dark.css")

            assert "focus-visible" in content
            assert "outline: 2px solid var(--app-color-primary)" in content
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

    def test_theme_toggle_button_present_for_anonymous(self, client):
        """Test que le bouton de toggle est présent pour les utilisateurs non authentifiés (page login)."""
        response = client.get("/login")
        assert response.status_code == 200
        html_content = response.data.decode("utf-8")

        assert 'id="theme-toggle"' in html_content

    def test_theme_javascript_present(self, logged_in_client):
        """Test que le JavaScript du thème sombre est présent."""
        response = logged_in_client.get("/")
        assert response.status_code == 200
        html_content = response.data.decode("utf-8")

        assert "js/main.js" in html_content
        assert 'type="module"' in html_content

        assert "function applyTheme" not in html_content

    def test_skip_link_present(self, client):
        """Test que le skip link pour l'accessibilité est présent. Depuis la
        refonte Tailwind/daisyUI, plus de classe .skip-link dédiée - le
        comportement (masqué sauf au focus) est porté par les utilitaires
        Tailwind sr-only/focus:not-sr-only, on vérifie donc le lien lui-même
        plutôt qu'un nom de classe."""
        response = client.get("/login")
        assert response.status_code == 200
        html_content = response.data.decode("utf-8")

        assert 'href="#main-content"' in html_content
        assert "Sauter la navigation" in html_content


class TestDarkThemeAccessibility:
    """Tests pour l'accessibilité du thème sombre."""

    def test_theme_toggle_has_aria_attributes(self, logged_in_client):
        """Test que le toggle de thème a les attributs d'accessibilité
        nécessaires. Depuis le passage au pattern "Theme Controller" de
        daisyUI (case à cocher réelle, voir base.html/theme-manager.js),
        plus d'aria-pressed (sémantique bouton, pas pertinente pour une
        checkbox - le "checked" natif suffit)."""
        response = logged_in_client.get("/")
        assert response.status_code == 200
        html_content = response.data.decode("utf-8")

        assert 'aria-label="Basculer entre le thème clair et sombre"' in html_content
        assert 'type="checkbox" id="theme-toggle"' in html_content

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

    def test_daisyui_variables_used(self, test_app):
        """Test que les variables daisyUI sont utilisées dans variables.css."""
        with test_app.app_context():
            content = read_css("variables.css")

            daisyui_variables = [
                "var(--color-primary)",
                "var(--color-info)",
                "var(--color-success)",
                "var(--color-warning)",
                "var(--color-error)",
                "var(--color-base-100)",
                "var(--color-base-content)",
            ]

            for var in daisyui_variables:
                assert (
                    var in content
                ), f"Variable daisyUI {var} non trouvée dans variables.css"

    def test_dark_theme_uses_data_attribute(self, test_app):
        """Test que le thème sombre utilise l'attribut data-theme."""
        with test_app.app_context():
            content = read_css("themes", "dark.css")

            assert '[data-theme="dark"]' in content


class TestDarkThemeWCAGCompliance:
    """Tests pour la conformité WCAG du thème sombre."""

    def test_focus_styles_present(self, test_app):
        """Test que les styles de focus pour l'accessibilité sont présents."""
        with test_app.app_context():
            content = read_css("themes", "dark.css")

            assert "focus-visible" in content
            assert "outline: 2px solid" in content

            assert "a:focus-visible" in content
            assert "button:focus-visible" in content
            assert "input:focus-visible" in content
