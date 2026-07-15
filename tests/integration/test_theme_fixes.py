"""
Tests checking the fixes for bugs and duplication in the visual theme.

These tests check that:
1. Duplicated styles have been removed
2. The JavaScript has been centralized
3. The missing CSS variables have been added
4. Inline styles have been replaced with CSS classes

The old `base-styles.css`, `dark-theme.css` and `fullcalendar-styles.css`
files have been removed and replaced by a tree of files (`variables.css`,
`base.css`, `utilities.css`, `components/*.css`, `layout/*.css`,
`themes/dark.css`, `vendor/fullcalendar-overrides.css`).
"""

import os

from flask import current_app


def read_css(*parts: str) -> str:
    assert current_app.static_folder is not None
    css_path = os.path.join(current_app.static_folder, "css", *parts)
    with open(css_path) as f:
        return f.read()


class TestNoDuplicateStyles:
    """Tests checking there are no duplicated styles."""

    def test_skip_link_not_duplicated(self, test_app):
        """Test that the skip link is only styled in one place. Under
        Tailwind/daisyUI, there's no home-grown .skip-link class in
        base.css anymore - the style (hidden except on focus) is carried
        directly by the Tailwind sr-only/focus:not-sr-only utilities on
        the link itself in base.html, so there's nothing to duplicate."""
        with test_app.app_context():
            base_css_content = read_css("base.css")
            assert ".skip-link {" not in base_css_content

            base_template_path = os.path.join(current_app.template_folder, "base.html")
            with open(base_template_path) as f:
                base_template_content = f.read()

            assert "<style>" not in base_template_content
            assert "sr-only" in base_template_content

    def test_fullcalendar_styles_not_duplicated(self, test_app):
        """Test that the FullCalendar styles aren't duplicated."""
        with test_app.app_context():
            fc_styles_content = read_css("vendor", "fullcalendar-overrides.css")

            assert ".fc-event-shift" in fc_styles_content
            assert ".fc-event-oncall" in fc_styles_content
            assert ".fc-event-leave" in fc_styles_content

            index_template_path = os.path.join(
                current_app.template_folder, "index.html"
            )
            with open(index_template_path) as f:
                index_template_content = f.read()

            assert (
                "<style>" not in index_template_content
                or ".fc-event-shift" not in index_template_content
            ), "The FullCalendar styles must no longer be inline in index.html"


class TestCentralizedJavaScript:
    """Tests checking that the JavaScript has been centralized."""

    def test_script_js_exists(self, test_app):
        """Test that main.js exists and loads the ThemeManager."""
        with test_app.app_context():
            main_path = os.path.join(current_app.static_folder, "js", "main.js")
            assert os.path.exists(main_path), f"File {main_path} does not exist"

            with open(main_path) as f:
                main_content = f.read()

            assert "ThemeManager" in main_content

            theme_manager_path = os.path.join(
                current_app.static_folder, "js", "theme", "theme-manager.js"
            )
            assert os.path.exists(
                theme_manager_path
            ), f"File {theme_manager_path} does not exist"

            with open(theme_manager_path) as f:
                theme_manager_content = f.read()

            assert "class ThemeManager" in theme_manager_content
            assert "applyTheme" in theme_manager_content
            assert "getSystemTheme" in theme_manager_content
            assert "getCurrentTheme" in theme_manager_content

    def test_no_inline_js_in_base(self, test_app):
        """Test that there's no more inline JavaScript in base.html."""
        with test_app.app_context():
            base_template_path = os.path.join(current_app.template_folder, "base.html")
            with open(base_template_path) as f:
                base_template_content = f.read()

            assert "function applyTheme" not in base_template_content
            assert "function updateToggleButton" not in base_template_content
            assert "function getSystemTheme" not in base_template_content
            assert "function getCurrentTheme" not in base_template_content

            assert "js/main.js" in base_template_content
            assert 'type="module"' in base_template_content


class TestCSSVariables:
    """Tests checking that the missing CSS variables have been added."""

    def test_base_styles_has_utility_classes(self, test_app):
        """Test that utilities.css contains the min-w-* utility classes.
        Under Tailwind/daisyUI, the home-grown spacing/display classes
        (gap-*, d-none, ...) and .type-tag (buttons.css) have been
        removed: Tailwind (JIT) already generates classes with the same
        names as gap-*/d-*, and daisyUI provides .badge in place of
        .type-tag - keeping the home-grown definitions on top was
        redundant and, for gap-*/mt-*/mb-*, silently wrong (different
        values than Tailwind's, which always take priority since they're
        outside any @layer)."""
        with test_app.app_context():
            utilities_content = read_css("utilities.css")

            assert ".min-w-140" in utilities_content
            assert ".min-w-180" in utilities_content
            assert ".min-w-200" in utilities_content
            assert ".gap-2 {" not in utilities_content
            assert ".d-none {" not in utilities_content

            buttons_content = read_css("components", "buttons.css")
            assert ".type-tag {" not in buttons_content


