import { announceToScreenReader } from '../utils/accessibility.js';

/**
 * Gère le thème sombre de l'application.
 * Utilise localStorage pour persister le choix de l'utilisateur.
 * Respecte les préférences système (prefers-color-scheme).
 */
export class ThemeManager {
    constructor() {
        this.html = document.documentElement;
        this.toggleBtn = document.getElementById('theme-toggle');
        this.storageKey = 'theme';
        this.init();
    }

    /**
     * Initialise le thème au chargement de la page.
     */
    init() {
        const currentTheme = this.getCurrentTheme();
        this.applyTheme(currentTheme);

        if (this.toggleBtn) {
            this.updateToggleButton(currentTheme === 'dark');
            this.toggleBtn.addEventListener('click', () => this.toggle());
        }

        // Écouter les changements de préférence système
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
            if (!localStorage.getItem(this.storageKey)) {
                this.applyTheme(e.matches ? 'dark' : 'light');
            }
        });

        // Initialiser l'accessibilité
        this.initAccessibility();
    }

    /**
     * Initialise les fonctionnalités d'accessibilité liées au thème.
     */
    initAccessibility() {
        // Annoncer le thème actuel aux lecteurs d'écran
        const currentTheme = this.getCurrentTheme();
        this.announceThemeChange(currentTheme);

        // Écouter les changements de thème pour les annoncer
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.attributeName === 'data-theme') {
                    const newTheme = this.html.getAttribute('data-theme');
                    this.announceThemeChange(newTheme);
                }
            });
        });

        observer.observe(this.html, {
            attributes: true
        });
    }

    /**
     * Annonce le changement de thème aux lecteurs d'écran.
     * @param {string} theme - 'dark' ou 'light'
     */
    announceThemeChange(theme) {
        const message = theme === 'dark'
            ? 'Thème sombre activé'
            : 'Thème clair activé';
        announceToScreenReader(message, 'polite');
    }

    /**
     * Applique le thème spécifié.
     * @param {string} theme - 'dark' ou 'light'
     */
    applyTheme(theme) {
        // Supprimer les classes et attributs existants
        this.html.classList.remove('dark-mode');
        this.html.removeAttribute('data-theme');

        // Appliquer le nouveau thème
        if (theme === 'dark') {
            this.html.setAttribute('data-theme', 'dark');
            this.html.classList.add('dark-mode');
            localStorage.setItem(this.storageKey, 'dark');
        } else {
            this.html.setAttribute('data-theme', 'light');
            localStorage.setItem(this.storageKey, 'light');
        }

        this.updateToggleButton(theme === 'dark');
    }

    /**
     * Toggle entre thème clair et sombre.
     */
    toggle() {
        const isCurrentlyDark = this.html.getAttribute('data-theme') === 'dark' ||
                               this.html.classList.contains('dark-mode');
        this.applyTheme(isCurrentlyDark ? 'light' : 'dark');
    }

    /**
     * Met à jour le bouton toggle.
     * @param {boolean} isDark - True si le thème sombre est actif
     */
    updateToggleButton(isDark) {
        if (!this.toggleBtn) return;

        const icon = this.toggleBtn.querySelector('i');
        this.toggleBtn.setAttribute('aria-pressed', isDark ? 'true' : 'false');

        if (isDark) {
            icon.classList.remove('fa-moon');
            icon.classList.add('fa-sun');
        } else {
            icon.classList.remove('fa-sun');
            icon.classList.add('fa-moon');
        }
    }

    /**
     * Obtient le thème actuel (localStorage ou système).
     * @returns {string} 'dark' ou 'light'
     */
    getCurrentTheme() {
        const storedTheme = localStorage.getItem(this.storageKey);
        if (storedTheme) return storedTheme;
        return this.getSystemTheme();
    }

    /**
     * Obtient la préférence système.
     * @returns {string} 'dark' ou 'light'
     */
    getSystemTheme() {
        return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }
}
