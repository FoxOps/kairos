"""
Tests pour vérifier les corrections des bugs et duplications du thème visuel.

Ces tests vérifient que :
1. Les styles dupliqués ont été supprimés
2. Le JavaScript a été centralisé
3. Les variables CSS manquantes ont été ajoutées
4. Les styles inline ont été remplacés par des classes CSS
"""

import pytest


class TestNoDuplicateStyles:
    """Tests pour vérifier l'absence de styles dupliqués."""

    def test_skip_link_not_duplicated(self, test_app):
        """Test que skip-link n'est défini qu'une seule fois (dans base-styles.css)."""
        import os
        from flask import current_app
        
        with test_app.app_context():
            # Vérifier que skip-link est dans base-styles.css
            base_styles_path = os.path.join(
                current_app.static_folder, 
                'css', 
                'base-styles.css'
            )
            assert os.path.exists(base_styles_path), f"Le fichier {base_styles_path} n'existe pas"
            
            with open(base_styles_path, 'r') as f:
                base_styles_content = f.read()
            
            assert '.skip-link' in base_styles_content, "skip-link doit être dans base-styles.css"
            
            # Vérifier que skip-link n'est PAS dans base.html
            base_template_path = os.path.join(
                current_app.template_folder, 
                'base.html'
            )
            with open(base_template_path, 'r') as f:
                base_template_content = f.read()
            
            # Le style inline ne doit plus être présent
            assert '<style>' not in base_template_content or '.skip-link' not in base_template_content, \
                "Les styles skip-link ne doivent plus être inline dans base.html"

    def test_fullcalendar_styles_not_duplicated(self, test_app):
        """Test que les styles FullCalendar ne sont pas dupliqués."""
        import os
        from flask import current_app
        
        with test_app.app_context():
            # Vérifier que fullcalendar-styles.css existe
            fc_styles_path = os.path.join(
                current_app.static_folder, 
                'css', 
                'fullcalendar-styles.css'
            )
            assert os.path.exists(fc_styles_path), f"Le fichier {fc_styles_path} n'existe pas"
            
            with open(fc_styles_path, 'r') as f:
                fc_styles_content = f.read()
            
            # Vérifier la présence des styles FullCalendar
            assert '.fc-event-shift' in fc_styles_content
            assert '.fc-event-oncall' in fc_styles_content
            assert '.fc-event-leave' in fc_styles_content
            
            # Vérifier que ces styles ne sont PAS dans index.html
            index_template_path = os.path.join(
                current_app.template_folder, 
                'index.html'
            )
            with open(index_template_path, 'r') as f:
                index_template_content = f.read()
            
            # Les styles inline ne doivent plus être présents
            assert '<style>' not in index_template_content or '.fc-event-shift' not in index_template_content, \
                "Les styles FullCalendar ne doivent plus être inline dans index.html"


class TestCentralizedJavaScript:
    """Tests pour vérifier que le JavaScript a été centralisé."""

    def test_script_js_exists(self, test_app):
        """Test que script.js existe et contient le ThemeManager."""
        import os
        from flask import current_app
        
        with test_app.app_context():
            script_path = os.path.join(
                current_app.static_folder, 
                'js', 
                'script.js'
            )
            assert os.path.exists(script_path), f"Le fichier {script_path} n'existe pas"
            
            with open(script_path, 'r') as f:
                script_content = f.read()
            
            # Vérifier la présence de la classe ThemeManager
            assert 'class ThemeManager' in script_content
            assert 'applyTheme' in script_content
            assert 'getSystemTheme' in script_content
            assert 'getCurrentTheme' in script_content

    def test_no_inline_js_in_base(self, test_app):
        """Test qu'il n'y a plus de JavaScript inline dans base.html."""
        import os
        from flask import current_app
        
        with test_app.app_context():
            base_template_path = os.path.join(
                current_app.template_folder, 
                'base.html'
            )
            with open(base_template_path, 'r') as f:
                base_template_content = f.read()
            
            # Vérifier que les anciennes fonctions ne sont plus présentes
            assert 'function applyTheme' not in base_template_content
            assert 'function updateToggleButton' not in base_template_content
            assert 'function getSystemTheme' not in base_template_content
            assert 'function getCurrentTheme' not in base_template_content
            
            # Vérifier que script.js est inclus
            assert 'script.js' in base_template_content


class TestCSSVariables:
    """Tests pour vérifier que les variables CSS manquantes ont été ajoutées."""

    def test_bulma_grey_variables_added(self, test_app):
        """Test que les variables --bulma-grey* ont été ajoutées."""
        import os
        from flask import current_app
        
        with test_app.app_context():
            dark_theme_path = os.path.join(
                current_app.static_folder, 
                'css', 
                'dark-theme.css'
            )
            with open(dark_theme_path, 'r') as f:
                dark_theme_content = f.read()
            
            # Vérifier la présence des variables manquantes
            assert '--bulma-grey:' in dark_theme_content
            assert '--bulma-grey-light:' in dark_theme_content
            assert '--bulma-grey-dark:' in dark_theme_content

    def test_base_styles_has_utility_classes(self, test_app):
        """Test que base-styles.css contient les classes utilitaires."""
        import os
        from flask import current_app
        
        with test_app.app_context():
            base_styles_path = os.path.join(
                current_app.static_folder, 
                'css', 
                'base-styles.css'
            )
            with open(base_styles_path, 'r') as f:
                base_styles_content = f.read()
            
            # Vérifier la présence des classes utilitaires
            assert '.min-w-140' in base_styles_content
            assert '.min-w-180' in base_styles_content
            assert '.min-w-200' in base_styles_content
            assert '.gap-2' in base_styles_content
            assert '.d-none' in base_styles_content
            assert '.type-tag' in base_styles_content


