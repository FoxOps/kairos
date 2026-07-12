/**
 * Glisser-déposer pour réordonner la liste de rotation d'astreinte
 * (app/templates/admin/automation/full.html).
 *
 * Externalisé depuis un <script> inline (CSP script-src 'self' stricte
 * bloquait silencieusement tout ce fichier - le drag & drop et le bouton
 * "Sauvegarder l'ordre" étaient cassés en production). saveRotationOrder()
 * était en plus définie à l'intérieur du listener DOMContentLoaded, donc
 * inaccessible à onclick="saveRotationOrder()" même avant la CSP stricte -
 * exposée maintenant via window.Leviia comme les autres callbacks inline.
 */

let sortableList;
let draggedItem = null;

function initRotationOrder() {
    sortableList = document.getElementById('rotation-order-list');
    if (!sortableList) return;

    sortableList.addEventListener('dragstart', (e) => {
        if (e.target.classList.contains('sortable-item')) {
            draggedItem = e.target;
            e.target.classList.add('dragging');
            e.dataTransfer.effectAllowed = 'move';
            e.dataTransfer.setData('text/html', e.target.innerHTML);
        }
    });

    sortableList.addEventListener('dragend', (e) => {
        if (e.target.classList.contains('sortable-item')) {
            e.target.classList.remove('dragging');
            draggedItem = null;
        }
    });

    sortableList.addEventListener('dragover', (e) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';

        const targetItem = e.target.closest('.sortable-item');
        if (targetItem && targetItem !== draggedItem) {
            const rect = targetItem.getBoundingClientRect();
            const next = (e.clientY - rect.top) / (rect.bottom - rect.top) > 0.5;

            if (next) {
                sortableList.insertBefore(draggedItem, targetItem.nextSibling);
            } else {
                sortableList.insertBefore(draggedItem, targetItem);
            }
        }
    });

    sortableList.addEventListener('dragenter', (e) => {
        e.preventDefault();
    });

    sortableList.addEventListener('drop', (e) => {
        e.preventDefault();
    });

    // Mettre à jour les positions cachées avant soumission
    document.querySelector('form').addEventListener('submit', () => {
        const items = sortableList.querySelectorAll('.sortable-item');
        items.forEach((item, index) => {
            const userId = item.dataset.userId;
            const positionInput = document.querySelector(`input[name="rotation_order_${userId}"]`);
            if (positionInput) {
                positionInput.value = index + 1;
            }
        });
    });
}

export function saveRotationOrder() {
    const form = document.querySelector('form');
    const items = sortableList.querySelectorAll('.sortable-item');

    items.forEach((item, index) => {
        const userId = item.dataset.userId;
        const positionInput = form.querySelector(`input[name="rotation_order_${userId}"]`);
        if (positionInput) {
            positionInput.value = index + 1;
        }
    });

    const actionInput = document.createElement('input');
    actionInput.type = 'hidden';
    actionInput.name = 'action';
    actionInput.value = 'save_order';
    form.appendChild(actionInput);

    form.submit();
}

document.addEventListener('DOMContentLoaded', initRotationOrder);
