import { announceToScreenReader } from '../utils/accessibility.js';

/**
 * Manages the app's dark theme.
 * Uses localStorage to persist the user's choice.
 * Honors the system preference (prefers-color-scheme).
 */
export class ThemeManager {
    constructor() {
        this.html = document.documentElement;
        this.toggleBtn = document.getElementById('theme-toggle');
        this.storageKey = 'theme';
        this.init();
    }

    /**
     * Initialize the theme on page load.
     */
    init() {
        const currentTheme = this.getCurrentTheme();
        this.applyTheme(currentTheme);

        if (this.toggleBtn) {
            this.updateToggleButton(currentTheme === 'dark');
            // Checkbox (daisyUI's "Theme Controller" swap pattern, see
            // base.html) - "change" is the semantically correct event for
            // a checkbox, not "click".
            this.toggleBtn.addEventListener('change', () => this.toggle());
        }

        // Watch for system-preference changes
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
            if (!localStorage.getItem(this.storageKey)) {
                this.applyTheme(e.matches ? 'dark' : 'light');
            }
        });

        // Initialize accessibility
        this.initAccessibility();
    }

    /**
     * Initialize theme-related accessibility features.
     */
    initAccessibility() {
        // Announce the current theme to screen readers
        const currentTheme = this.getCurrentTheme();
        this.announceThemeChange(currentTheme);

        // Watch for theme changes to announce them
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
     * Announce the theme change to screen readers.
     * @param {string} theme - 'dark' or 'light'
     */
    announceThemeChange(theme) {
        const message = theme === 'dark'
            ? 'Thème sombre activé'
            : 'Thème clair activé';
        announceToScreenReader(message, 'polite');
    }

    /**
     * Apply the given theme.
     * @param {string} theme - 'dark' or 'light'
     */
    applyTheme(theme) {
        // daisyUI only reads the data-theme attribute (themes named
        // "light"/"dark" defined in base.html) - no separate class needed
        // anymore (.dark-mode used to depend on Bulma's light/dark
        // derivation).
        const resolvedTheme = theme === 'dark' ? 'dark' : 'light';
        this.html.setAttribute('data-theme', resolvedTheme);
        localStorage.setItem(this.storageKey, resolvedTheme);

        this.updateToggleButton(resolvedTheme === 'dark');
    }

    /**
     * Toggle between light and dark theme.
     */
    toggle() {
        const isCurrentlyDark = this.html.getAttribute('data-theme') === 'dark';
        this.applyTheme(isCurrentlyDark ? 'light' : 'dark');
    }

    /**
     * Update the toggle button (daisyUI `swap` sun/moon icon, driven by a
     * real checkbox - see base.html).
     * @param {boolean} isDark - True if the dark theme is active
     */
    updateToggleButton(isDark) {
        if (!this.toggleBtn) return;

        // Real checkbox: the "checked" state natively drives
        // .swap-on/.swap-off through daisyUI's own :checked CSS, no need
        // to toggle a swap-active class by hand. The native "checked" also
        // carries the accessibility semantics (no need for aria-pressed,
        // which is for buttons, not checkboxes).
        this.toggleBtn.checked = isDark;
    }

    /**
     * Get the current theme (localStorage or system).
     * @returns {string} 'dark' or 'light'
     */
    getCurrentTheme() {
        const storedTheme = localStorage.getItem(this.storageKey);
        if (storedTheme) return storedTheme;
        return this.getSystemTheme();
    }

    /**
     * Get the system preference.
     * @returns {string} 'dark' or 'light'
     */
    getSystemTheme() {
        return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }
}
