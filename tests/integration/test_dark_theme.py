"""
Tests for Leviia Schedule's dark theme.

These tests check that:
1. The dark theme's CSS loads correctly
2. The toggle button is present for authenticated users
3. The dark theme's JavaScript is present
4. Accessibility best practices are followed
5. The CSS variables are correctly mapped to daisyUI
6. The FullCalendar-specific styles are present

Under Tailwind/daisyUI (Bulma has been removed): daisyUI itself handles
the light/dark switch for its own components through its --color-*
variables and [data-theme] - variables.css only maps those variables to
stable app-level names (used by
dashboard.css/rotation-order.css/fullcalendar-overrides.css),
`themes/dark.css` now only holds the FullCalendar overrides (an
external, non-daisyUI-aware library) and generic accessibility
settings - no more Bulma contrast fixes (.button.is-warning, etc.),
which became unnecessary since daisyUI already manages its own
contrast. The switching mechanism now only uses the data-theme
attribute (the redundant .dark-mode class has been removed from
theme-manager.js).
"""

import os

from flask import current_app


def read_css(*parts: str) -> str:
    """Read the content of a CSS file under app/static/css/."""
    assert current_app.static_folder is not None
    css_path = os.path.join(current_app.static_folder, "css", *parts)
    with open(css_path) as f:
        return f.read()


class TestDarkThemeCSS:
    """Tests for the dark theme's CSS files."""

    def test_dark_theme_css_exists(self, test_app):
        """Test that the dark theme's CSS file exists."""
        with test_app.app_context():
            css_path = os.path.join(
                current_app.static_folder, "css", "themes", "dark.css"
            )
            assert os.path.exists(css_path), f"File {css_path} does not exist"

    def test_dark_theme_css_content(self, test_app):
        """Test that the required variables and selectors are present."""
        with test_app.app_context():
            variables = read_css("variables.css")
            dark = read_css("themes", "dark.css")

            # CSS variables in :root (variables.css) - primary/info/
            # success/warning are prefixed "app-" (otherwise they'd
            # collide with daisyUI's reserved --color-* variables;
            # danger/error didn't collide so it stays as-is).
            assert ":root" in variables
            assert "--app-color-primary" in variables
            assert "--app-color-info" in variables
            assert "--app-color-success" in variables
            assert "--app-color-warning" in variables
            assert "--color-danger" in variables

            # Mapping to daisyUI's variables
            assert "var(--color-primary)" in variables
            assert "var(--color-info)" in variables
            assert "var(--color-success)" in variables
            assert "var(--color-warning)" in variables
            assert "var(--color-error)" in variables

            # Background and text variables
            assert "--bg-primary" in variables
            assert "--text-primary" in variables
            assert "var(--color-base-100)" in variables
            assert "var(--color-base-content)" in variables

            # Dark theme selector
            assert '[data-theme="dark"]' in dark

    def test_daisyui_variable_mapping(self, test_app):
        """Test that Leviia's variables are correctly mapped to daisyUI."""
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
        """Test that the min-w-* utility classes are present (the
        mt-*/mb-*/gap-*/d-* spacing/display classes have been removed -
        Tailwind (JIT) already generates classes with the same names,
        and keeping a duplicate, non-layer, home-grown definition always
        won against Tailwind's utilities, sometimes with different
        values - a real bug that was found and fixed)."""
        with test_app.app_context():
            content = read_css("utilities.css")

            assert ".min-w-140" in content
            assert ".min-w-150" in content
            assert ".min-w-180" in content
            assert ".min-w-200" in content

    def test_fullcalendar_styles_present(self, test_app):
        """Test that the FullCalendar-specific styles are present."""
        with test_app.app_context():
            overrides = read_css("vendor", "fullcalendar-overrides.css")
            dark = read_css("themes", "dark.css")

            assert ".fc-event-shift" in overrides
            assert ".fc-event-oncall" in overrides
            assert ".fc-event-leave" in overrides

            assert '[data-theme="dark"] .fc' in dark
            assert "background-color: var(--bg-primary)" in dark

    def test_focus_visible_styles_present(self, test_app):
        """Test that the focus-visible styles are present (dark theme)."""
        with test_app.app_context():
            content = read_css("themes", "dark.css")

            assert "focus-visible" in content
            assert "outline: 2px solid var(--app-color-primary)" in content
            assert "outline-offset: 2px" in content


