/**
 * Ephemeral notifications (toasts) and simple browser confirmation.
 */

/**
 * Show a notification.
 * @param {string} message - Message to display
 * @param {string} type - Notification type (success, danger, warning, info)
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

    // Remove after 5 seconds
    setTimeout(() => {
        notification.classList.add('is-hidden');
        setTimeout(() => notification.remove(), 500);
    }, 5000);
}

/**
 * Confirm an action with the user.
 * @param {string} message - Confirmation message
 * @returns {boolean} True if confirmed
 */
export function confirmAction(message) {
    return confirm(message);
}
