/**
 * Leviia Schedule - JavaScript Principal
 * ======================================
 * 
 * Ce fichier centralise toute la logique JavaScript de l'application.
 * Il remplace les scripts inline dans les templates.
 * 
 * Améliorations WCAG implémentées :
 * - Gestion des attributs ARIA
 * - Navigation au clavier
 * - Focus visible
 * - Messages accessibles
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
            
            // Ajouter la gestion du clavier
            this.toggleBtn.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    this.toggle();
                }
            });
        }

        // Écouter les changements de préférence système
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
            if (!localStorage.getItem(this.storageKey)) {
                this.applyTheme(e.matches ? 'dark' : 'light');
            }
        });

        // Initialiser l'accessibilité au chargement
        this.initAccessibility();
    }

    /**
     * Initialise les fonctionnalités d'accessibilité.
     */
    initAccessibility() {
        // Ajouter l'attribut aria-live à la région principale
        const mainContent = document.getElementById('main-content');
        if (mainContent && !mainContent.getAttribute('aria-live')) {
            mainContent.setAttribute('aria-live', 'polite');
        }

        // Gérer le menu burger pour mobile
        this.initMobileMenu();

        // Gérer les dropdowns accessibles
        this.initAccessibleDropdowns();

        // Gérer les notifications accessibles
        this.initAccessibleNotifications();
    }

    /**
     * Initialise le menu mobile accessible.
     */
    initMobileMenu() {
        const navbarBurgers = document.querySelectorAll('.navbar-burger');
        
        navbarBurgers.forEach(burger => {
            burger.addEventListener('click', () => {
                const targetId = burger.getAttribute('aria-controls');
                const target = document.getElementById(targetId);
                
                if (target) {
                    const isExpanded = burger.getAttribute('aria-expanded') === 'true';
                    burger.setAttribute('aria-expanded', !isExpanded);
                    target.classList.toggle('is-active');
                }
            });

            // Ajouter la gestion du clavier
            burger.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    burger.click();
                }
            });
        });
    }

    /**
     * Initialise les dropdowns accessibles.
     */
    initAccessibleDropdowns() {
        const dropdownTriggers = document.querySelectorAll('[aria-haspopup="true"]');
        
        dropdownTriggers.forEach(trigger => {
            const dropdown = trigger.nextElementSibling;
            
            if (dropdown && dropdown.classList.contains('navbar-dropdown')) {
                // Gérer l'ouverture/fermeture
                trigger.addEventListener('click', (e) => {
                    e.preventDefault();
                    const isExpanded = trigger.getAttribute('aria-expanded') === 'true';
                    trigger.setAttribute('aria-expanded', !isExpanded);
                    dropdown.classList.toggle('is-active');
                });

                // Gérer le clavier
                trigger.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        trigger.click();
                    } else if (e.key === 'Escape') {
                        trigger.setAttribute('aria-expanded', 'false');
                        dropdown.classList.remove('is-active');
                    }
                });

                // Gérer la navigation dans le dropdown
                const items = dropdown.querySelectorAll('[role="menuitem"]');
                items.forEach((item, index) => {
                    item.addEventListener('keydown', (e) => {
                        if (e.key === 'Escape') {
                            trigger.setAttribute('aria-expanded', 'false');
                            dropdown.classList.remove('is-active');
                            trigger.focus();
                        } else if (e.key === 'ArrowDown') {
                            e.preventDefault();
                            const nextIndex = (index + 1) % items.length;
                            items[nextIndex].focus();
                        } else if (e.key === 'ArrowUp') {
                            e.preventDefault();
                            const prevIndex = (index - 1 + items.length) % items.length;
                            items[prevIndex].focus();
                        }
                    });
                });
            }
        });
    }

    /**
     * Initialise les notifications accessibles.
     */
    initAccessibleNotifications() {
        // Les notifications existantes sont déjà marquées avec role="alert"
        // dans le template base.html
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

        // Annoncer le changement de thème aux lecteurs d'écran
        this.announceThemeChange(theme);
    }

    /**
     * Annonce le changement de thème aux lecteurs d'écran.
     * @param {string} theme - 'dark' ou 'light'
     */
    announceThemeChange(theme) {
        const liveRegion = document.createElement('div');
        liveRegion.setAttribute('aria-live', 'polite');
        liveRegion.setAttribute('aria-atomic', 'true');
        liveRegion.className = 'is-sr-only';
        liveRegion.textContent = `Thème changé vers ${theme === 'dark' ? 'sombre' : 'clair'}`;
        
        document.body.appendChild(liveRegion);
        
        // Supprimer après l'annonce
        setTimeout(() => {
            liveRegion.remove();
        }, 1000);
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
 * Affiche une notification accessible.
 * @param {string} message - Message à afficher
 * @param {string} type - Type de notification (success, danger, warning, info)
 */
function showNotification(message, type = 'info') {
    // Créer un conteneur pour les notifications s'il n'existe pas
    let container = document.getElementById('notification-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'notification-container';
        container.setAttribute('aria-live', 'polite');
        container.setAttribute('aria-atomic', 'true');
        container.style.position = 'fixed';
        container.style.top = '20px';
        container.style.right = '20px';
        container.style.zIndex = '1000';
        container.style.maxWidth = '400px';
        container.style.display = 'flex';
        container.style.flexDirection = 'column';
        container.style.gap = '0.5rem';
        document.body.appendChild(container);
    }
    
    const notification = document.createElement('div');
    notification.className = `notification is-${type}`;
    notification.textContent = message;
    notification.setAttribute('role', 'alert');
    notification.setAttribute('aria-live', 'assertive');
    notification.style.maxWidth = '400px';
    
    container.appendChild(notification);
    
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

/**
 * Affiche une confirmation accessible avec focus.
 * @param {string} message - Message de confirmation
 * @param {Function} onConfirm - Callback si confirmé
 * @param {Function} onCancel - Callback si annulé
 */
function confirmActionAccessible(message, onConfirm, onCancel) {
    // Créer un modal de confirmation
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.setAttribute('role', 'dialog');
    modal.setAttribute('aria-labelledby', 'confirmation-title');
    modal.setAttribute('aria-modal', 'true');
    
    modal.innerHTML = `
        <div class="modal-background"></div>
        <div class="modal-card">
            <header class="modal-card-head">
                <p class="modal-card-title" id="confirmation-title">Confirmation</p>
                <button class="delete close-modal" aria-label="Fermer"></button>
            </header>
            <section class="modal-card-body">
                <p>${message}</p>
            </section>
            <footer class="modal-card-foot">
                <button class="button is-primary confirm-btn">Confirmer</button>
                <button class="button close-modal">Annuler</button>
            </footer>
        </div>
    `;
    
    document.body.appendChild(modal);
    modal.classList.add('is-active');
    
    // Focus sur le bouton confirmer
    const confirmBtn = modal.querySelector('.confirm-btn');
    confirmBtn.focus();
    
    // Gérer les boutons
    modal.querySelectorAll('.close-modal').forEach(btn => {
        btn.addEventListener('click', () => {
            modal.remove();
            if (onCancel) onCancel();
        });
    });
    
    confirmBtn.addEventListener('click', () => {
        modal.remove();
        if (onConfirm) onConfirm();
    });
    
    // Gérer le clavier
    modal.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            modal.remove();
            if (onCancel) onCancel();
        } else if (e.key === 'Enter' && document.activeElement === confirmBtn) {
            modal.remove();
            if (onConfirm) onConfirm();
        }
    });
    
    // Empêcher la navigation en arrière
    modal.querySelector('.modal-background').addEventListener('click', () => {
        modal.remove();
        if (onCancel) onCancel();
    });
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
        const isHidden = el.style.display === 'none';
        el.style.display = isHidden ? '' : 'none';
        
        // Mettre à jour aria-hidden
        el.setAttribute('aria-hidden', isHidden ? 'false' : 'true');
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
        el.setAttribute('aria-hidden', 'false');
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
        el.setAttribute('aria-hidden', 'true');
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
// ACCESSIBILITÉ - FONCTIONS UTILITAIRES
// ============================================

