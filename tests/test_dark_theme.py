"""
Tests pour le thème sombre de Leviia Schedule.

Ces tests vérifient que :
1. Le CSS du thème sombre est correctement chargé
2. Le bouton de toggle est présent pour les utilisateurs authentifiés
3. Le JavaScript du thème sombre est présent
4. Les bonnes pratiques d'accessibilité sont respectées
"""

import pytest


class TestDarkThemeCSS:
    """Tests pour le fichier CSS du thème sombre."""

    def test_dark_theme_css_exists(self, app):
        """Test que le fichier CSS du thème sombre existe."""
        import os
        from flask import current_app
        
        with app.app_context():
            css_path = os.path.join(
                current_app.static_folder, 
                'css', 
                'dark-theme.css'
            )
            assert os.path.exists(css_path), f"Le fichier {css_path} n'existe pas"

    def test_dark_theme_css_content(self, app):
        """Test que le fichier CSS contient les sélecteurs nécessaires."""
        import os
        from flask import current_app
        
        with app.app_context():
            css_path = os.path.join(
                current_app.static_folder, 
                'css', 
                'dark-theme.css'
            )
            
            with open(css_path, 'r') as f:
                content = f.read()
            
            # Vérifier la présence des variables CSS
            assert ':root' in content
            assert '--bg-primary' in content
            assert '--text-primary' in content
            assert '--color-primary' in content
            
            # Vérifier la présence des sélecteurs pour le thème sombre
            assert '[data-theme="dark"]' in content
            assert '.dark-mode' in content
            
            # Vérifier la présence des styles pour les éléments principaux
            assert '.navbar' in content
            assert '.button' in content
            assert '.box' in content
            assert '.notification' in content
            assert '.table' in content
            assert '.fc' in content  # FullCalendar
            
            # Vérifier le support de prefers-color-scheme
            assert 'prefers-color-scheme: dark' in content


class TestDarkThemeTemplate:
    """Tests pour l'intégration du thème sombre dans les templates."""

    def test_dark_theme_css_included_in_base_template(self, client):
        """Test que le CSS du thème sombre est inclus dans le template base."""
        response = client.get('/login')
        assert response.status_code == 200
        assert 'dark-theme.css' in response.data.decode('utf-8')

    def test_theme_toggle_button_present_for_authenticated_user(self, logged_in_client):
        """Test que le bouton de toggle est présent pour les utilisateurs authentifiés."""
        response = logged_in_client.get('/')
        assert response.status_code == 200
        html_content = response.data.decode('utf-8')
        
        # Vérifier la présence du bouton
        assert 'theme-toggle' in html_content
        assert 'aria-label="Basculer entre le thème clair et sombre"' in html_content

    def test_theme_toggle_button_not_present_for_anonymous(self, client):
        """Test que le bouton de toggle n'est PAS présent pour les utilisateurs non authentifiés."""
        response = client.get('/login')
        assert response.status_code == 200
        html_content = response.data.decode('utf-8')
        
        # Le bouton ne doit pas être présent sur la page de login
        # On vérifie que l'élément button avec id="theme-toggle" n'est pas présent
        assert '<button id="theme-toggle"' not in html_content

    def test_theme_javascript_present(self, logged_in_client):
        """Test que le JavaScript du thème sombre est présent."""
        response = logged_in_client.get('/')
        assert response.status_code == 200
        html_content = response.data.decode('utf-8')
        
        # Vérifier la présence des fonctions JavaScript
        assert 'applyTheme' in html_content
        assert 'getSystemTheme' in html_content
        assert 'getCurrentTheme' in html_content
        assert 'localStorage.setItem' in html_content

    def test_skip_link_present(self, client):
        """Test que le skip link pour l'accessibilité est présent."""
        response = client.get('/login')
        assert response.status_code == 200
        html_content = response.data.decode('utf-8')
        
        assert 'skip-link' in html_content
        assert 'Sauter la navigation' in html_content


class TestDarkThemeAccessibility:
    """Tests pour l'accessibilité du thème sombre."""

    def test_theme_toggle_has_aria_attributes(self, logged_in_client):
        """Test que le bouton toggle a les attributs ARIA nécessaires."""
        response = logged_in_client.get('/')
        assert response.status_code == 200
        html_content = response.data.decode('utf-8')
        
        assert 'aria-label="Basculer entre le thème clair et sombre"' in html_content
        assert 'aria-pressed' in html_content

    def test_main_content_has_id(self, client):
        """Test que le contenu principal a un ID pour le skip link."""
        response = client.get('/login')
        assert response.status_code == 200
        html_content = response.data.decode('utf-8')
        
        assert 'id="main-content"' in html_content

    def test_navbar_has_role(self, client):
        """Test que la navbar a un rôle ARIA."""
        response = client.get('/login')
        assert response.status_code == 200
        html_content = response.data.decode('utf-8')
        
        assert 'role="navigation"' in html_content


class TestDarkThemeVariables:
    """Tests pour les variables CSS du thème sombre."""

    def test_color_variables_defined(self, app):
        """Test que les variables de couleur sont définies."""
        import os
        from flask import current_app
        
        with app.app_context():
            css_path = os.path.join(
                current_app.static_folder, 
                'css', 
                'dark-theme.css'
            )
            
            with open(css_path, 'r') as f:
                content = f.read()
            
            # Vérifier les variables de couleur pour le thème clair
            assert '--color-primary: #00d1b2;' in content
            assert '--color-info: #3273dc;' in content
            assert '--color-success: #23d160;' in content
            assert '--color-warning: #ffdd57;' in content
            assert '--color-danger: #f14668;' in content
            
            # Vérifier les variables de fond et texte pour le thème clair
            assert '--bg-primary: #ffffff;' in content
            assert '--text-primary: #363636;' in content

    def test_dark_theme_variables_override(self, app):
        """Test que les variables du thème sombre écrasent celles du thème clair."""
        import os
        from flask import current_app
        
        with app.app_context():
            css_path = os.path.join(
                current_app.static_folder, 
                'css', 
                'dark-theme.css'
            )
            
            with open(css_path, 'r') as f:
                content = f.read()
            
            # Vérifier que le thème sombre a des variables différentes
            dark_section = content[content.find('[data-theme="dark"]'):]
            
            assert '--bg-primary: #1a1a1a;' in dark_section
            assert '--text-primary: #e0e0e0;' in dark_section


class TestDarkThemeWCAGCompliance:
    """Tests pour la conformité WCAG du thème sombre."""

    def test_contrast_ratios_in_css(self, app):
        """Test que les couleurs ont des ratios de contraste suffisants."""
        import os
        from flask import current_app
        
        with app.app_context():
            css_path = os.path.join(
                current_app.static_folder, 
                'css', 
                'dark-theme.css'
            )
            
            with open(css_path, 'r') as f:
                content = f.read()
            
            # Vérifier que les boutons warning ont du texte noir pour le contraste
            # (le jaune #ffdd57 a besoin de texte noir pour un ratio de 7.5:1)
            assert 'color: #000 !important;' in content
            
            # Vérifier que les notifications warning ont du texte noir
            assert 'color: #000 !important; /* Noir pour contraste suffisant' in content

    def test_focus_styles_present(self, app):
        """Test que les styles de focus pour l'accessibilité sont présents."""
        import os
        from flask import current_app
        
        with app.app_context():
            css_path = os.path.join(
                current_app.static_folder, 
                'css', 
                'dark-theme.css'
            )
            
            with open(css_path, 'r') as f:
                content = f.read()
            
            # Vérifier les styles de focus visible
            assert 'focus-visible' in content
            assert 'outline: 2px solid' in content
