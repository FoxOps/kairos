/**
 * Drag & drop to reorder the on-call rotation list
 * (app/templates/admin/automation/full.html).
 *
 * This file was extracted from an inline <script>: a strict
 * `script-src 'self'` CSP silently blocked the whole block, breaking the
 * drag & drop and the "Sauvegarder l'ordre" button in production.
 * saveRotationOrder() was also originally defined inside the
 * DOMContentLoaded listener, making it unreachable from
 * onclick="saveRotationOrder()" even before the strict CSP - it's now
 * exposed via window.Leviia like the other inline callbacks.
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

    // Update the hidden position fields before submitting
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

    // Reuse an existing action field if there's one, instead of adding a
    // second - two same-name fields submitted to the server mean Werkzeug's
    // request.form.get("action") (app/routes/admin_automation_routes.py)
    // returns the first one, not this one, so the actually intended action
    // gets silently ignored.
    let actionInput = form.querySelector('input[name="action"]');
    if (!actionInput) {
        actionInput = document.createElement('input');
        actionInput.type = 'hidden';
        actionInput.name = 'action';
        form.appendChild(actionInput);
    }
    actionInput.value = 'save_order';

    form.submit();
}

document.addEventListener('DOMContentLoaded', initRotationOrder);
