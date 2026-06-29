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

// Initialiser le gestionnaire de thème
let themeManager;
document.addEventListener('DOMContentLoaded', () => {
    themeManager = new ThemeManager();
});

// ============================================
// FONCTIONS D'ACCESSIBILITÉ
// ============================================

/**
 * Annonce un message aux lecteurs d'écran.
 * @param {string} message - Message à annoncer
 * @param {string} politeness - Niveau de politesse ('polite' ou 'assertive')
 */
function announceToScreenReader(message, politeness = 'polite') {
    const liveRegion = document.getElementById('aria-live-region') || createLiveRegion(politeness);
    liveRegion.textContent = message;
    
    // Réinitialiser après l'annonce pour permettre des annonces répétées
    setTimeout(() => {
        liveRegion.textContent = '';
    }, 1000);
}

/**
 * Crée une région live pour les annonces aux lecteurs d'écran.
 * @param {string} politeness - Niveau de politesse ('polite' ou 'assertive')
 * @returns {HTMLElement} La région live créée
 */
function createLiveRegion(politeness) {
    const liveRegion = document.createElement('div');
    liveRegion.id = 'aria-live-region';
    liveRegion.setAttribute('role', 'status');
    liveRegion.setAttribute('aria-live', politeness);
    liveRegion.setAttribute('aria-atomic', 'true');
    liveRegion.style.position = 'absolute';
    liveRegion.style.width = '1px';
    liveRegion.style.height = '1px';
    liveRegion.style.margin = '-1px';
    liveRegion.style.padding = '0';
    liveRegion.style.overflow = 'hidden';
    liveRegion.style.clip = 'rect(0, 0, 0, 0)';
    liveRegion.style.border = '0';
    
    document.body.appendChild(liveRegion);
    return liveRegion;
}

/**
 * Met le focus sur un élément.
 * @param {HTMLElement|string} element - Élément ou sélecteur CSS
 */
function focusElement(element) {
    const el = typeof element === 'string' ? document.querySelector(element) : element;
    if (el && el.focus) {
        el.focus();
        // Ajouter un style de focus visible pour les navigateurs qui ne gèrent pas :focus-visible
        el.style.outline = '3px solid #00d1b2';
        el.style.outlineOffset = '2px';
    }
}

/**
 * Configure la navigation au clavier pour une liste d'éléments.
 * @param {HTMLElement|string} container - Conteneur ou sélecteur CSS
 * @param {string} itemSelector - Sélecteur CSS pour les éléments de la liste
 */
function setupKeyboardNavigation(container, itemSelector) {
    const cont = typeof container === 'string' ? document.querySelector(container) : container;
    if (!cont) return;

    const items = cont.querySelectorAll(itemSelector);
    if (items.length === 0) return;

    let currentIndex = 0;

    items.forEach((item, index) => {
        item.setAttribute('tabindex', '0');
        
        item.addEventListener('keydown', (e) => {
            switch (e.key) {
                case 'ArrowUp':
                case 'ArrowLeft':
                    e.preventDefault();
                    currentIndex = (currentIndex - 1 + items.length) % items.length;
                    focusElement(items[currentIndex]);
                    break;
                case 'ArrowDown':
                case 'ArrowRight':
                    e.preventDefault();
                    currentIndex = (currentIndex + 1) % items.length;
                    focusElement(items[currentIndex]);
                    break;
                case 'Home':
                    e.preventDefault();
                    currentIndex = 0;
                    focusElement(items[currentIndex]);
                    break;
                case 'End':
                    e.preventDefault();
                    currentIndex = items.length - 1;
                    focusElement(items[currentIndex]);
                    break;
                case 'Enter':
                case ' ':
                    e.preventDefault();
                    item.click();
                    break;
            }
        });

        item.addEventListener('focus', () => {
            currentIndex = index;
            item.setAttribute('aria-current', 'true');
        });

        item.addEventListener('blur', () => {
            item.setAttribute('aria-current', 'false');
        });
    });
}

/**
 * Affiche les erreurs de formulaire de manière accessible.
 * @param {Object} errors - Objet contenant les erreurs (ex: { field1: 'Erreur 1', field2: 'Erreur 2' })
 */
function displayFormErrorsAccessible(errors) {
    // Annoncer le nombre d'erreurs
    const errorCount = Object.keys(errors).length;
    const errorMessage = errorCount === 1 
        ? '1 erreur de formulaire. Veuillez la corriger.' 
        : `${errorCount} erreurs de formulaire. Veuillez les corriger.`;
    announceToScreenReader(errorMessage, 'assertive');

    // Mettre le focus sur le premier champ en erreur
    const firstErrorField = document.querySelector(`[name="${Object.keys(errors)[0]}"]`);
    if (firstErrorField) {
        focusElement(firstErrorField);
    }
}

/**
 * Valide un formulaire de manière accessible.
 * @param {HTMLElement|string} form - Formulaire ou sélecteur CSS
 * @returns {boolean} True si le formulaire est valide
 */
