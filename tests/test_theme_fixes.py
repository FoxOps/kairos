"""
Tests pour vérifier les corrections des bugs et duplications du thème visuel.

Ces tests vérifient que :
1. Les styles dupliqués ont été supprimés
2. Le JavaScript a été centralisé
3. Les variables CSS manquantes ont été ajoutées
4. Les styles inline ont été remplacés par des classes CSS

Depuis la Phase 3 (restructuration frontend), les anciens fichiers
`base-styles.css`, `dark-theme.css` et `fullcalendar-styles.css` ont été
supprimés et remplacés par une arborescence (`variables.css`, `base.css`,
`utilities.css`, `components/*.css`, `layout/*.css`, `themes/dark.css`,
`vendor/fullcalendar-overrides.css`).
"""

import os

import pytest
from flask import current_app


def read_css(*parts: str) -> str:
    css_path = os.path.join(current_app.static_folder, 'css', *parts)
    with open(css_path, 'r') as f:
        return f.read()


class TestNoDuplicateStyles:
    """Tests pour vérifier l'absence de styles dupliqués."""

    def test_skip_link_not_duplicated(self, test_app):
        """Test que skip-link n'est défini qu'une seule fois (dans base.css)."""
        with test_app.app_context():
            base_css_content = read_css('base.css')
            assert '.skip-link' in base_css_content, "skip-link doit être dans base.css"

            base_template_path = os.path.join(current_app.template_folder, 'base.html')
            with open(base_template_path, 'r') as f:
                base_template_content = f.read()

            assert '<style>' not in base_template_content or '.skip-link' not in base_template_content, \
                "Les styles skip-link ne doivent plus être inline dans base.html"

    def test_fullcalendar_styles_not_duplicated(self, test_app):
        """Test que les styles FullCalendar ne sont pas dupliqués."""
        with test_app.app_context():
            fc_styles_content = read_css('vendor', 'fullcalendar-overrides.css')

            assert '.fc-event-shift' in fc_styles_content
            assert '.fc-event-oncall' in fc_styles_content
            assert '.fc-event-leave' in fc_styles_content

            index_template_path = os.path.join(current_app.template_folder, 'index.html')
            with open(index_template_path, 'r') as f:
                index_template_content = f.read()

            assert '<style>' not in index_template_content or '.fc-event-shift' not in index_template_content, \
                "Les styles FullCalendar ne doivent plus être inline dans index.html"


class TestCentralizedJavaScript:
    """Tests pour vérifier que le JavaScript a été centralisé."""

    def test_script_js_exists(self, test_app):
        """Test que script.js existe et contient le ThemeManager."""
        with test_app.app_context():
            script_path = os.path.join(current_app.static_folder, 'js', 'script.js')
            assert os.path.exists(script_path), f"Le fichier {script_path} n'existe pas"

            with open(script_path, 'r') as f:
                script_content = f.read()

            assert 'class ThemeManager' in script_content
            assert 'applyTheme' in script_content
            assert 'getSystemTheme' in script_content
            assert 'getCurrentTheme' in script_content

    def test_no_inline_js_in_base(self, test_app):
        """Test qu'il n'y a plus de JavaScript inline dans base.html."""
        with test_app.app_context():
            base_template_path = os.path.join(current_app.template_folder, 'base.html')
            with open(base_template_path, 'r') as f:
                base_template_content = f.read()

            assert 'function applyTheme' not in base_template_content
            assert 'function updateToggleButton' not in base_template_content
            assert 'function getSystemTheme' not in base_template_content
            assert 'function getCurrentTheme' not in base_template_content

            assert 'script.js' in base_template_content


