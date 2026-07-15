/**
 * Small DOM manipulation helpers (accept a CSS selector or an element).
 */

/**
 * Toggle an element's visibility.
 * @param {string|HTMLElement} element - Element or selector
 */
export function toggleVisibility(element) {
    const el = typeof element === 'string' ? document.querySelector(element) : element;
    if (el) {
        el.style.display = el.style.display === 'none' ? '' : 'none';
    }
}

/**
 * Show an element.
 * @param {string|HTMLElement} element - Element or selector
 */
export function showElement(element) {
    const el = typeof element === 'string' ? document.querySelector(element) : element;
    if (el) {
        el.style.display = '';
    }
}

/**
 * Hide an element.
 * @param {string|HTMLElement} element - Element or selector
 */
export function hideElement(element) {
    const el = typeof element === 'string' ? document.querySelector(element) : element;
    if (el) {
        el.style.display = 'none';
    }
}

/**
 * Add a class to an element.
 * @param {string|HTMLElement} element - Element or selector
 * @param {string} className - Class to add
 */
export function addClass(element, className) {
    const el = typeof element === 'string' ? document.querySelector(element) : element;
    if (el) {
        el.classList.add(className);
    }
}

/**
 * Remove a class from an element.
 * @param {string|HTMLElement} element - Element or selector
 * @param {string} className - Class to remove
 */
export function removeClass(element, className) {
    const el = typeof element === 'string' ? document.querySelector(element) : element;
    if (el) {
        el.classList.remove(className);
    }
}

/**
 * Toggle a class on an element.
 * @param {string|HTMLElement} element - Element or selector
 * @param {string} className - Class to toggle
 */
export function toggleClass(element, className) {
    const el = typeof element === 'string' ? document.querySelector(element) : element;
    if (el) {
        el.classList.toggle(className);
    }
}
