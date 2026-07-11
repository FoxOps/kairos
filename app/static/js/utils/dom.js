/**
 * Petits helpers de manipulation du DOM (accepte sélecteur CSS ou élément).
 */

/**
 * Toggle la visibilité d'un élément.
 * @param {string|HTMLElement} element - Élément ou sélecteur
 */
export function toggleVisibility(element) {
    const el = typeof element === 'string' ? document.querySelector(element) : element;
    if (el) {
        el.style.display = el.style.display === 'none' ? '' : 'none';
    }
}

/**
 * Affiche un élément.
 * @param {string|HTMLElement} element - Élément ou sélecteur
 */
export function showElement(element) {
    const el = typeof element === 'string' ? document.querySelector(element) : element;
    if (el) {
        el.style.display = '';
    }
}

/**
 * Masque un élément.
 * @param {string|HTMLElement} element - Élément ou sélecteur
 */
export function hideElement(element) {
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
export function addClass(element, className) {
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
export function removeClass(element, className) {
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
export function toggleClass(element, className) {
    const el = typeof element === 'string' ? document.querySelector(element) : element;
    if (el) {
        el.classList.toggle(className);
    }
}
