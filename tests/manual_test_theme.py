#!/usr/bin/env python3
"""
Manual test script to check the visual theme fixes.

This script lets you manually test the key features:
1. Dark theme (toggle, persistence, system preferences)
2. FullCalendar rendering
3. Visual consistency across pages
4. Accessibility

Run with: python tests/manual_test_theme.py
"""

import os
import sys

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def print_header(title):
    """Print a colored header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def print_section(title):
    """Print a colored section."""
    print(f"\n{'-'*60}")
    print(f"  {title}")
    print(f"{'-'*60}")


def print_result(test_name, passed, message=""):
    """Print a test's result."""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"  {status}: {test_name}")
    if message:
        print(f"     → {message}")


def test_file_structure():
    """Test the file structure."""
    print_header("📁 FILE STRUCTURE TEST")

    static_folder = os.path.join(os.path.dirname(__file__), "..", "app", "static")
    template_folder = os.path.join(os.path.dirname(__file__), "..", "app", "templates")

    # Check the CSS files
    css_files = [
        "css/variables.css",
        "css/base.css",
        "css/utilities.css",
        "css/themes/dark.css",
        "css/vendor/fullcalendar-overrides.css",
    ]

    print_section("CSS files")
    for css_file in css_files:
        css_path = os.path.join(static_folder, css_file)
        exists = os.path.exists(css_path)
        print_result(
            f"{css_file} exists",
            exists,
            f"Size: {os.path.getsize(css_path)} bytes" if exists else "",
        )

    # Check the JS files
    print_section("JavaScript files")
    js_files = [
        "js/main.js",
        "js/theme/theme-manager.js",
        "js/utils/dom.js",
        "js/utils/accessibility.js",
        "js/notifications/flash-messages.js",
    ]
    for js_file in js_files:
        js_path = os.path.join(static_folder, js_file)
        exists = os.path.exists(js_path)
        size = os.path.getsize(js_path) if exists else 0
        print_result(
            f"{js_file} exists", exists, f"Size: {size} bytes" if exists else ""
        )

    # Check the templates
    print_section("Templates")
    template_files = [
        "base.html",
        "index.html",
        "dashboard.html",
        "schedule.html",
        "oncall.html",
        "leave.html",
    ]
    for template_file in template_files:
        template_path = os.path.join(template_folder, template_file)
        exists = os.path.exists(template_path)
        size = os.path.getsize(template_path) if exists else 0
        print_result(
            f"{template_file} exists",
            exists,
            f"Size: {size} bytes" if exists else "",
        )


def test_css_content():
    """Test the CSS files' content."""
    print_header("🎨 CSS CONTENT TEST")

    static_folder = os.path.join(os.path.dirname(__file__), "..", "app", "static")

    # Check base.css / utilities.css / components/buttons.css
    print_section("base.css / utilities.css / components/buttons.css")
    with open(os.path.join(static_folder, "css", "base.css")) as f:
        base_content = f.read()
    with open(os.path.join(static_folder, "css", "utilities.css")) as f:
        utilities_content = f.read()
    with open(os.path.join(static_folder, "css", "components", "buttons.css")) as f:
        buttons_content = f.read()

    checks = [
        (".skip-link" in base_content, "skip-link class present (base.css)"),
        (
            ".min-w-180" in utilities_content,
            "min-w-180 class present (utilities.css)",
        ),
        (".gap-2" in utilities_content, "gap-2 class present (utilities.css)"),
        (".d-none" in utilities_content, "d-none class present (utilities.css)"),
        (
            ".type-tag" in buttons_content,
            "type-tag class present (components/buttons.css)",
        ),
    ]

    for passed, description in checks:
        print_result(description, passed)

    # Check vendor/fullcalendar-overrides.css and themes/dark.css
    print_section("vendor/fullcalendar-overrides.css / themes/dark.css")
    fc_styles_path = os.path.join(
        static_folder, "css", "vendor", "fullcalendar-overrides.css"
    )
    with open(fc_styles_path) as f:
        fc_content = f.read()
    dark_theme_path = os.path.join(static_folder, "css", "themes", "dark.css")
    with open(dark_theme_path) as f:
        dark_content = f.read()

    checks = [
        (".fc-event-shift" in fc_content, "fc-event-shift style present"),
        (".fc-event-oncall" in fc_content, "fc-event-oncall style present"),
        (".fc-event-leave" in fc_content, "fc-event-leave style present"),
        ('[data-theme="dark"]' in dark_content, "dark theme selectors present"),
    ]

    for passed, description in checks:
        print_result(description, passed)

    # Check variables.css
    print_section("variables.css")
    variables_path = os.path.join(static_folder, "css", "variables.css")
    with open(variables_path) as f:
        content = f.read()

    checks = [
        ("--bulma-grey:", "--bulma-grey variable present"),
        ("--bulma-grey-light:", "--bulma-grey-light variable present"),
        ("--bulma-grey-dark:", "--bulma-grey-dark variable present"),
    ]

    for variable, description in checks:
        print_result(description, variable in content)


