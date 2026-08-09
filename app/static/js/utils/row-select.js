/**
 * Table row-selection for the "delete selection" action on
 * /schedule, /oncall, /leave: a `.js-select-all` header checkbox toggles
 * every `.js-row-select` row checkbox, and the `.js-delete-selected-submit`
 * button is only enabled once at least one row is checked - each page
 * has exactly one of each, so no per-table scoping is needed.
 */
export function initRowSelectCheckboxes() {
    const selectAll = document.querySelector('.js-select-all');
    const submitButton = document.querySelector('.js-delete-selected-submit');

    if (!selectAll || !submitButton) return;

    const rowCheckboxes = () => document.querySelectorAll('.js-row-select');

    function updateSubmitState() {
        const anyChecked = Array.from(rowCheckboxes()).some((checkbox) => checkbox.checked);
        submitButton.disabled = !anyChecked;
    }

    selectAll.addEventListener('change', () => {
        rowCheckboxes().forEach((checkbox) => {
            checkbox.checked = selectAll.checked;
        });
        updateSubmitState();
    });

    document.addEventListener('change', (event) => {
        if (!event.target.classList.contains('js-row-select')) return;

        if (!event.target.checked) {
            selectAll.checked = false;
        } else if (Array.from(rowCheckboxes()).every((checkbox) => checkbox.checked)) {
            selectAll.checked = true;
        }
        updateSubmitState();
    });

    updateSubmitState();
}
