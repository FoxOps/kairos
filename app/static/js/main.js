/**
 * Leviia Schedule - JavaScript entry point
 * =============================================
 *
 * Loads the app's ES6 modules and exposes `window.Leviia` for the
 * templates' inline event handlers (onclick=...) and the FullCalendar
 * callbacks.
 */

import { ThemeManager } from './theme/theme-manager.js';
import { NavbarMenu } from './navbar/navbar-menu.js';
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
    initConfirmDeleteActions,
} from './utils/accessibility.js';
import { showNotification, confirmAction } from './notifications/toast.js';
import { initFlashMessages } from './notifications/flash-messages.js';
import {
    copyToken,
    copyUrlShiftsAll,
    copyUrlShiftsMy,
    copyUrlOncallAll,
    copyUrlOncallMy,
    copyUrlLeavesAll,
    copyUrlLeavesMy,
} from './clipboard/copy-token.js';
import { saveRotationOrder } from './automation/rotation-order.js';

let themeManager;
let navbarMenu;
document.addEventListener('DOMContentLoaded', () => {
    themeManager = new ThemeManager();
    navbarMenu = new NavbarMenu();
    initFlashMessages();
    initConfirmDeleteActions();
});

// Export functions for the templates (inline onclick, FullCalendar callbacks)
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
    copyToken,
    copyUrlShiftsAll,
    copyUrlShiftsMy,
    copyUrlOncallAll,
    copyUrlOncallMy,
    copyUrlLeavesAll,
    copyUrlLeavesMy,
    saveRotationOrder,
    // ThemeManager instance (initialized on load)
    get themeManager() {
        return themeManager;
    }
};
