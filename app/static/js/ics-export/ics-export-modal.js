/**
 * ICS export modal (app/templates/_ics_export_buttons.html) - the
 * modal itself is a server-rendered daisyUI checkbox-toggle modal (no
 * dynamic content, unlike the JS-built shift-creation modal in
 * calendar/fullcalendar-config.js), so this file covers what a
 * checkbox-toggle modal can't do on its own: closing on "Télécharger"
 * and on Escape (a native <dialog> gets both for free via
 * showModal()/close(); a checkbox has no equivalent) - plus the
 * group-checkbox/Moi-Tout-toggle interaction and the live recompute of
 * the copyable URL and download link as the viewer changes those.
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

// One .ics-export-modal-root per resource type (shifts/oncall/leaves),
// server-rendered by _ics_export_buttons.html with its own group
// checkboxes, an optional Moi/Tout le monde toggle, a copyable URL
// input and a download link - all scoped under this one root element.
export function initIcsExportGroupScopeControls() {
    document.querySelectorAll('.ics-export-modal-root').forEach((root) => {
        const resourceType = root.dataset.resourceType;
        const baseUrl = root.dataset.baseUrl;
        const token = root.dataset.token;
        const ownGroupId = root.dataset.ownGroupId;

        const checkboxes = root.querySelectorAll('.ics-export-group-checkbox');
        const toggle = root.querySelector('.ics-export-scope-toggle');
        const urlInput = document.getElementById(`${root.id.replace('-root', '')}-input`);
        const downloadLink = document.getElementById(
            `${root.id.replace('-root', '')}-download`
        );

        function checkedGroupIds() {
            return Array.from(checkboxes)
                .filter((cb) => cb.checked)
                .map((cb) => cb.value);
        }

        function update() {
            const groupIds = checkedGroupIds();
            const ownGroupChecked = ownGroupId !== '' && groupIds.includes(ownGroupId);

            if (toggle) {
                toggle.disabled = !ownGroupChecked;
                if (!ownGroupChecked) {
                    // Exporting "Moi" for a group the viewer isn't part
                    // of would silently produce an empty calendar -
                    // force "Tout le monde" instead. Re-checking the
                    // viewer's own group only re-enables the toggle, it
                    // doesn't snap the choice back to "Moi" on its own.
                    toggle.checked = true;
                }
            }
            const scope = toggle && !toggle.checked ? 'my' : 'all';

            // Nothing selected: a group_ids= with zero values is
            // indistinguishable server-side from "no group_ids param at
            // all" (i.e. unfiltered/everyone) - rather than silently
            // producing that surprising result, disable the copy/
            // download actions instead of emitting a misleading URL.
            const nothingSelected = scope === 'all' && groupIds.length === 0;

            let url = `${baseUrl}/export/${resourceType}?scope=${scope}&token=${token}`;
            if (scope === 'all') {
                groupIds.forEach((id) => {
                    url += `&group_ids=${id}`;
                });
            }

            if (urlInput) {
                urlInput.value = nothingSelected ? '' : url;
            }
            if (downloadLink) {
                if (nothingSelected) {
                    downloadLink.removeAttribute('href');
                    downloadLink.setAttribute('aria-disabled', 'true');
                } else {
                    downloadLink.setAttribute('href', url);
                    downloadLink.removeAttribute('aria-disabled');
                }
            }
            const copyButton = urlInput
                ? urlInput.closest('.join').querySelector('[data-copy-target]')
                : null;
            if (copyButton) {
                copyButton.disabled = nothingSelected;
            }
        }

        checkboxes.forEach((cb) => cb.addEventListener('change', update));
        if (toggle) {
            toggle.addEventListener('change', update);
        }
        update();
    });
}