/**
 * Annonce un message aux lecteurs d'écran.
 * @param {string} message - Message à annoncer
 * @param {string} politeness - 'polite' ou 'assertive'
 */
function announceToScreenReader(message, politeness = 'polite') {
    let liveRegion = document.getElementById('sr-announcer');
    
    if (!liveRegion) {
        liveRegion = document.createElement('div');
        liveRegion.id = 'sr-announcer';
        liveRegion.setAttribute('aria-live', politeness);
        liveRegion.setAttribute('aria-atomic', 'true');
        liveRegion.className = 'is-sr-only';
        document.body.appendChild(liveRegion);
    }
    
    // Vider et mettre à jour le contenu
    liveRegion.textContent = '';
    
    // Utiliser setTimeout pour s'assurer que le DOM est mis à jour
    setTimeout(() => {
        liveRegion.textContent = message;
    }, 50);
}

/**
 * Vérifie si un élément est visible à l'écran.
 * @param {HTMLElement} element - Élément à vérifier
 * @returns {boolean} True si visible
 */
function isElementVisible(element) {
    if (!element) return false;
    
    const style = window.getComputedStyle(element);
    if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') {
        return false;
    }
    
    const rect = element.getBoundingClientRect();
    return rect.width > 0 && rect.height > 0;
}

