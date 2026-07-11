#!/usr/bin/env python3
"""
Script de test manuel pour vérifier les corrections du thème visuel.

Ce script permet de tester manuellement les fonctionnalités clés :
1. Thème sombre (toggle, persistance, préférences système)
2. Affichage FullCalendar
3. Cohérence visuelle entre les pages
4. Accessibilité

Exécution : python tests/manual_test_theme.py
"""

import sys
import os

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from app.models import User, Group, ShiftType

def print_header(title):
    """Affiche un en-tête coloré."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def print_section(title):
    """Affiche une section colorée."""
    print(f"\n{'-'*60}")
    print(f"  {title}")
    print(f"{'-'*60}")

def print_result(test_name, passed, message=""):
    """Affiche le résultat d'un test."""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"  {status}: {test_name}")
    if message:
        print(f"     → {message}")

def test_file_structure():
    """Teste la structure des fichiers."""
    print_header("📁 TEST DE LA STRUCTURE DES FICHIERS")
    
    static_folder = os.path.join(os.path.dirname(__file__), '..', 'app', 'static')
    template_folder = os.path.join(os.path.dirname(__file__), '..', 'app', 'templates')
    
    # Vérifier les fichiers CSS
    css_files = [
        'css/variables.css',
        'css/base.css',
        'css/utilities.css',
        'css/themes/dark.css',
        'css/vendor/fullcalendar-overrides.css',
    ]

    print_section("Fichiers CSS")
    for css_file in css_files:
        css_path = os.path.join(static_folder, css_file)
        exists = os.path.exists(css_path)
        print_result(f"{css_file} existe", exists, f"Taille: {os.path.getsize(css_path)} octets" if exists else "")

    # Vérifier les fichiers JS
    print_section("Fichiers JavaScript")
    js_files = [
        'js/main.js',
        'js/theme/theme-manager.js',
        'js/utils/dom.js',
        'js/utils/date.js',
        'js/utils/accessibility.js',
        'js/notifications/toast.js',
    ]
    for js_file in js_files:
        js_path = os.path.join(static_folder, js_file)
        exists = os.path.exists(js_path)
        size = os.path.getsize(js_path) if exists else 0
        print_result(f"{js_file} existe", exists, f"Taille: {size} octets" if exists else "")
    
    # Vérifier les templates
    print_section("Templates")
    template_files = ['base.html', 'index.html', 'dashboard.html', 'schedule.html', 'oncall.html', 'leave.html']
    for template_file in template_files:
        template_path = os.path.join(template_folder, template_file)
        exists = os.path.exists(template_path)
        size = os.path.getsize(template_path) if exists else 0
        print_result(f"{template_file} existe", exists, f"Taille: {size} octets" if exists else "")

def test_css_content():
    """Teste le contenu des fichiers CSS."""
    print_header("🎨 TEST DU CONTENU CSS")
    
    static_folder = os.path.join(os.path.dirname(__file__), '..', 'app', 'static')
    
    # Vérifier base.css / utilities.css / components/buttons.css
    print_section("base.css / utilities.css / components/buttons.css")
    with open(os.path.join(static_folder, 'css', 'base.css'), 'r') as f:
        base_content = f.read()
    with open(os.path.join(static_folder, 'css', 'utilities.css'), 'r') as f:
        utilities_content = f.read()
    with open(os.path.join(static_folder, 'css', 'components', 'buttons.css'), 'r') as f:
        buttons_content = f.read()

    checks = [
        ('.skip-link' in base_content, "Classe skip-link présente (base.css)"),
        ('.min-w-180' in utilities_content, "Classe min-w-180 présente (utilities.css)"),
        ('.gap-2' in utilities_content, "Classe gap-2 présente (utilities.css)"),
        ('.d-none' in utilities_content, "Classe d-none présente (utilities.css)"),
        ('.type-tag' in buttons_content, "Classe type-tag présente (components/buttons.css)"),
    ]

    for passed, description in checks:
        print_result(description, passed)

    # Vérifier vendor/fullcalendar-overrides.css et themes/dark.css
    print_section("vendor/fullcalendar-overrides.css / themes/dark.css")
    fc_styles_path = os.path.join(static_folder, 'css', 'vendor', 'fullcalendar-overrides.css')
    with open(fc_styles_path, 'r') as f:
        fc_content = f.read()
    dark_theme_path = os.path.join(static_folder, 'css', 'themes', 'dark.css')
    with open(dark_theme_path, 'r') as f:
        dark_content = f.read()

    checks = [
        ('.fc-event-shift' in fc_content, "Style fc-event-shift présent"),
        ('.fc-event-oncall' in fc_content, "Style fc-event-oncall présent"),
        ('.fc-event-leave' in fc_content, "Style fc-event-leave présent"),
        ('[data-theme="dark"]' in dark_content, "Sélecteurs dark theme présents"),
    ]

    for passed, description in checks:
        print_result(description, passed)

    # Vérifier variables.css
    print_section("variables.css")
    variables_path = os.path.join(static_folder, 'css', 'variables.css')
    with open(variables_path, 'r') as f:
        content = f.read()

    checks = [
        ('--bulma-grey:', "Variable --bulma-grey présente"),
        ('--bulma-grey-light:', "Variable --bulma-grey-light présente"),
        ('--bulma-grey-dark:', "Variable --bulma-grey-dark présente"),
    ]

    for variable, description in checks:
        print_result(description, variable in content)

