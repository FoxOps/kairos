"""
Tests pour les ressources statiques (vendor assets) de Leviia Schedule.

Ces tests vérifient que :
1. Les fichiers CSS/JS de Font Awesome 7.2.0 sont correctement installés
2. Les polices (webfonts) de Font Awesome 7.2.0 sont présentes
3. Les fichiers de Bulma et FullCalendar sont présents
"""

import pytest
import os
from flask import current_app


class TestFontAwesome:
    """Tests pour Font Awesome 7.2.0."""

    def test_font_awesome_css_exists(self, app):
        """Test que le fichier CSS de Font Awesome 7.2.0 existe."""
        with app.app_context():
            css_path = os.path.join(
                current_app.static_folder,
                'vendor',
                'font-awesome',
                'all.min.css'
            )
            assert os.path.exists(css_path), f"Le fichier {css_path} n'existe pas"

    def test_font_awesome_css_version(self, app):
        """Test que le fichier CSS contient la version 7.2.0."""
        with app.app_context():
            css_path = os.path.join(
                current_app.static_folder,
                'vendor',
                'font-awesome',
                'all.min.css'
            )
            
            with open(css_path, 'r') as f:
                content = f.read()
            
            # Vérifier la présence de la version 7.2.0
            assert 'Font Awesome Free 7.2.0' in content, "La version 7.2.0 n'est pas trouvée dans le CSS"

    def test_font_awesome_webfonts_exist(self, app):
        """Test que les fichiers webfonts de Font Awesome 7.2.0 existent."""
        with app.app_context():
            webfonts_dir = os.path.join(
                current_app.static_folder,
                'vendor',
                'font-awesome',
                'webfonts'
            )
            
            # Fichiers WOFF2 requis pour Font Awesome 7.2.0
            required_files = [
                'fa-brands-400.woff2',
                'fa-regular-400.woff2',
                'fa-solid-900.woff2',
                'fa-v4compatibility.woff2'
            ]
            
            for font_file in required_files:
                font_path = os.path.join(webfonts_dir, font_file)
                assert os.path.exists(font_path), f"Le fichier {font_path} n'existe pas"

    def test_font_awesome_webfonts_referenced_in_css(self, app):
        """Test que le CSS référence correctement les webfonts."""
        with app.app_context():
            css_path = os.path.join(
                current_app.static_folder,
                'vendor',
                'font-awesome',
                'all.min.css'
            )
            
            with open(css_path, 'r') as f:
                content = f.read()
            
            # Vérifier que le CSS référence les polices
            assert 'url(../webfonts/fa-brands-400.woff2)' in content, "fa-brands-400.woff2 non référencé"
            assert 'url(../webfonts/fa-regular-400.woff2)' in content, "fa-regular-400.woff2 non référencé"
            assert 'url(../webfonts/fa-solid-900.woff2)' in content, "fa-solid-900.woff2 non référencé"


class TestBulma:
    """Tests pour Bulma CSS."""

    def test_bulma_css_exists(self, app):
        """Test que le fichier CSS de Bulma existe."""
        with app.app_context():
            css_path = os.path.join(
                current_app.static_folder,
                'vendor',
                'bulma',
                'bulma.css'
            )
            assert os.path.exists(css_path), f"Le fichier {css_path} n'existe pas"


class TestFullCalendar:
    """Tests pour FullCalendar."""

    def test_fullcalendar_js_exists(self, app):
        """Test que le fichier JS de FullCalendar existe."""
        with app.app_context():
            js_path = os.path.join(
                current_app.static_folder,
                'vendor',
                'fullcalendar',
                'index.global.min.js'
            )
            assert os.path.exists(js_path), f"Le fichier {js_path} n'existe pas"

    def test_fullcalendar_locale_fr_exists(self, app):
        """Test que le fichier de locale française de FullCalendar existe."""
        with app.app_context():
            locale_path = os.path.join(
                current_app.static_folder,
                'vendor',
                'fullcalendar',
                'locales',
                'fr.global.min.js'
            )
            assert os.path.exists(locale_path), f"Le fichier {locale_path} n'existe pas"