/**
 * Focus sur un élément avec gestion du focus visible.
 * @param {string|HTMLElement} element - Élément ou sélecteur
 */
function focusElement(element) {
    const el = typeof element === 'string' ? document.querySelector(element) : element;
    if (el && isElementVisible(el)) {
        el.focus();
        
        // Pour les éléments qui ne sont pas naturellement focusables
        if (!el.hasAttribute('tabindex')) {
            el.setAttribute('tabindex', '-1');
        }
    }
}

/**
 * Gère la navigation au clavier dans une liste.
 * @param {string} containerSelector - Sélecteur du conteneur
 * @param {string} itemSelector - Sélecteur des éléments
 */
function setupKeyboardNavigation(containerSelector, itemSelector) {
    const container = document.querySelector(containerSelector);
    if (!container) return;
    
    const items = container.querySelectorAll(itemSelector);
    
    items.forEach((item, index) => {
        item.addEventListener('keydown', (e) => {
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                const nextIndex = (index + 1) % items.length;
                focusElement(items[nextIndex]);
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                const prevIndex = (index - 1 + items.length) % items.length;
                focusElement(items[prevIndex]);
            } else if (e.key === 'Home') {
                e.preventDefault();
                focusElement(items[0]);
            } else if (e.key === 'End') {
                e.preventDefault();
                focusElement(items[items.length - 1]);
            }
        });
    });
}

// ============================================
// ACCESSIBILITÉ - GESTION DES ERREURS DE FORMULAIRE
// ============================================

/**
 * Affiche les erreurs de formulaire de manière accessible.
 * @param {Object} errors - Objet contenant les erreurs par champ
 */
function displayFormErrorsAccessible(errors) {
    // Créer une région live pour les erreurs
    let errorRegion = document.getElementById('form-error-region');
    
    if (!errorRegion) {
        errorRegion = document.createElement('div');
        errorRegion.id = 'form-error-region';
        errorRegion.setAttribute('aria-live', 'assertive');
        errorRegion.setAttribute('aria-atomic', 'true');
        errorRegion.className = 'notification is-danger is-sr-only';
        document.body.appendChild(errorRegion);
    }
    
    // Construire le message d'erreur
    const errorMessages = [];
    for (const [field, message] of Object.entries(errors)) {
        errorMessages.push(`${field}: ${message}`);
    }
    
    errorRegion.textContent = errorMessages.join('. ');
    
    // Supprimer après 5 secondes
    setTimeout(() => {
        errorRegion.textContent = '';
    }, 5000);
}

/**
 * Valide un formulaire et affiche les erreurs de manière accessible.
 * @param {HTMLFormElement} form - Formulaire à valider
 * @returns {boolean} True si valide
 */