function validateFormAccessible(form) {
    const formEl = typeof form === 'string' ? document.querySelector(form) : form;
    if (!formEl) return false;

    let isValid = true;
    const errors = {};

    // Valider les champs requis
    const requiredFields = formEl.querySelectorAll('[required]');
    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            isValid = false;
            const fieldName = field.getAttribute('aria-label') || 
                             field.getAttribute('name') || 
                             field.getAttribute('id') || 
                             'Champ non nommé';
            errors[field.name || field.id] = `Le champ ${fieldName} est obligatoire.`;
            
            // Ajouter un message d'erreur visible
            let errorEl = field.nextElementSibling;
            if (!errorEl || !errorEl.classList.contains('error-message')) {
                errorEl = document.createElement('div');
                errorEl.className = 'help is-danger error-message';
                errorEl.setAttribute('role', 'alert');
                field.parentNode.insertBefore(errorEl, field.nextSibling);
            }
            errorEl.textContent = errors[field.name || field.id];
            
            // Ajouter une classe d'erreur au champ
            field.classList.add('is-danger');
        } else {
            // Supprimer l'erreur si elle existe
            const errorEl = field.nextElementSibling;
            if (errorEl && errorEl.classList.contains('error-message')) {
                errorEl.remove();
            }
            field.classList.remove('is-danger');
        }
    });

    if (!isValid) {
        displayFormErrorsAccessible(errors);
    }

    return isValid;
}

/**
 * Rend un tableau accessible.
 * @param {string} tableSelector - Sélecteur CSS pour le tableau
 */
function makeTableAccessible(tableSelector) {
    const table = document.querySelector(tableSelector);
    if (!table) return;

    // Ajouter scope aux en-têtes
    const headers = table.querySelectorAll('th');
    headers.forEach(header => {
        if (!header.hasAttribute('scope')) {
            header.setAttribute('scope', 'col');
        }
    });

    // Ajouter scope aux cellules d'en-tête de ligne
    const rowHeaders = table.querySelectorAll('td[role="rowheader"]');
    rowHeaders.forEach(header => {
        if (!header.hasAttribute('scope')) {
            header.setAttribute('scope', 'row');
        }
    });

    // Ajouter une légende si elle n'existe pas
    if (!table.querySelector('caption')) {
        const caption = document.createElement('caption');
        caption.className = 'is-sr-only';
        caption.textContent = 'Tableau de données';
        table.insertBefore(caption, table.firstChild);
    }
}

/**
 * Confirme une action avec l'utilisateur de manière accessible.
 * @param {string} message - Message de confirmation
 * @param {Function} onConfirm - Fonction à exécuter si l'utilisateur confirme
 * @param {Function} onCancel - Fonction à exécuter si l'utilisateur annule
 */
function confirmActionAccessible(message, onConfirm, onCancel) {
    // Créer une modale accessible
    const modal = document.createElement('div');
    modal.className = 'modal is-active';
    modal.setAttribute('role', 'dialog');
    modal.setAttribute('aria-modal', 'true');
    modal.setAttribute('aria-labelledby', 'confirmation-title');

    modal.innerHTML = `
        <div class="modal-background" role="button" tabindex="0" aria-label="Fermer"></div>
        <div class="modal-card">
            <header class="modal-card-head">
                <h2 id="confirmation-title" class="modal-card-title">Confirmation</h2>
                <button class="delete" aria-label="Fermer" role="button"></button>
            </header>
            <section class="modal-card-body">
                <p>${message}</p>
            </section>
            <footer class="modal-card-foot">
                <button class="button is-light" aria-label="Annuler" role="button">Annuler</button>
                <button class="button is-primary" aria-label="Confirmer" role="button">Confirmer</button>
            </footer>
        </div>
    `;

    document.body.appendChild(modal);

    // Mettre le focus sur le bouton Confirmer
    const confirmBtn = modal.querySelector('.button.is-primary');
    const cancelBtn = modal.querySelector('.button.is-light');
    const closeBtn = modal.querySelector('.delete');
    const background = modal.querySelector('.modal-background');

    focusElement(confirmBtn);

    // Gérer les événements
    const handleConfirm = () => {
        modal.remove();
        if (onConfirm) onConfirm();
    };

    const handleCancel = () => {
        modal.remove();
        if (onCancel) onCancel();
    };

    confirmBtn.addEventListener('click', handleConfirm);
    cancelBtn.addEventListener('click', handleCancel);
    closeBtn.addEventListener('click', handleCancel);
    background.addEventListener('click', handleCancel);

    // Gérer la navigation au clavier
    confirmBtn.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            handleConfirm();
        }
        if (e.key === 'Escape') {
            e.preventDefault();
            handleCancel();
        }
    });

    cancelBtn.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            handleCancel();
        }
        if (e.key === 'Escape') {
            e.preventDefault();
            handleCancel();
        }
    });

    closeBtn.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            handleCancel();
        }
    });

    // Piège de focus dans la modale
    modal.addEventListener('keydown', (e) => {
        if (e.key === 'Tab') {
            const focusableElements = modal.querySelectorAll(
                'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
            );
            const firstElement = focusableElements[0];
            const lastElement = focusableElements[focusableElements.length - 1];

            if (e.shiftKey && document.activeElement === firstElement) {
                e.preventDefault();
                focusElement(lastElement);
            } else if (!e.shiftKey && document.activeElement === lastElement) {
                e.preventDefault();
                focusElement(firstElement);
            }
        }
    });
}

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
    notification.setAttribute('role', 'alert');
    notification.setAttribute('aria-live', 'assertive');
    
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
    confirmActionAccessible,
    toggleVisibility,
    showElement,
    hideElement,
    addClass,
    removeClass,
    toggleClass,
    announceToScreenReader,
    focusElement,
    setupKeyboardNavigation,
    displayFormErrorsAccessible,
    validateFormAccessible,
    makeTableAccessible,
    // Instance du ThemeManager (initialisée au chargement)
    get themeManager() {
        return themeManager;
    }
};