class TestDarkThemeTemplate:
    """Tests for the dark theme's integration into the templates."""

    def test_dark_theme_css_included_in_base_template(self, client):
        """Test that the dark theme's CSS is included in the base template."""
        response = client.get("/login")
        assert response.status_code == 200
        assert "themes/dark.css" in response.data.decode("utf-8")

    def test_theme_toggle_button_present_for_authenticated_user(self, logged_in_client):
        """Test that the toggle button is present for authenticated users."""
        response = logged_in_client.get("/")
        assert response.status_code == 200
        html_content = response.data.decode("utf-8")

        assert "theme-toggle" in html_content
        assert 'aria-label="Basculer entre le thème clair et sombre"' in html_content

    def test_theme_toggle_button_absent_for_anonymous(self, client):
        """The sidebar (which hosts the toggle) is fully hidden on anonymous
        pages like /login - only the centered login card is shown."""
        response = client.get("/login")
        assert response.status_code == 200
        html_content = response.data.decode("utf-8")

        assert 'id="theme-toggle"' not in html_content

    def test_theme_javascript_present(self, logged_in_client):
        """Test that the dark theme's JavaScript is present."""
        response = logged_in_client.get("/")
        assert response.status_code == 200
        html_content = response.data.decode("utf-8")

        assert "js/main.js" in html_content
        assert 'type="module"' in html_content

        assert "function applyTheme" not in html_content

    def test_skip_link_present(self, client):
        """Test that the accessibility skip link is present. Under
        Tailwind/daisyUI, there's no dedicated .skip-link class anymore -
        the behavior (hidden except on focus) is carried by the
        Tailwind sr-only/focus:not-sr-only utilities, so this checks the
        link itself rather than a class name."""
        response = client.get("/login")
        assert response.status_code == 200
        html_content = response.data.decode("utf-8")

        assert 'href="#main-content"' in html_content
        assert "Sauter la navigation" in html_content


class TestDarkThemeAccessibility:
    """Tests for the dark theme's accessibility."""

    def test_theme_toggle_has_aria_attributes(self, logged_in_client):
        """Test that the theme toggle has the required accessibility
        attributes. Since switching to daisyUI's "Theme Controller"
        pattern (a real checkbox, see base.html/theme-manager.js),
        there's no more aria-pressed (button semantics, not relevant for
        a checkbox - the native "checked" is enough)."""
        response = logged_in_client.get("/")
        assert response.status_code == 200
        html_content = response.data.decode("utf-8")

        assert 'aria-label="Basculer entre le thème clair et sombre"' in html_content
        assert 'type="checkbox" id="theme-toggle"' in html_content

    def test_main_content_has_id(self, client):
        """Test that the main content has an ID for the skip link."""
        response = client.get("/login")
        assert response.status_code == 200
        html_content = response.data.decode("utf-8")

        assert 'id="main-content"' in html_content

    def test_navbar_has_role(self, logged_in_client):
        """Test that the navbar has an ARIA role. The nav sidebar only
        exists for authenticated users - anonymous pages hide it entirely."""
        response = logged_in_client.get("/")
        assert response.status_code == 200
        html_content = response.data.decode("utf-8")

        assert 'role="navigation"' in html_content


class TestDarkThemeVariables:
    """Tests for the dark theme's CSS variables."""

    def test_daisyui_variables_used(self, test_app):
        """Test that daisyUI's variables are used in variables.css."""
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
                ), f"daisyUI variable {var} not found in variables.css"

    def test_dark_theme_uses_data_attribute(self, test_app):
        """Test that the dark theme uses the data-theme attribute."""
        with test_app.app_context():
            content = read_css("themes", "dark.css")

            assert '[data-theme="dark"]' in content


class TestDarkThemeWCAGCompliance:
    """Tests for the dark theme's WCAG compliance."""

    def test_focus_styles_present(self, test_app):
        """Test that the accessibility focus styles are present."""
        with test_app.app_context():
            content = read_css("themes", "dark.css")

            assert "focus-visible" in content
            assert "outline: 2px solid" in content

            assert "a:focus-visible" in content
            assert "button:focus-visible" in content
            assert "input:focus-visible" in content