def test_js_content():
    """Test the JavaScript file's content."""
    print_header("⚡ JAVASCRIPT CONTENT TEST")

    static_folder = os.path.join(os.path.dirname(__file__), "..", "app", "static")
    theme_manager_path = os.path.join(static_folder, "js", "theme", "theme-manager.js")

    with open(theme_manager_path) as f:
        content = f.read()

    print_section("js/theme/theme-manager.js")
    checks = [
        ("class ThemeManager", "ThemeManager class present"),
        ("applyTheme", "applyTheme function present"),
        ("getSystemTheme", "getSystemTheme function present"),
        ("getCurrentTheme", "getCurrentTheme function present"),
        ("localStorage", "localStorage usage present"),
        ("prefers-color-scheme", "system-preference support present"),
    ]

    for check, description in checks:
        print_result(description, check in content)


def test_template_content():
    """Test the templates' content."""
    print_header("📜 TEMPLATE CONTENT TEST")

    template_folder = os.path.join(os.path.dirname(__file__), "..", "app", "templates")

    # Check base.html
    print_section("base.html")
    base_path = os.path.join(template_folder, "base.html")
    with open(base_path) as f:
        content = f.read()

    checks = [
        ("css/base.css", "base.css included"),
        ("themes/dark.css", "themes/dark.css included"),
        ("js/main.js", "main.js included"),
        ('type="module"' in content, "main.js loaded as an ES6 module"),
        ("function applyTheme" not in content, "no inline applyTheme function"),
    ]

    for check, description in checks:
        if isinstance(check, bool):
            print_result(description, check)
        else:
            print_result(description, check in content)

    # Check index.html
    print_section("index.html")
    index_path = os.path.join(template_folder, "index.html")
    with open(index_path) as f:
        content = f.read()

    checks = [
        (
            "vendor/fullcalendar-overrides.css",
            "vendor/fullcalendar-overrides.css included",
        ),
        ("min-w-180", "min-w-180 class used"),
        ('style="min-width: 180px"' not in content, "no inline min-width style"),
    ]

    for check, description in checks:
        if isinstance(check, bool):
            print_result(description, check)
        else:
            print_result(description, check in content)

    # Check dashboard.html
    print_section("dashboard.html")
    dashboard_path = os.path.join(template_folder, "dashboard.html")
    with open(dashboard_path) as f:
        content = f.read()

    checks = [
        ('class="badge badge-primary"', "badge badge-primary class used"),
        ('class="badge badge-ghost"', "badge badge-ghost class used"),
        ("var(--bulma-grey)" not in content, "no var(--bulma-grey)"),
    ]

    for check, description in checks:
        if isinstance(check, bool):
            print_result(description, check)
        else:
            print_result(description, check in content)


def test_duplicate_detection():
    """Test the duplication detection."""
    print_header("🔍 DUPLICATION DETECTION TEST")

    template_folder = os.path.join(os.path.dirname(__file__), "..", "app", "templates")
    static_folder = os.path.join(os.path.dirname(__file__), "..", "app", "static")

    print_section("CSS duplication check")

    # Check that skip-link only lives in base.css
    base_styles_path = os.path.join(static_folder, "css", "base.css")
    base_template_path = os.path.join(template_folder, "base.html")

    with open(base_styles_path) as f:
        base_styles_content = f.read()
    with open(base_template_path) as f:
        base_template_content = f.read()

    has_skip_link_in_css = ".skip-link" in base_styles_content
    has_skip_link_inline = (
        "<style>" in base_template_content and ".skip-link" in base_template_content
    )

    print_result("skip-link in base.css", has_skip_link_in_css)
    print_result("skip-link is NOT inline in base.html", not has_skip_link_inline)

    # Check that FullCalendar only lives in vendor/fullcalendar-overrides.css
    fc_styles_path = os.path.join(
        static_folder, "css", "vendor", "fullcalendar-overrides.css"
    )
    index_template_path = os.path.join(template_folder, "index.html")

    with open(fc_styles_path) as f:
        fc_styles_content = f.read()
    with open(index_template_path) as f:
        index_template_content = f.read()

    has_fc_in_css = ".fc-event-shift" in fc_styles_content
    has_fc_inline = (
        "<style>" in index_template_content
        and ".fc-event-shift" in index_template_content
    )

    print_result("FullCalendar in vendor/fullcalendar-overrides.css", has_fc_in_css)
    print_result("FullCalendar is NOT inline in index.html", not has_fc_inline)


def run_all_tests():
    """Run every test."""
    print("\n" + "=" * 60)
    print("  🧪 MANUAL TESTS FOR THE VISUAL THEME")
    print("=" * 60)

    test_file_structure()
    test_css_content()
    test_js_content()
    test_template_content()
    test_duplicate_detection()

    print_header("✅ ALL MANUAL TESTS COMPLETE")
    print("\nTo test the dynamic features (dark theme, FullCalendar),")
    print("start the server and test manually in the browser:")
    print("  1. Navigate to http://localhost:5000")
    print("  2. Click the moon/sun button to toggle the dark theme")
    print("  3. Check that the theme persists across pages")
    print("  4. Check that FullCalendar renders correctly")
    print("  5. Test the skip-link (Tab + Enter)")
    print("\nTo run the automated tests:")
    print("  pytest tests/test_dark_theme.py tests/test_theme_fixes.py -v")


if __name__ == "__main__":
    run_all_tests()
