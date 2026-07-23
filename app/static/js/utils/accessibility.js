/**
 * Shared accessibility helpers (screen-reader announcements, focus,
 * keyboard navigation, form validation, confirmation modal).
 */
import { getString } from './i18n.js';

/**
 * Announce a message to screen readers.
 * @param {string} message - Message to announce
 * @param {string} politeness - Politeness level ('polite' or 'assertive')
 */
export function announceToScreenReader(message, politeness = 'polite') {
    const liveRegion = document.getElementById('aria-live-region') || createLiveRegion(politeness);
    liveRegion.textContent = message;

    // Reset after the announcement so repeated announcements are picked up
    setTimeout(() => {
        liveRegion.textContent = '';
    }, 1000);
}

/**
 * Create a live region for screen-reader announcements.
 * @param {string} politeness - Politeness level ('polite' or 'assertive')
 * @returns {HTMLElement} The created live region
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
 * Focus an element.
 * @param {HTMLElement|string} element - Element or CSS selector
 */
export function focusElement(element) {
    const el = typeof element === 'string' ? document.querySelector(element) : element;
    if (el && el.focus) {
        el.focus();
        // Add a visible focus style for browsers that don't support :focus-visible
        el.style.outline = '3px solid #00d1b2';
        el.style.outlineOffset = '2px';
    }
}

/**
 * Confirm an action with the user accessibly.
 * @param {string} message - Confirmation message
 * @param {Function} onConfirm - Function to run if the user confirms
 * @param {Function} onCancel - Function to run if the user cancels
 */
export function confirmActionAccessible(message, onConfirm, onCancel) {
    // Build an accessible modal
    const modal = document.createElement('div');
    modal.className = 'modal modal-open';
    modal.setAttribute('role', 'dialog');
    modal.setAttribute('aria-modal', 'true');
    modal.setAttribute('aria-labelledby', 'confirmation-title');

    // Only static markup lives in innerHTML: the message (which may be
    // derived from user data such as a name) is injected afterwards via
    // textContent, never interpolated directly into the HTML (XSS
    // protection - a name containing HTML/JS must never be able to
    // execute here).
    modal.innerHTML = `
        <div class="modal-box">
            <div class="flex items-start justify-between">
                <h2 id="confirmation-title" class="text-lg font-bold">${getString('confirmation_title')}</h2>
                <button class="btn btn-sm btn-circle btn-ghost" aria-label="${getString('close')}" role="button">&times;</button>
            </div>
            <p class="py-4"></p>
            <div class="modal-action">
                <button class="btn" aria-label="${getString('cancel')}" role="button">${getString('cancel')}</button>
                <button class="btn btn-primary" aria-label="${getString('confirm')}" role="button">${getString('confirm')}</button>
            </div>
        </div>
        <div class="modal-backdrop" role="button" tabindex="0" aria-label="${getString('close')}"></div>
    `;
    modal.querySelector('p.py-4').textContent = message;

    document.body.appendChild(modal);

    // Focus the Confirm button
    const confirmBtn = modal.querySelector('.btn-primary');
    const cancelBtn = modal.querySelector('.modal-action .btn:not(.btn-primary)');
    const closeBtn = modal.querySelector('.btn-circle');
    const background = modal.querySelector('.modal-backdrop');

    focusElement(confirmBtn);

    // Wire up event handlers
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

    // Handle keyboard navigation
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

    // Trap focus within the modal
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

/**
 * Wire up accessible delete confirmation for every button/link tagged
 * `.js-confirm-delete`, through a single delegated listener (instead of a
 * per-element inline onclick attribute).
 *
 * The message comes from the `data-confirm-message` attribute, never
 * interpolated directly into executable template-side HTML/JS - it goes
 * through the DOM (an HTML attribute escaped by Jinja, read via
 * `.dataset`), not a server-built JS string. Combined with
 * confirmActionAccessible() (which inserts the message via textContent), a
 * user value such as a name can never break out of its data context to
 * execute.
 */
export function initConfirmDeleteActions() {
    document.addEventListener('click', (event) => {
        const trigger = event.target.closest('.js-confirm-delete');
        if (!trigger) return;

        event.preventDefault();
        const message = trigger.dataset.confirmMessage || getString('are_you_sure');

        if (trigger.tagName === 'BUTTON') {
            const form = trigger.form;
            confirmActionAccessible(message, () => form.submit());
        } else {
            const href = trigger.href;
            confirmActionAccessible(message, () => {
                window.location.href = href;
            });
        }
    });
}