class TestInlineStylesReplacement:
    """Tests pour vérifier que les styles inline ont été remplacés."""

    def test_no_inline_styles_in_base(self, test_app):
        """Test qu'il n'y a plus de styles inline dans base.html."""
        import os
        from flask import current_app
        
        with test_app.app_context():
            base_template_path = os.path.join(
                current_app.template_folder, 
                'base.html'
            )
            with open(base_template_path, 'r') as f:
                base_template_content = f.read()
            
            # Vérifier qu'il n'y a pas de balise <style> avec du contenu
            # (on autorise la balise vide pour les blocks extra_css)
            import re
            style_tags = re.findall(r'<style[^>]*>(.*?)</style>', base_template_content, re.DOTALL)
            for style_content in style_tags:
                # Vérifier que le style n'est pas vide (contient du contenu)
                if style_content.strip():
                    # Si c'est un block Jinja2, c'est OK
                    if '{% block' not in style_content and '{% endblock' not in style_content:
                        assert False, f"Style inline trouvé dans base.html: {style_content[:100]}"

    def test_dashboard_uses_type_tag_classes(self, test_app):
        """Test que dashboard.html utilise les classes type-tag au lieu des styles inline."""
        import os
        from flask import current_app
        
        with test_app.app_context():
            dashboard_template_path = os.path.join(
                current_app.template_folder, 
                'dashboard.html'
            )
            with open(dashboard_template_path, 'r') as f:
                dashboard_content = f.read()
            
            # Vérifier que les classes type-tag sont utilisées
            assert 'class="type-tag is-primary"' in dashboard_content
            assert 'class="type-tag is-light"' in dashboard_content
            
            # Vérifier qu'il n'y a plus de var(--bulma-grey)
            assert 'var(--bulma-grey)' not in dashboard_content

    def test_index_uses_min_w_classes(self, test_app):
        """Test que index.html utilise les classes min-w-* au lieu des styles inline."""
        import os
        from flask import current_app
        
        with test_app.app_context():
            index_template_path = os.path.join(
                current_app.template_folder, 
                'index.html'
            )
            with open(index_template_path, 'r') as f:
                index_content = f.read()
            
            # Vérifier que les classes min-w-* sont utilisées
            assert 'class="tag is-danger min-w-180"' in index_content
            assert 'class="button is-small is-success min-w-180"' in index_content
            
            # Vérifier qu'il n'y a plus de style="min-width: 180px"
            assert 'style="min-width: 180px"' not in index_content


class TestFileStructure:
    """Tests pour vérifier la structure des fichiers."""

    def test_required_files_exist(self, test_app):
        """Test que tous les fichiers requis existent."""
        import os
        from flask import current_app
        
        with test_app.app_context():
            static_folder = current_app.static_folder
            template_folder = current_app.template_folder
            
            # Vérifier les fichiers CSS
            required_css = [
                'css/dark-theme.css',
                'css/base-styles.css',
                'css/fullcalendar-styles.css'
            ]
            for css_file in required_css:
                css_path = os.path.join(static_folder, css_file)
                assert os.path.exists(css_path), f"Le fichier {css_path} n'existe pas"
            
            # Vérifier les fichiers JS
            required_js = [
                'js/script.js'
            ]
            for js_file in required_js:
                js_path = os.path.join(static_folder, js_file)
                assert os.path.exists(js_path), f"Le fichier {js_path} n'existe pas"
            
            # Vérifier les templates
            required_templates = [
                'base.html',
                'index.html',
                'dashboard.html'
            ]
            for template_file in required_templates:
                template_path = os.path.join(template_folder, template_file)
                assert os.path.exists(template_path), f"Le template {template_path} n'existe pas"

    def test_css_files_included_in_templates(self, logged_in_client):
        """Test que les fichiers CSS sont correctement inclus dans les templates."""
        response = logged_in_client.get('/')
        assert response.status_code == 200
        html_content = response.data.decode('utf-8')
        
        # Vérifier que tous les fichiers CSS sont inclus
        assert 'dark-theme.css' in html_content
        assert 'base-styles.css' in html_content
        
        # Vérifier que fullcalendar-styles.css est inclus dans index
        response = logged_in_client.get('/')
        html_content = response.data.decode('utf-8')
        assert 'fullcalendar-styles.css' in html_content

    def test_js_file_included_in_base_template(self, logged_in_client):
        """Test que script.js est inclus dans le template de base."""
        response = logged_in_client.get('/')
        assert response.status_code == 200
        html_content = response.data.decode('utf-8')
        
        assert 'script.js' in html_content
