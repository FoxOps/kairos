/**
 * Flash messages (base.html): manual dismissal (button) and automatic
 * dismissal after a delay (data-auto-dismiss, ms).
 */

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

export function initFlashMessages() {
    document.querySelectorAll('.flash-message').forEach((alertEl) => {
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
    });
}