def test_js_content():
    """Teste le contenu du fichier JavaScript."""
    print_header("⚡ TEST DU CONTENU JAVASCRIPT")
    
    static_folder = os.path.join(os.path.dirname(__file__), '..', 'app', 'static')
    theme_manager_path = os.path.join(static_folder, 'js', 'theme', 'theme-manager.js')

    with open(theme_manager_path, 'r') as f:
        content = f.read()

    print_section("js/theme/theme-manager.js")
    checks = [
        ('class ThemeManager', "Classe ThemeManager présente"),
        ('applyTheme', "Fonction applyTheme présente"),
        ('getSystemTheme', "Fonction getSystemTheme présente"),
        ('getCurrentTheme', "Fonction getCurrentTheme présente"),
        ('localStorage', "Utilisation de localStorage présente"),
        ('prefers-color-scheme', "Support des préférences système présent"),
    ]

    for check, description in checks:
        print_result(description, check in content)

def test_template_content():
    """Teste le contenu des templates."""
    print_header("📜 TEST DU CONTENU DES TEMPLATES")
    
    template_folder = os.path.join(os.path.dirname(__file__), '..', 'app', 'templates')
    
    # Vérifier base.html
    print_section("base.html")
    base_path = os.path.join(template_folder, 'base.html')
    with open(base_path, 'r') as f:
        content = f.read()
    
    checks = [
        ('css/base.css', "base.css inclus"),
        ('themes/dark.css', "themes/dark.css inclus"),
        ('js/main.js', "main.js inclus"),
        ('type="module"' in content, "main.js chargé en module ES6"),
        ('function applyTheme' not in content, "Pas de fonction applyTheme inline"),
    ]
    
    for check, description in checks:
        if isinstance(check, bool):
            print_result(description, check)
        else:
            print_result(description, check in content)
    
    # Vérifier index.html
    print_section("index.html")
    index_path = os.path.join(template_folder, 'index.html')
    with open(index_path, 'r') as f:
        content = f.read()
    
    checks = [
        ('vendor/fullcalendar-overrides.css', "vendor/fullcalendar-overrides.css inclus"),
        ('min-w-180', "Classe min-w-180 utilisée"),
        ('style="min-width: 180px"' not in content, "Pas de style inline min-width"),
    ]
    
    for check, description in checks:
        if isinstance(check, bool):
            print_result(description, check)
        else:
            print_result(description, check in content)
    
    # Vérifier dashboard.html
    print_section("dashboard.html")
    dashboard_path = os.path.join(template_folder, 'dashboard.html')
    with open(dashboard_path, 'r') as f:
        content = f.read()
    
    checks = [
        ('class="type-tag is-primary"', "Classe type-tag is-primary utilisée"),
        ('class="type-tag is-light"', "Classe type-tag is-light utilisée"),
        ('var(--bulma-grey)' not in content, "Pas de var(--bulma-grey)"),
    ]
    
    for check, description in checks:
        if isinstance(check, bool):
            print_result(description, check)
        else:
            print_result(description, check in content)

def test_duplicate_detection():
    """Teste la détection des duplications."""
    print_header("🔍 TEST DE DÉTECTION DES DUPLICATIONS")
    
    template_folder = os.path.join(os.path.dirname(__file__), '..', 'app', 'templates')
    static_folder = os.path.join(os.path.dirname(__file__), '..', 'app', 'static')
    
    print_section("Vérification des duplications CSS")
    
    # Vérifier que skip-link n'est que dans base.css
    base_styles_path = os.path.join(static_folder, 'css', 'base.css')
    base_template_path = os.path.join(template_folder, 'base.html')

    with open(base_styles_path, 'r') as f:
        base_styles_content = f.read()
    with open(base_template_path, 'r') as f:
        base_template_content = f.read()

    has_skip_link_in_css = '.skip-link' in base_styles_content
    has_skip_link_inline = '<style>' in base_template_content and '.skip-link' in base_template_content

    print_result("skip-link dans base.css", has_skip_link_in_css)
    print_result("skip-link N'EST PAS inline dans base.html", not has_skip_link_inline)

    # Vérifier que FullCalendar n'est que dans vendor/fullcalendar-overrides.css
    fc_styles_path = os.path.join(static_folder, 'css', 'vendor', 'fullcalendar-overrides.css')
    index_template_path = os.path.join(template_folder, 'index.html')

    with open(fc_styles_path, 'r') as f:
        fc_styles_content = f.read()
    with open(index_template_path, 'r') as f:
        index_template_content = f.read()

    has_fc_in_css = '.fc-event-shift' in fc_styles_content
    has_fc_inline = '<style>' in index_template_content and '.fc-event-shift' in index_template_content

    print_result("FullCalendar dans vendor/fullcalendar-overrides.css", has_fc_in_css)
    print_result("FullCalendar N'EST PAS inline dans index.html", not has_fc_inline)

def run_all_tests():
    """Exécute tous les tests."""
    print("\n" + "="*60)
    print("  🧪 TESTS MANUELS POUR LE THÈME VISUEL")
    print("="*60)
    
    test_file_structure()
    test_css_content()
    test_js_content()
    test_template_content()
    test_duplicate_detection()
    
    print_header("✅ TOUS LES TESTS MANUELS TERMINÉS")
    print("\nPour tester les fonctionnalités dynamiques (thème sombre, FullCalendar),")
    print("veuillez démarrer le serveur et tester manuellement dans le navigateur :")
    print("  1. Naviguez sur http://localhost:5000")
    print("  2. Cliquez sur le bouton lune/soleil pour toggler le thème sombre")
    print("  3. Vérifiez que le thème est persistant entre les pages")
    print("  4. Vérifiez que FullCalendar s'affiche correctement")
    print("  5. Testez le skip-link (Tab + Entrée)")
    print("\nPour exécuter les tests automatiques :")
    print("  pytest tests/test_dark_theme.py tests/test_theme_fixes.py -v")

if __name__ == '__main__':
    run_all_tests()
