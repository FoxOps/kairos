/**
 * Notifications éphémères (toasts) et confirmation navigateur simple.
 */

/**
 * Affiche une notification.
 * @param {string} message - Message à afficher
 * @param {string} type - Type de notification (success, danger, warning, info)
 */
export function showNotification(message, type = 'info') {
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
export function confirmAction(message) {
    return confirm(message);
}