class TestInlineStylesReplacement:
    """Tests checking that inline styles have been replaced."""

    def test_no_inline_styles_in_base(self, test_app):
        """Test that there's no more inline style in base.html."""
        with test_app.app_context():
            base_template_path = os.path.join(current_app.template_folder, "base.html")
            with open(base_template_path) as f:
                base_template_content = f.read()

            import re

            style_tags = re.findall(
                r"<style[^>]*>(.*?)</style>", base_template_content, re.DOTALL
            )
            for style_content in style_tags:
                if style_content.strip():
                    if (
                        "{% block" not in style_content
                        and "{% endblock" not in style_content
                    ):
                        assert (
                            False
                        ), f"Inline style found in base.html: {style_content[:100]}"

    def test_dashboard_uses_type_tag_classes(self, test_app):
        """Test that dashboard.html uses daisyUI badge classes (rather
        than inline styles) - the former home-grown type-tag
        is-primary/is-light classes were replaced by daisyUI badges
        under Tailwind/daisyUI.

        Shift-type badges now use a dynamic per-type color
        (shift_type_colors, see common_helpers.build_shift_type_color_map,
        computed by rank on the route side then passed to the template)
        instead of a fixed class - this checks the pattern (a
        dynamically generated daisyUI badge) rather than one exact
        literal class."""
        with test_app.app_context():
            dashboard_template_path = os.path.join(
                current_app.template_folder, "dashboard.html"
            )
            with open(dashboard_template_path) as f:
                dashboard_content = f.read()

            assert 'class="badge badge-{{ shift_type_colors.get(' in dashboard_content

            assert "var(--bulma-grey)" not in dashboard_content

    def test_index_uses_min_w_classes(self, test_app):
        """Test that index.html uses the min-w-* classes instead of inline styles."""
        with test_app.app_context():
            index_template_path = os.path.join(
                current_app.template_folder, "index.html"
            )
            with open(index_template_path) as f:
                index_content = f.read()

            assert 'class="badge badge-error min-w-180"' in index_content
            assert 'class="btn btn-success btn-sm min-w-180"' in index_content

            assert 'style="min-width: 180px"' not in index_content


class TestFileStructure:
    """Tests checking the file structure."""

    def test_required_files_exist(self, test_app):
        """Test that every required file exists."""
        with test_app.app_context():
            static_folder = current_app.static_folder
            template_folder = current_app.template_folder

            required_css = [
                "css/variables.css",
                "css/base.css",
                "css/utilities.css",
                "css/themes/dark.css",
                "css/vendor/fullcalendar-overrides.css",
            ]
            for css_file in required_css:
                css_path = os.path.join(static_folder, css_file)
                assert os.path.exists(css_path), f"File {css_path} does not exist"

            required_js = [
                "js/main.js",
                "js/theme/theme-manager.js",
                "js/utils/dom.js",
                "js/utils/date.js",
                "js/utils/accessibility.js",
                "js/notifications/toast.js",
            ]
            for js_file in required_js:
                js_path = os.path.join(static_folder, js_file)
                assert os.path.exists(js_path), f"File {js_path} does not exist"

            required_templates = ["base.html", "index.html", "dashboard.html"]
            for template_file in required_templates:
                template_path = os.path.join(template_folder, template_file)
                assert os.path.exists(
                    template_path
                ), f"Template {template_path} does not exist"

    def test_css_files_included_in_templates(self, logged_in_client):
        """Test that the CSS files are correctly included in the templates."""
        response = logged_in_client.get("/")
        assert response.status_code == 200
        html_content = response.data.decode("utf-8")

        assert "themes/dark.css" in html_content
        assert "css/base.css" in html_content

        response = logged_in_client.get("/")
        html_content = response.data.decode("utf-8")
        assert "vendor/fullcalendar-overrides.css" in html_content

    def test_js_file_included_in_base_template(self, logged_in_client):
        """Test that main.js is included in the base template as a module."""
        response = logged_in_client.get("/")
        assert response.status_code == 200
        html_content = response.data.decode("utf-8")

        assert "js/main.js" in html_content
        assert 'type="module"' in html_content
