/**
 * Flash messages (base.html): manual dismissal (button) and automatic
 * dismissal after a delay (data-auto-dismiss, ms).
 */
import { getString } from '../utils/i18n.js';

function dismiss(alertEl) {
    if (!alertEl || alertEl.dataset.dismissed) {
        return;
    }
    alertEl.dataset.dismissed = 'true';
    alertEl.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
    alertEl.style.opacity = '0';
    alertEl.style.transform = 'translateY(-8px)';
    setTimeout(() => alertEl.remove(), 300);
}

// Wires dismissal (close button + auto-dismiss timer) onto one
// `.flash-message` element - shared by both server-rendered messages
// (initFlashMessages, on page load) and client-side ones
// (showFlashMessage, appended later by AJAX call sites).
function wireDismissal(alertEl) {
    const closeButton = alertEl.querySelector('.flash-message-close');
    if (closeButton) {
        closeButton.addEventListener('click', () => dismiss(alertEl));
    }

    const delay = parseInt(alertEl.dataset.autoDismiss, 10);
    if (delay > 0) {
        const timer = setTimeout(() => dismiss(alertEl), delay);
        // Give the user time to read if they're hovering/focusing the message.
        alertEl.addEventListener('mouseenter', () => clearTimeout(timer));
        alertEl.addEventListener('focusin', () => clearTimeout(timer));
    }
}

export function initFlashMessages() {
    document.querySelectorAll('.flash-message').forEach(wireDismissal);
}

const FLASH_TYPE_BY_CATEGORY = {
    danger: 'error',
    success: 'success',
    warning: 'warning',
    info: 'info',
};

const FLASH_ICON_BY_TYPE = {
    error: 'fa-circle-exclamation',
    success: 'fa-circle-check',
    warning: 'fa-triangle-exclamation',
    info: 'fa-circle-info',
};

// Appends a visible flash message identical in markup/behavior to a
// server-rendered one (base.html) - for AJAX call sites (the calendar's
// shift/on-call create/update/delete actions) that have no full-page
// reload to carry a server-side flash() through. Real production bug:
// these call sites only ever announced outcomes to screen readers
// (announceToScreenReader, an invisible aria-live region) - a sighted
// admin got no visible confirmation of success, and no visible error
// message at all on failure.
export function showFlashMessage(message, category = 'info') {
    const container = document.getElementById('flash-messages');
    if (!container) return;

    const flashType = FLASH_TYPE_BY_CATEGORY[category] || category;
    const icon = FLASH_ICON_BY_TYPE[flashType] || 'fa-circle-info';

    const alertEl = document.createElement('div');
    alertEl.className = `alert alert-${flashType} mb-2 flash-message`;
    alertEl.setAttribute('role', 'alert');
    alertEl.setAttribute('aria-live', 'assertive');
    alertEl.dataset.autoDismiss = '6000';
    alertEl.innerHTML = `
        <i class="fas ${icon}" aria-hidden="true"></i>
        <span></span>
        <button type="button" class="btn btn-ghost btn-xs btn-circle ml-auto flash-message-close" aria-label="${getString('close_notification')}">
            <i class="fas fa-xmark" aria-hidden="true"></i>
        </button>
    `;
    // The message itself goes through textContent, never innerHTML -
    // unlike the icon/button markup above (static, no user data), this
    // can carry a server-provided error string.
    alertEl.querySelector('span').textContent = message;

    container.appendChild(alertEl);
    wireDismissal(alertEl);
}
