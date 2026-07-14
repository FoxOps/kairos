/**
 * Fonctions d'accessibilité partagées (annonces lecteur d'écran, focus,
 * navigation clavier, validation de formulaire, modale de confirmation).
 */

/**
 * Annonce un message aux lecteurs d'écran.
 * @param {string} message - Message à annoncer
 * @param {string} politeness - Niveau de politesse ('polite' ou 'assertive')
 */
export function announceToScreenReader(message, politeness = 'polite') {
    const liveRegion = document.getElementById('aria-live-region') || createLiveRegion(politeness);
    liveRegion.textContent = message;

    // Réinitialiser après l'annonce pour permettre des annonces répétées
    setTimeout(() => {
        liveRegion.textContent = '';
    }, 1000);
}

/**
 * Crée une région live pour les annonces aux lecteurs d'écran.
 * @param {string} politeness - Niveau de politesse ('polite' ou 'assertive')
 * @returns {HTMLElement} La région live créée
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
 * Met le focus sur un élément.
 * @param {HTMLElement|string} element - Élément ou sélecteur CSS
 */
export function focusElement(element) {
    const el = typeof element === 'string' ? document.querySelector(element) : element;
    if (el && el.focus) {
        el.focus();
        // Ajouter un style de focus visible pour les navigateurs qui ne gèrent pas :focus-visible
        el.style.outline = '3px solid #00d1b2';
        el.style.outlineOffset = '2px';
    }
}

/**
 * Configure la navigation au clavier pour une liste d'éléments.
 * @param {HTMLElement|string} container - Conteneur ou sélecteur CSS
 * @param {string} itemSelector - Sélecteur CSS pour les éléments de la liste
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
 * Affiche les erreurs de formulaire de manière accessible.
 * @param {Object} errors - Objet contenant les erreurs (ex: { field1: 'Erreur 1', field2: 'Erreur 2' })
 */
export function displayFormErrorsAccessible(errors) {
    // Annoncer le nombre d'erreurs
    const errorCount = Object.keys(errors).length;
    const errorMessage = errorCount === 1
        ? '1 erreur de formulaire. Veuillez la corriger.'
        : `${errorCount} erreurs de formulaire. Veuillez les corriger.`;
    announceToScreenReader(errorMessage, 'assertive');

    // Mettre le focus sur le premier champ en erreur
    const firstErrorField = document.querySelector(`[name="${Object.keys(errors)[0]}"]`);
    if (firstErrorField) {
        focusElement(firstErrorField);
    }
}

/**
 * Valide un formulaire de manière accessible.
 * @param {HTMLElement|string} form - Formulaire ou sélecteur CSS
 * @returns {boolean} True si le formulaire est valide
 */
export function validateFormAccessible(form) {
    const formEl = typeof form === 'string' ? document.querySelector(form) : form;
    if (!formEl) return false;

    let isValid = true;
    const errors = {};

    // Valider les champs requis
    const requiredFields = formEl.querySelectorAll('[required]');
    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            isValid = false;
            const fieldName = field.getAttribute('aria-label') ||
                             field.getAttribute('name') ||
                             field.getAttribute('id') ||
                             'Champ non nommé';
            errors[field.name || field.id] = `Le champ ${fieldName} est obligatoire.`;

            // Ajouter un message d'erreur visible
            let errorEl = field.nextElementSibling;
            if (!errorEl || !errorEl.classList.contains('error-message')) {
                errorEl = document.createElement('div');
                errorEl.className = 'help is-danger error-message';
                errorEl.setAttribute('role', 'alert');
                field.parentNode.insertBefore(errorEl, field.nextSibling);
            }
            errorEl.textContent = errors[field.name || field.id];

            // Ajouter une classe d'erreur au champ
            field.classList.add('is-danger');
        } else {
            // Supprimer l'erreur si elle existe
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
 * Rend un tableau accessible.
 * @param {string} tableSelector - Sélecteur CSS pour le tableau
 */
export function makeTableAccessible(tableSelector) {
    const table = document.querySelector(tableSelector);
    if (!table) return;

    // Ajouter scope aux en-têtes
    const headers = table.querySelectorAll('th');
    headers.forEach(header => {
        if (!header.hasAttribute('scope')) {
            header.setAttribute('scope', 'col');
        }
    });

    // Ajouter scope aux cellules d'en-tête de ligne
    const rowHeaders = table.querySelectorAll('td[role="rowheader"]');
    rowHeaders.forEach(header => {
        if (!header.hasAttribute('scope')) {
            header.setAttribute('scope', 'row');
        }
    });

    // Ajouter une légende si elle n'existe pas
    if (!table.querySelector('caption')) {
        const caption = document.createElement('caption');
        caption.className = 'is-sr-only';
        caption.textContent = 'Tableau de données';
        table.insertBefore(caption, table.firstChild);
    }
}

/**
 * Confirme une action avec l'utilisateur de manière accessible.
 * @param {string} message - Message de confirmation
 * @param {Function} onConfirm - Fonction à exécuter si l'utilisateur confirme
 * @param {Function} onCancel - Fonction à exécuter si l'utilisateur annule
 */
export function confirmActionAccessible(message, onConfirm, onCancel) {
    // Créer une modale accessible
    const modal = document.createElement('div');
    modal.className = 'modal modal-open';
    modal.setAttribute('role', 'dialog');
    modal.setAttribute('aria-modal', 'true');
    modal.setAttribute('aria-labelledby', 'confirmation-title');

    // Structure statique uniquement dans innerHTML : le message (potentiellement
    // dérivé de données utilisateur comme un nom) est injecté ensuite via
    // textContent, jamais interpolé directement dans le HTML (protection XSS -
    // un nom contenant du HTML/JS ne doit jamais pouvoir s'exécuter ici).
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

    // Mettre le focus sur le bouton Confirmer
    const confirmBtn = modal.querySelector('.btn-primary');
    const cancelBtn = modal.querySelector('.modal-action .btn:not(.btn-primary)');
    const closeBtn = modal.querySelector('.btn-circle');
    const background = modal.querySelector('.modal-backdrop');

    focusElement(confirmBtn);

    // Gérer les événements
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

    // Gérer la navigation au clavier
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

    // Piège de focus dans la modale
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
 * Câble la confirmation accessible pour tous les boutons/liens de suppression
 * marqués `.js-confirm-delete`, via un seul listener délégué (plutôt que des
 * attributs onclick inline par élément).
 *
 * Le message vient de l'attribut `data-confirm-message`, jamais interpolé
 * directement dans du HTML/JS exécutable côté template - il transite par le
 * DOM (attribut HTML échappé par Jinja, lu via `.dataset`), pas par une
 * chaîne JS construite côté serveur. Combiné à confirmActionAccessible()
 * (qui insère le message via textContent), une valeur utilisateur comme un
 * nom ne peut jamais casser hors de son contexte de données pour s'exécuter.
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
