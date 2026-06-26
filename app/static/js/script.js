/**
 * Leviia Schedule - JavaScript Principal
 * ======================================
 * 
 * Ce fichier centralise toute la logique JavaScript de l'application.
 * Il remplace les scripts inline dans les templates.
 */

// ============================================
// GESTION DU THÈME SOMBRE
// ============================================

/**
 * Gère le thème sombre de l'application.
 * Utilise localStorage pour persister le choix de l'utilisateur.
 * Respecte les préférences système (prefers-color-scheme).
 */
class ThemeManager {
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

// Initialiser le gestionnaire de thème
let themeManager;
document.addEventListener('DOMContentLoaded', () => {
    themeManager = new ThemeManager();
});

// ============================================
// FONCTIONS UTILITAIRES
// ============================================

/**
 * Formate une date pour l'affichage.
 * @param {Date|string} date - Date à formater
 * @returns {string} Date formatée
 */
function formatDate(date) {
    if (!date) return '';
    if (typeof date === 'string') date = new Date(date);
    return date.toLocaleDateString('fr-FR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric'
    });
}

/**
 * Formate une heure pour l'affichage.
 * @param {Date|string} date - Date à formater
 * @returns {string} Heure formatée
 */
function formatTime(date) {
    if (!date) return '';
    if (typeof date === 'string') date = new Date(date);
    return date.toLocaleTimeString('fr-FR', {
        hour: '2-digit',
        minute: '2-digit'
    });
}

/**
 * Formate une date et heure pour l'affichage.
 * @param {Date|string} date - Date à formater
 * @returns {string} Date et heure formatées
 */
function formatDateTime(date) {
    if (!date) return '';
    if (typeof date === 'string') date = new Date(date);
    return date.toLocaleString('fr-FR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

/**
 * Affiche une notification.
 * @param {string} message - Message à afficher
 * @param {string} type - Type de notification (success, danger, warning, info)
 */
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification is-${type}`;
    notification.textContent = message;
    notification.style.position = 'fixed';
    notification.style.top = '20px';
    notification.style.right = '20px';
    notification.style.zIndex = '1000';
    notification.style.maxWidth = '400px';
    
    document.body.appendChild(notification);
    
    // Supprimer après 5 secondes
    setTimeout(() => {
        notification.classList.add('is-hidden');
        setTimeout(() => notification.remove(), 500);
    }, 5000);
}

/**
 * Confirme une action avec l'utilisateur.
 * @param {string} message - Message de confirmation
 * @returns {boolean} True si confirmé
 */
function confirmAction(message) {
    return confirm(message);
}

// ============================================
// GESTION DES ÉLÉMENTS DU DOM
// ============================================

/**
 * Toggle la visibilité d'un élément.
 * @param {string|HTMLElement} element - Élément ou sélecteur
 */
function toggleVisibility(element) {
    const el = typeof element === 'string' ? document.querySelector(element) : element;
    if (el) {
        el.style.display = el.style.display === 'none' ? '' : 'none';
    }
}

/**
 * Affiche un élément.
 * @param {string|HTMLElement} element - Élément ou sélecteur
 */
function showElement(element) {
    const el = typeof element === 'string' ? document.querySelector(element) : element;
    if (el) {
        el.style.display = '';
    }
}

/**
 * Masque un élément.
 * @param {string|HTMLElement} element - Élément ou sélecteur
 */
function hideElement(element) {
    const el = typeof element === 'string' ? document.querySelector(element) : element;
    if (el) {
        el.style.display = 'none';
    }
}

/**
 * Ajoute une classe à un élément.
 * @param {string|HTMLElement} element - Élément ou sélecteur
 * @param {string} className - Classe à ajouter
 */
function addClass(element, className) {
    const el = typeof element === 'string' ? document.querySelector(element) : element;
    if (el) {
        el.classList.add(className);
    }
}

/**
 * Supprime une classe d'un élément.
 * @param {string|HTMLElement} element - Élément ou sélecteur
 * @param {string} className - Classe à supprimer
 */
function removeClass(element, className) {
    const el = typeof element === 'string' ? document.querySelector(element) : element;
    if (el) {
        el.classList.remove(className);
    }
}

/**
 * Toggle une classe sur un élément.
 * @param {string|HTMLElement} element - Élément ou sélecteur
 * @param {string} className - Classe à toggler
 */
function toggleClass(element, className) {
    const el = typeof element === 'string' ? document.querySelector(element) : element;
    if (el) {
        el.classList.toggle(className);
    }
}

// ============================================
// EXPORT POUR UTILISATION DANS LES TEMPLATES
// ============================================

// Exporter les fonctions pour les templates
window.Leviia = {
    ThemeManager,
    formatDate,
    formatTime,
    formatDateTime,
    showNotification,
    confirmAction,
    toggleVisibility,
    showElement,
    hideElement,
    addClass,
    removeClass,
    toggleClass,
    // Instance du ThemeManager (initialisée au chargement)
    get themeManager() {
        return themeManager;
    }
};
