/**
 * Shared accessibility helpers (screen-reader announcements, focus,
 * keyboard navigation, form validation, confirmation modal).
 */

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
 * Set up keyboard navigation for a list of elements.
 * @param {HTMLElement|string} container - Container or CSS selector
 * @param {string} itemSelector - CSS selector for the list items
 */
export function setupKeyboardNavigation(container, itemSelector) {
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
 * Display form errors accessibly.
 * @param {Object} errors - Object containing the errors (e.g. { field1: 'Error 1', field2: 'Error 2' })
 */
export function displayFormErrorsAccessible(errors) {
    // Announce the error count
    const errorCount = Object.keys(errors).length;
    const errorMessage = errorCount === 1
        ? '1 erreur de formulaire. Veuillez la corriger.'
        : `${errorCount} erreurs de formulaire. Veuillez les corriger.`;
    announceToScreenReader(errorMessage, 'assertive');

    // Focus the first field in error
    const firstErrorField = document.querySelector(`[name="${Object.keys(errors)[0]}"]`);
    if (firstErrorField) {
        focusElement(firstErrorField);
    }
}

/**
 * Validate a form accessibly.
 * @param {HTMLElement|string} form - Form or CSS selector
 * @returns {boolean} True if the form is valid
 */
export function validateFormAccessible(form) {
    const formEl = typeof form === 'string' ? document.querySelector(form) : form;
    if (!formEl) return false;

    let isValid = true;
    const errors = {};

    // Validate the required fields
    const requiredFields = formEl.querySelectorAll('[required]');
    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            isValid = false;
            const fieldName = field.getAttribute('aria-label') ||
                             field.getAttribute('name') ||
                             field.getAttribute('id') ||
                             'Champ non nommé';
            errors[field.name || field.id] = `Le champ ${fieldName} est obligatoire.`;

            // Add a visible error message
            let errorEl = field.nextElementSibling;
            if (!errorEl || !errorEl.classList.contains('error-message')) {
                errorEl = document.createElement('div');
                errorEl.className = 'help is-danger error-message';
                errorEl.setAttribute('role', 'alert');
                field.parentNode.insertBefore(errorEl, field.nextSibling);
            }
            errorEl.textContent = errors[field.name || field.id];

            // Add an error class to the field
            field.classList.add('is-danger');
        } else {
            // Remove the error if there is one
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
 * Make a table accessible.
 * @param {string} tableSelector - CSS selector for the table
 */
export function makeTableAccessible(tableSelector) {
    const table = document.querySelector(tableSelector);
    if (!table) return;

    // Add scope to header cells
    const headers = table.querySelectorAll('th');
    headers.forEach(header => {
        if (!header.hasAttribute('scope')) {
            header.setAttribute('scope', 'col');
        }
    });

    // Add scope to row-header cells
    const rowHeaders = table.querySelectorAll('td[role="rowheader"]');
    rowHeaders.forEach(header => {
        if (!header.hasAttribute('scope')) {
            header.setAttribute('scope', 'row');
        }
    });

    // Add a caption if there isn't one already
    if (!table.querySelector('caption')) {
        const caption = document.createElement('caption');
        caption.className = 'is-sr-only';
        caption.textContent = 'Tableau de données';
        table.insertBefore(caption, table.firstChild);
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
                <h2 id="confirmation-title" class="text-lg font-bold">Confirmation</h2>
                <button class="btn btn-sm btn-circle btn-ghost" aria-label="Fermer" role="button">&times;</button>
            </div>
            <p class="py-4"></p>
            <div class="modal-action">
                <button class="btn" aria-label="Annuler" role="button">Annuler</button>
                <button class="btn btn-primary" aria-label="Confirmer" role="button">Confirmer</button>
            </div>
        </div>
        <div class="modal-backdrop" role="button" tabindex="0" aria-label="Fermer"></div>
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
        const message = trigger.dataset.confirmMessage || 'Êtes-vous sûr ?';

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
