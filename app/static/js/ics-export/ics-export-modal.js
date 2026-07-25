/**
 * ICS export modal (app/templates/_ics_export_buttons.html) - the
 * modal itself is a server-rendered daisyUI checkbox-toggle modal (no
 * dynamic content, unlike the JS-built shift-creation modal in
 * calendar/fullcalendar-config.js), so this file only covers what a
 * checkbox-toggle modal can't do on its own: closing on "Télécharger"
 * and on Escape (a native <dialog> gets both for free via
 * showModal()/close(); a checkbox has no equivalent).
 */

export function closeIcsModal(modalId) {
    const checkbox = document.getElementById(modalId);
    if (checkbox) {
        checkbox.checked = false;
    }
}

export function initIcsModalEscapeHandling() {
    document.addEventListener('keydown', (event) => {
        if (event.key !== 'Escape') {
            return;
        }
        document.querySelectorAll('.ics-modal-toggle:checked').forEach((checkbox) => {
            checkbox.checked = false;
        });
    });
}
