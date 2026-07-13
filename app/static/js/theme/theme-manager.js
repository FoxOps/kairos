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
        // daisyUI ne lit que l'attribut data-theme (thèmes nommés "light"/
        // "dark" définis dans base.html) - plus besoin de classe séparée
        // (.dark-mode dépendait de la dérivation clair/sombre de Bulma).
        const resolvedTheme = theme === 'dark' ? 'dark' : 'light';
        this.html.setAttribute('data-theme', resolvedTheme);
        localStorage.setItem(this.storageKey, resolvedTheme);

        this.updateToggleButton(resolvedTheme === 'dark');
    }

    /**
     * Toggle entre thème clair et sombre.
     */
    toggle() {
        const isCurrentlyDark = this.html.getAttribute('data-theme') === 'dark';
        this.applyTheme(isCurrentlyDark ? 'light' : 'dark');
    }

    /**
     * Met à jour le bouton toggle (icône soleil/lune daisyUI `swap`).
     * @param {boolean} isDark - True si le thème sombre est actif
     */
    updateToggleButton(isDark) {
        if (!this.toggleBtn) return;

        this.toggleBtn.setAttribute('aria-pressed', isDark ? 'true' : 'false');

        // `.swap` daisyUI sans <input> (bouton, pas une case à cocher) -
        // piloté par la classe `swap-active` plutôt qu'un état :checked.
        // Les icônes elles-même (.swap-on/.swap-off) gardent leurs classes
        // après conversion Font Awesome SVG+JS (voir base.html), seul le
        // conteneur .swap a besoin d'être manipulé ici.
        this.toggleBtn.classList.toggle('swap-active', isDark);
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