function validateFormAccessible(form) {
    let isValid = true;
    const errors = {};
    
    // Vérifier les champs requis
    const requiredFields = form.querySelectorAll('[required]');
    
    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            const label = form.querySelector(`label[for="${field.id}"]`) || 
                         field.previousElementSibling;
            const fieldName = label ? label.textContent : field.name;
            errors[fieldName] = 'Ce champ est obligatoire';
            isValid = false;
        }
    });
    
    if (!isValid) {
        displayFormErrorsAccessible(errors);
        
        // Focus sur le premier champ invalide
        const firstInvalid = form.querySelector('[required]:invalid');
        if (firstInvalid) {
            focusElement(firstInvalid);
        }
    }
    
    return isValid;
}

// ============================================
// ACCESSIBILITÉ - GESTION DES TABLEAUX
// ============================================

/**
 * Rend un tableau accessible avec des en-têtes associés.
 * @param {string} tableSelector - Sélecteur du tableau
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

// ============================================
// INITIALISATION GLOBALE DE L'ACCESSIBILITÉ
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    // Initialiser le gestionnaire de thème (déjà fait dans ThemeManager.init)
    
    // Ajouter des attributs ARIA de base
    const html = document.documentElement;
    if (!html.hasAttribute('lang')) {
        html.setAttribute('lang', 'fr');
    }
    
    // S'assurer que le body a un rôle
    const body = document.body;
    if (!body.hasAttribute('role')) {
        body.setAttribute('role', 'document');
    }
    
    // Gérer les liens externes
    const externalLinks = document.querySelectorAll('a[href^="http"]:not([href*="' + window.location.host + '"])');
    externalLinks.forEach(link => {
        if (!link.hasAttribute('aria-label') && !link.hasAttribute('title')) {
            const label = link.textContent.trim();
            link.setAttribute('aria-label', `${label} (lien externe)`);
        }
        link.setAttribute('rel', 'noopener noreferrer');
        link.setAttribute('target', '_blank');
    });
    
    // Gérer les images sans alt
    const images = document.querySelectorAll('img:not([alt])');
    images.forEach(img => {
        // Si c'est une image décorative (via classe ou parent)
        if (img.classList.contains('is-decorative') || 
            img.parentElement.classList.contains('is-decorative')) {
            img.setAttribute('alt', '');
            img.setAttribute('aria-hidden', 'true');
        } else {
            // Sinon, ajouter un alt générique (à améliorer)
            img.setAttribute('alt', 'Image');
        }
    });
    
    // Gérer les boutons sans type
    const buttons = document.querySelectorAll('button:not([type])');
    buttons.forEach(button => {
        button.setAttribute('type', 'button');
    });
    
    // Gérer les formulaires
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        if (!form.hasAttribute('novalidate')) {
            form.setAttribute('novalidate', '');
        }
        
        // Ajouter aria-live pour les messages de validation
        if (!form.querySelector('[aria-live]')) {
            const liveRegion = document.createElement('div');
            liveRegion.setAttribute('aria-live', 'polite');
            liveRegion.setAttribute('aria-atomic', 'true');
            liveRegion.className = 'is-sr-only';
            form.appendChild(liveRegion);
        }
    });
});

// ============================================
// GESTION DES ÉVÉNEMENTS GLOBAUX
// ============================================

// Gérer les erreurs JavaScript de manière accessible
window.addEventListener('error', (e) => {
    console.error('Erreur JavaScript:', e.error);
    announceToScreenReader('Une erreur est survenue. Veuillez actualiser la page.');
});

// Gérer les changements de taille de la fenêtre pour le responsive
window.addEventListener('resize', () => {
    // Peut être utilisé pour ajuster l'UI en fonction de la taille
});

// Gérer le focus visible pour tous les éléments
window.addEventListener('keydown', (e) => {
    if (e.key === 'Tab') {
        document.body.classList.add('keyboard-navigation');
    }
});

window.addEventListener('mousedown', () => {
    document.body.classList.remove('keyboard-navigation');
});