class TestCSSVariables:
    """Tests pour vérifier que les variables CSS manquantes ont été ajoutées."""

    def test_bulma_grey_variables_added(self, test_app):
        """Test que les variables --bulma-grey* ont été ajoutées."""
        with test_app.app_context():
            content = read_css('variables.css')

            assert '--bulma-grey:' in content
            assert '--bulma-grey-light:' in content
            assert '--bulma-grey-dark:' in content

    def test_base_styles_has_utility_classes(self, test_app):
        """Test que utilities.css contient les classes utilitaires."""
        with test_app.app_context():
            utilities_content = read_css('utilities.css')

            assert '.min-w-140' in utilities_content
            assert '.min-w-180' in utilities_content
            assert '.min-w-200' in utilities_content
            assert '.gap-2' in utilities_content
            assert '.d-none' in utilities_content

            buttons_content = read_css('components', 'buttons.css')
            assert '.type-tag' in buttons_content


class TestInlineStylesReplacement:
    """Tests pour vérifier que les styles inline ont été remplacés."""

    def test_no_inline_styles_in_base(self, test_app):
        """Test qu'il n'y a plus de styles inline dans base.html."""
        with test_app.app_context():
            base_template_path = os.path.join(current_app.template_folder, 'base.html')
            with open(base_template_path, 'r') as f:
                base_template_content = f.read()

            import re
            style_tags = re.findall(r'<style[^>]*>(.*?)</style>', base_template_content, re.DOTALL)
            for style_content in style_tags:
                if style_content.strip():
                    if '{% block' not in style_content and '{% endblock' not in style_content:
                        assert False, f"Style inline trouvé dans base.html: {style_content[:100]}"

    def test_dashboard_uses_type_tag_classes(self, test_app):
        """Test que dashboard.html utilise les classes type-tag au lieu des styles inline."""
        with test_app.app_context():
            dashboard_template_path = os.path.join(current_app.template_folder, 'dashboard.html')
            with open(dashboard_template_path, 'r') as f:
                dashboard_content = f.read()

            assert 'class="type-tag is-primary"' in dashboard_content
            assert 'class="type-tag is-light"' in dashboard_content

            assert 'var(--bulma-grey)' not in dashboard_content

    def test_index_uses_min_w_classes(self, test_app):
        """Test que index.html utilise les classes min-w-* au lieu des styles inline."""
        with test_app.app_context():
            index_template_path = os.path.join(current_app.template_folder, 'index.html')
            with open(index_template_path, 'r') as f:
                index_content = f.read()

            assert 'class="tag is-danger min-w-180"' in index_content
            assert 'class="button is-small is-success min-w-180"' in index_content

            assert 'style="min-width: 180px"' not in index_content


class TestFileStructure:
    """Tests pour vérifier la structure des fichiers."""

    def test_required_files_exist(self, test_app):
        """Test que tous les fichiers requis existent."""
        with test_app.app_context():
            static_folder = current_app.static_folder
            template_folder = current_app.template_folder

            required_css = [
                'css/variables.css',
                'css/base.css',
                'css/utilities.css',
                'css/themes/dark.css',
                'css/vendor/fullcalendar-overrides.css',
            ]
            for css_file in required_css:
                css_path = os.path.join(static_folder, css_file)
                assert os.path.exists(css_path), f"Le fichier {css_path} n'existe pas"

            required_js = ['js/script.js']
            for js_file in required_js:
                js_path = os.path.join(static_folder, js_file)
                assert os.path.exists(js_path), f"Le fichier {js_path} n'existe pas"

            required_templates = ['base.html', 'index.html', 'dashboard.html']
            for template_file in required_templates:
                template_path = os.path.join(template_folder, template_file)
                assert os.path.exists(template_path), f"Le template {template_path} n'existe pas"

    def test_css_files_included_in_templates(self, logged_in_client):
        """Test que les fichiers CSS sont correctement inclus dans les templates."""
        response = logged_in_client.get('/')
        assert response.status_code == 200
        html_content = response.data.decode('utf-8')

        assert 'themes/dark.css' in html_content
        assert 'css/base.css' in html_content

        response = logged_in_client.get('/')
        html_content = response.data.decode('utf-8')
        assert 'vendor/fullcalendar-overrides.css' in html_content

    def test_js_file_included_in_base_template(self, logged_in_client):
        """Test que script.js est inclus dans le template de base."""
        response = logged_in_client.get('/')
        assert response.status_code == 200
        html_content = response.data.decode('utf-8')

        assert 'script.js' in html_content
