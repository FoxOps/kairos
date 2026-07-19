/**
 * Kairos - JavaScript entry point
 * =============================================
 *
 * Loads the app's ES6 modules and exposes `window.Kairos` for the
 * templates' inline event handlers (onclick=...) and the FullCalendar
 * callbacks.
 */

import { ThemeManager } from './theme/theme-manager.js';
import { NavbarMenu } from './navbar/navbar-menu.js';
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
import { initDatePickers } from './utils/date-picker.js';

let themeManager;
let navbarMenu;
document.addEventListener('DOMContentLoaded', () => {
    themeManager = new ThemeManager();
    navbarMenu = new NavbarMenu();
    initFlashMessages();
    initConfirmDeleteActions();
    // Replaces every native <input type="date">/<input type="datetime-local">
    // present at page load with the Vanilla Calendar Pro popup - see
    // date-picker.js. Inputs created later (e.g. the dynamically-built
    // shift-creation modal in fullcalendar-config.js) bind themselves
    // separately, since they don't exist yet at this point.
    initDatePickers();
});

// Export functions for the templates (inline onclick, FullCalendar callbacks)
window.Kairos = {
    ThemeManager,
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
