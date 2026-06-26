"""
Tests pour le thème sombre de Leviia Schedule.

Ces tests vérifient que :
1. Le CSS du thème sombre est correctement chargé
2. Le bouton de toggle est présent pour les utilisateurs authentifiés
3. Le JavaScript du thème sombre est présent
4. Les bonnes pratiques d'accessibilité sont respectées
5. Les variables CSS sont correctement mappées vers Bulma
6. Les styles spécifiques pour FullCalendar sont présents
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
        """Test que le fichier CSS contient les sélecteurs et variables nécessaires."""
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
            
            # Vérifier la présence des variables CSS dans :root
            assert ':root' in content
            assert '--color-primary' in content
            assert '--color-info' in content
            assert '--color-success' in content
            assert '--color-warning' in content
            assert '--color-danger' in content
            
            # Vérifier le mappage vers les variables Bulma
            assert 'var(--bulma-primary)' in content
            assert 'var(--bulma-info)' in content
            assert 'var(--bulma-success)' in content
            assert 'var(--bulma-warning)' in content
            assert 'var(--bulma-danger)' in content
            
            # Vérifier la présence des variables de fond et texte
            assert '--bg-primary' in content
            assert '--text-primary' in content
            assert 'var(--bulma-background)' in content
            assert 'var(--bulma-text)' in content
            
            # Vérifier la présence des sélecteurs pour le thème sombre
            assert '[data-theme="dark"]' in content
            assert '.dark-mode' in content
            
            # Vérifier le support de prefers-color-scheme
            assert 'prefers-color-scheme: dark' in content

    def test_bulma_variable_mapping(self, app):
        """Test que les variables Leviia sont correctement mappées vers Bulma."""
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
            
            # Vérifier le mappage des couleurs primaires
            assert '--color-primary: var(--bulma-primary);' in content
            assert '--color-info: var(--bulma-info);' in content
            assert '--color-success: var(--bulma-success);' in content
            assert '--color-warning: var(--bulma-warning);' in content
            assert '--color-danger: var(--bulma-danger);' in content
            
            # Vérifier le mappage des couleurs secondaires
            assert '--color-primary-light: var(--bulma-primary-light);' in content
            assert '--color-info-light: var(--bulma-info-light);' in content
            assert '--color-success-light: var(--bulma-success-light);' in content
            assert '--color-warning-light: var(--bulma-warning-light);' in content
            assert '--color-danger-light: var(--bulma-danger-light);' in content
            
            # Vérifier le mappage des fond et texte
            assert '--bg-primary: var(--bulma-background);' in content
            assert '--text-primary: var(--bulma-text);' in content

    def test_utility_classes_present(self, app):
        """Test que les classes utilitaires sont présentes."""
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
            
            # Vérifier les classes de gap
            assert '.gap-0' in content
            assert '.gap-1' in content
            assert '.gap-2' in content
            
            # Vérifier les classes de min-width
            assert '.min-w-140' in content
            assert '.min-w-150' in content

    def test_fullcalendar_styles_present(self, app):
        """Test que les styles spécifiques pour FullCalendar sont présents."""
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
            
            # Vérifier les styles pour les événements FullCalendar
            assert '.fc-event-shift' in content
            assert '.fc-event-oncall' in content
            assert '.fc-event-leave' in content
            assert '.fc' in content
            
            # Vérifier les styles de fond et texte pour FullCalendar
            assert '[data-theme="dark"] .fc' in content
            assert 'background-color: var(--bulma-background)' in content

    def test_contrast_fixes_present(self, app):
        """Test que les corrections de contraste pour les boutons warning sont présentes."""
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
            
            # Vérifier les corrections de contraste pour les boutons warning
            assert '[data-theme="dark"] .button.is-warning' in content
            assert 'color: #000 !important;' in content
            
            # Vérifier les corrections pour les tags warning
            assert '[data-theme="dark"] .tag.is-warning' in content

    def test_skip_link_styles_present(self, app):
        """Test que les styles pour le skip link sont présents."""
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
            
            # Vérifier les styles pour le skip link
            assert '.skip-link' in content
            assert 'position: absolute' in content
            assert 'top: -40px' in content

    def test_required_field_indicator_present(self, app):
        """Test que l'indicateur de champ obligatoire est présent."""
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
            
            # Vérifier l'indicateur de champ obligatoire
            assert '.label.required::after' in content
            assert 'content: " *"' in content
            assert 'color: var(--color-danger)' in content

    def test_sr_only_class_present(self, app):
        """Test que la classe .is-sr-only pour l'accessibilité est présente."""
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
            
            # Vérifier la classe .is-sr-only
            assert '.is-sr-only' in content
            assert 'position: absolute' in content
            assert 'width: 1px' in content
            assert 'height: 1px' in content

    def test_focus_visible_styles_present(self, app):
        """Test que les styles pour focus-visible sont présents."""
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
            
            # Vérifier les styles focus-visible
            assert 'focus-visible' in content
            assert 'outline: 2px solid var(--color-primary)' in content
            assert 'outline-offset: 2px' in content


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
        
        # Vérifier que le fichier script.js est inclus (centralisation du JS)
        assert 'script.js' in html_content
        assert 'src="{{ url_for(\'static\', filename=\'js/script.js\') }}"' in html_content or '/static/js/script.js' in html_content
        
        # Vérifier que les anciennes fonctions inline ne sont plus présentes
        # (car elles sont maintenant dans script.js)
        assert 'function applyTheme' not in html_content

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

    def test_bulma_variables_used(self, app):
        """Test que les variables Bulma sont utilisées dans le CSS."""
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
            
            # Vérifier que les variables Bulma sont utilisées
            bulma_variables = [
                'var(--bulma-primary)',
                'var(--bulma-info)',
                'var(--bulma-success)',
                'var(--bulma-warning)',
                'var(--bulma-danger)',
                'var(--bulma-background)',
                'var(--bulma-text)',
                'var(--bulma-border)',
            ]
            
            for var in bulma_variables:
                assert var in content, f"Variable Bulma {var} non trouvée dans le CSS"

    def test_dark_theme_uses_data_attribute(self, app):
        """Test que le thème sombre utilise l'attribut data-theme."""
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
            
            # Vérifier que [data-theme="dark"] est utilisé
            assert '[data-theme="dark"]' in content
            
            # Vérifier que .dark-mode est aussi utilisé pour la compatibilité
            assert '.dark-mode' in content


class TestDarkThemeWCAGCompliance:
    """Tests pour la conformité WCAG du thème sombre."""

    def test_contrast_fixes_for_warning_elements(self, app):
        """Test que les corrections de contraste pour les éléments warning sont présentes."""
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
            
            # Vérifier que les corrections s'appliquent aux boutons et tags warning
            dark_section = content[content.find('[data-theme="dark"]'):]
            assert '.button.is-warning' in dark_section
            assert '.tag.is-warning' in dark_section

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
            
            # Vérifier que les styles s'appliquent à différents éléments
            assert 'a:focus-visible' in content
            assert 'button:focus-visible' in content
            assert 'input:focus-visible' in content
