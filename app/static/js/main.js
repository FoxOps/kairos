/**
 * Leviia Schedule - Point d'entrée JavaScript
 * =============================================
 *
 * Charge les modules ES6 de l'application et expose `window.Leviia`
 * pour les gestionnaires d'événements inline des templates (onclick=...)
 * et les callbacks FullCalendar.
 */

import { ThemeManager } from './theme/theme-manager.js';
import { formatDate, formatTime, formatDateTime } from './utils/date.js';
import {
    toggleVisibility,
    showElement,
    hideElement,
    addClass,
    removeClass,
    toggleClass,
} from './utils/dom.js';
import {
    announceToScreenReader,
    focusElement,
    setupKeyboardNavigation,
    displayFormErrorsAccessible,
    validateFormAccessible,
    makeTableAccessible,
    confirmActionAccessible,
} from './utils/accessibility.js';
import { showNotification, confirmAction } from './notifications/toast.js';

let themeManager;
document.addEventListener('DOMContentLoaded', () => {
    themeManager = new ThemeManager();
});

// Exporter les fonctions pour les templates (onclick inline, callbacks FullCalendar)
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
