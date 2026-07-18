/**
 * FullCalendar configuration and interactions (home page).
 *
 * This file was extracted from an inline <script> in index.html so the CSP
 * can enforce a strict `script-src 'self'` (an inline <script> would need
 * 'unsafe-inline' or a nonce). Server-injected data (isAdmin, events) is
 * passed via data-* attributes and a <script type="application/json"> tag
 * instead of Jinja interpolation directly into JS.
 *
 * FullCalendar stays on 6.1.21 (no bump to 7.0.0) and is loaded from
 * jsDelivr rather than cdnjs - two independent findings from real-browser
 * testing:
 *   1. cdnjs hosts neither the internal chunks nor the locale files for any
 *      version of this package that was tried (consistent 404s);
 *   2. FullCalendar 7.0.0 throws a real runtime error outside its own
 *      official build pipeline ("Class constructor ... cannot be invoked
 *      without 'new'", thrown from FullCalendar's own compiled code on the
 *      first Preact render - reproduced identically via jsDelivr AND via
 *      esm.sh, which normally rebuilds packages with their dependencies
 *      already resolved - so this is not a CDN-hosting issue but a bug in
 *      this package under this consumption mode, outside the reach of any
 *      CDN-side workaround). Stays on the last stable 6.x release, loaded
 *      from a CDN instead of being vendored locally like the rest of the app.
 */
import {
    announceToScreenReader,
    confirmActionAccessible,
    focusElement,
} from '../utils/accessibility.js';
import { getString } from '../utils/i18n.js';
import { initDatePicker, syncDatePicker } from '../utils/date-picker.js';

document.addEventListener('DOMContentLoaded', function () {
    const calendarEl = document.getElementById('calendar');
    if (!calendarEl) {
        console.error("Element #calendar not found!");
        return;
    }

    const isAdmin = calendarEl.dataset.isAdmin === 'true';
    // Viewer/org-configurable time format (12h AM/PM vs 24h, see
    // app.get_time_format() and base.html's <body data-time-format>) -
    // drives FullCalendar's own event/slot time rendering below.
    const hour12 = (document.body.dataset.timeFormat || '').includes('%I');
    const eventsDataEl = document.getElementById('calendar-events-data');
    const events = eventsDataEl ? JSON.parse(eventsDataEl.textContent) : [];
    const csrfToken = document.querySelector('meta[name="csrf-token"]').content;

    // Read edit-mode state from the URL
    const urlParams = new URLSearchParams(window.location.search);
    let editModeEnabled = urlParams.get('edit') === 'true';
    let tipsVisible = false;

    // Toggle button handling
    const toggleEditModeBtn = document.getElementById('toggle-edit-mode');
    const toggleTipsBtn = document.getElementById('toggle-tips');
    const editModeStatusTag = document.getElementById('edit-mode-status-tag');
    const tipsContainer = document.getElementById('tips-container');

    // Update the URL and edit-mode state
    function updateEditModeState(enabled) {
        editModeEnabled = enabled;

        // Update the URL without reloading the page
        const url = new URL(window.location);
        if (enabled) {
            url.searchParams.set('edit', 'true');
        } else {
            url.searchParams.delete('edit');
        }
        window.history.pushState({}, '', url);

        // Update the UI
        if (editModeStatusTag) {
            if (enabled) {
                editModeStatusTag.innerHTML = `<i class="fas fa-edit" aria-hidden="true"></i> ${getString('edit_mode_on')}`;
                editModeStatusTag.classList.remove('badge-error');
                editModeStatusTag.classList.add('badge-success');
                editModeStatusTag.setAttribute('aria-label', getString('edit_mode_on'));
            } else {
                editModeStatusTag.innerHTML = `<i class="fas fa-edit" aria-hidden="true"></i> ${getString('edit_mode_off')}`;
                editModeStatusTag.classList.remove('badge-success');
                editModeStatusTag.classList.add('badge-error');
                editModeStatusTag.setAttribute('aria-label', getString('edit_mode_off'));
            }
        }

        if (toggleEditModeBtn) {
            if (enabled) {
                toggleEditModeBtn.innerHTML = `<i class="fas fa-toggle-off" aria-hidden="true"></i> ${getString('disable_edit_mode_short')}`;
                toggleEditModeBtn.classList.remove('btn-success');
                toggleEditModeBtn.classList.add('btn-error');
                toggleEditModeBtn.setAttribute('aria-label', getString('disable_edit_mode'));
            } else {
                toggleEditModeBtn.innerHTML = `<i class="fas fa-toggle-on" aria-hidden="true"></i> ${getString('enable_edit_mode_short')}`;
                toggleEditModeBtn.classList.remove('btn-error');
                toggleEditModeBtn.classList.add('btn-success');
                toggleEditModeBtn.setAttribute('aria-label', getString('enable_edit_mode'));
            }
        }

        // Update the calendar's own properties
        if (window.calendar) {
            window.calendar.setOption('editable', enabled && isAdmin);
            window.calendar.setOption('selectable', enabled && isAdmin);
            window.calendar.setOption('droppable', enabled && isAdmin);
        }
    }

    if (toggleEditModeBtn && editModeStatusTag) {
        toggleEditModeBtn.addEventListener('click', function () {
            updateEditModeState(!editModeEnabled);
        });
    }

    if (toggleTipsBtn && tipsContainer) {
        toggleTipsBtn.addEventListener('click', function () {
            tipsVisible = !tipsVisible;

            if (tipsVisible) {
                tipsContainer.classList.remove('hidden');
                toggleTipsBtn.innerHTML = `<i class="fas fa-eye-slash" aria-hidden="true"></i> ${getString('hide_tips_short')}`;
                toggleTipsBtn.classList.remove('btn-info');
                toggleTipsBtn.classList.add('btn-warning');
                toggleTipsBtn.setAttribute('aria-label', getString('hide_tips'));
            } else {
                tipsContainer.classList.add('hidden');
                toggleTipsBtn.innerHTML = `<i class="fas fa-eye" aria-hidden="true"></i> ${getString('show_tips_short')}`;
                toggleTipsBtn.classList.remove('btn-warning');
                toggleTipsBtn.classList.add('btn-info');
                toggleTipsBtn.setAttribute('aria-label', getString('show_tips'));
            }
        });
    }

    const calendar = new FullCalendar.Calendar(calendarEl, {
        // Event start/end strings from the server are already translated
        // into the viewer's own timezone (server-side, via
        // app/utils/helpers/timezone_helpers.py) - timeZone: 'UTC' tells
        // FullCalendar to display those digits literally instead of
        // reinterpreting them against the browser's own system clock,
        // which would double-convert. No moment-timezone/luxon plugin
        // needed (this app is CDN-only, see CLAUDE.md's Frontend
        // section) - the server does all the real zoneinfo conversion.
        // Every other Date getter/constructor in this file must stay
        // consistent with this (UTC getters, no `new Date(str)` on a
        // timezone-less string) - see formatDateForInput and the
        // shift-creation modal below.
        timeZone: 'UTC',
        initialView: 'dayGridMonth',
        headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,timeGridWeek,timeGridDay'
        },
        events: events,
        locale: 'fr',
        firstDay: 1,
        eventTimeFormat: {
            hour: '2-digit',
            minute: '2-digit',
            hour12: hour12
        },
        slotLabelFormat: {
            hour: '2-digit',
            minute: '2-digit',
            hour12: hour12
        },
        height: 'auto',

        // Enable drag & drop for admins
        editable: editModeEnabled && isAdmin,
        selectable: editModeEnabled && isAdmin,
        droppable: editModeEnabled && isAdmin,

        // Drag & drop configuration
        eventDrop: function (info) {
            // Called when an event is dropped
            const event = info.event;
            const eventId = event.id;
            const newStart = event.start;
            const newEnd = event.end;

            if (!eventId || eventId === undefined) {
                // This is a new event created by an external drop
                return;
            }

            // Determine the event type and the resource ID
            const extendedProps = event.extendedProps || {};
            const type = extendedProps.type;
            const resourceId = extendedProps.resourceId;

            let endpoint = '';

            if (type === 'shift') {
                endpoint = `/api/shifts/${resourceId}`;
            } else if (type === 'oncall') {
                endpoint = `/api/oncall/${resourceId}`;
            } else if (type === 'leave') {
                endpoint = `/api/leave/${resourceId}`;
            } else {
                info.revert();
                return;
            }

            // Send the update to the server
            fetch(endpoint, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': csrfToken
                },
                credentials: 'same-origin',
                body: JSON.stringify({
                    start: newStart.toISOString(),
                    end: newEnd.toISOString()
                })
            })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        console.log('Event updated:', data.message);
                        // Only refetch the calendar's events (FullCalendar
                        // AJAX request) instead of the whole page, to avoid
                        // losing the user's context (filters, scroll,
                        // current view).
                        calendar.refetchEvents();
                        if (data.rebalance_warning) {
                            announceToScreenReader(
                                getString('rebalance_warning'),
                                'assertive'
                            );
                        }
                    } else {
                        // Revert the change on error
                        info.revert();
                        announceToScreenReader(getString('error_prefix') + data.error, 'assertive');
                    }
                })
                .catch(error => {
                    info.revert();
                    console.error('Error:', error);
                    announceToScreenReader(getString('update_error'), 'assertive');
                });
        },

        eventResize: function (info) {
            // Called when an event is resized
            const event = info.event;
            const eventId = event.id;
            const newStart = event.start;
            const newEnd = event.end;

            if (!eventId || eventId === undefined) {
                return;
            }

            // Determine the event type and the resource ID
            const extendedProps = event.extendedProps || {};
            const type = extendedProps.type;
            const resourceId = extendedProps.resourceId;

            let endpoint = '';

            if (type === 'shift') {
                endpoint = `/api/shifts/${resourceId}`;
            } else if (type === 'oncall') {
                endpoint = `/api/oncall/${resourceId}`;
            } else if (type === 'leave') {
                endpoint = `/api/leave/${resourceId}`;
            } else {
                info.revert();
                return;
            }

            // Send the update to the server
            fetch(endpoint, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': csrfToken
                },
                credentials: 'same-origin',
                body: JSON.stringify({
                    start: newStart.toISOString(),
                    end: newEnd.toISOString()
                })
            })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        console.log('Event resized:', data.message);
                        // Only refetch the calendar's events, not the whole
                        // page (see eventDrop above).
                        calendar.refetchEvents();
                        if (data.rebalance_warning) {
                            announceToScreenReader(
                                getString('rebalance_warning'),
                                'assertive'
                            );
                        }
                    } else {
                        info.revert();
                        announceToScreenReader(getString('error_prefix') + data.error, 'assertive');
                    }
                })
                .catch(error => {
                    info.revert();
                    console.error('Error:', error);
                    announceToScreenReader(getString('resize_error'), 'assertive');
                });
        },

        select: function (info) {
            // Called when a time range is selected (to create a new shift)
            // Edit mode only
            if (!isAdmin || !editModeEnabled) {
                calendar.unselect();
                return;
            }

            const start = info.start;
            const end = info.end || start;

            // Open a modal to pick the user and the shift type
            openShiftCreationModal(start, end);

            calendar.unselect();
        },

        eventClick: function (info) {
            // Called when an event is clicked
            const event = info.event;
            const eventId = event.id;

            if (!eventId || eventId === undefined) {
                return;
            }

            // In edit mode, clicking an event deletes it (with confirmation)
            // Outside edit mode, clicking does nothing
            if (editModeEnabled && isAdmin) {
                // Determine the event type and the resource ID
                const extendedProps = event.extendedProps || {};
                const type = extendedProps.type;
                const resourceId = extendedProps.resourceId;

                let endpoint = '';
                let message = '';

                if (type === 'shift') {
                    endpoint = `/api/shifts/${resourceId}`;
                    message = getString('confirm_delete_shift');
                } else if (type === 'oncall') {
                    endpoint = `/api/oncall/${resourceId}`;
                    message = getString('confirm_delete_oncall');
                } else if (type === 'leave') {
                    endpoint = `/api/leave/${resourceId}`;
                    message = getString('confirm_delete_leave');
                } else {
                    return;
                }

                confirmActionAccessible(message,
                    () => {
                        fetch(endpoint, {
                            method: 'DELETE',
                            headers: {
                                'Content-Type': 'application/json',
                                'X-Requested-With': 'XMLHttpRequest',
                                'X-CSRFToken': csrfToken
                            },
                            credentials: 'same-origin'
                        })
                            .then(response => response.json())
                            .then(data => {
                                if (data.success) {
                                    event.remove();
                                    console.log('Event deleted:', data.message);
                                    announceToScreenReader(getString('event_deleted'), 'polite');
                                    // Reload the page to resync with the backend
                                    location.reload();
                                } else {
                                    announceToScreenReader(getString('error_prefix') + data.error, 'assertive');
                                }
                            })
                            .catch(error => {
                                console.error('Error:', error);
                                announceToScreenReader(getString('delete_error'), 'assertive');
                            });
                    },
                    () => {
                        announceToScreenReader(getString('delete_cancelled'), 'polite');
                    }
                );
            }
        },

        eventDidMount: function (info) {
            // Attach custom data to the event
            const event = info.event;
            if (event.extendedProps && event.extendedProps.userId) {
                event.setExtendedProp('userId', event.extendedProps.userId);
            }
        },

        // Disable drag & drop on weekends
        dateClick: function (info) {
            const date = info.date;
            // getUTCDay, not getDay - see formatDateForInput's comment.
            if (date.getUTCDay() === 0 || date.getUTCDay() === 6) { // Sunday (0) or Saturday (6)
                announceToScreenReader(getString('weekend_restriction'), 'assertive');
                return false;
            }
        }
    });

    calendar.render();

    // Swap the loading skeleton (daisyUI skeleton) for the calendar once
    // its first render is done.
    const calendarSkeleton = document.getElementById('calendar-skeleton');
    if (calendarSkeleton) {
        calendarSkeleton.classList.add('hidden');
    }
    calendarEl.classList.remove('hidden');

    // Expose the calendar globally
    window.calendar = calendar;

    // Initialize the UI and the calendar from the edit-mode state
    updateEditModeState(editModeEnabled);

    // Escape a value before interpolating it into the HTML generated below
    // (user names/emails, shift-type labels - server data, but no reason to
    // trust its content when rendered as HTML).
    function escapeHtml(value) {
        const div = document.createElement('div');
        div.textContent = value;
        return div.innerHTML;
    }

    // Open the shift-creation modal
    function openShiftCreationModal(start, end) {
        // Load the users and shift types
        Promise.all([
            fetch('/api/users').then(r => r.json()),
            fetch('/api/shift-types').then(r => r.json())
        ]).then(([users, shiftTypes]) => {
            // Build the modal (native <dialog> element - focus trap and
            // Escape-to-close are handled natively by the browser via
            // showModal(), no need to hand-roll them).
            const modalId = 'create-shift-modal';
            let modal = document.getElementById(modalId);

            if (!modal) {
                modal = document.createElement('dialog');
                modal.id = modalId;
                modal.className = 'modal';
                modal.setAttribute('aria-labelledby', 'create-shift-title');
                modal.innerHTML = `
                    <div class="modal-box">
                        <div class="flex items-start justify-between">
                            <h2 id="create-shift-title" class="text-lg font-bold">
                                <i class="fas fa-plus" aria-hidden="true"></i> ${getString('create_new_shift_title')}
                            </h2>
                            <button type="button" class="btn btn-sm btn-circle btn-ghost close-modal" aria-label="${getString('close')}">&times;</button>
                        </div>
                        <form id="shift-creation-form" aria-labelledby="create-shift-title" class="flex flex-col gap-4 py-4">
                            <div>
                                <label class="label" for="shift-start">${getString('start_datetime')}</label>
                                <input type="datetime-local" id="shift-start" class="input w-full" value="${formatDateForInput(start)}" required aria-required="true">
                            </div>
                            <div>
                                <label class="label" for="shift-end">${getString('end_datetime')}</label>
                                <input type="datetime-local" id="shift-end" class="input w-full" value="${formatDateForInput(end)}" required aria-required="true">
                            </div>
                            <div>
                                <label class="label" for="shift-user">${getString('user')}</label>
                                <select id="shift-user" class="select w-full" required aria-required="true">
                                    <option value="">${getString('select_user')}</option>
                                    ${users.map(u => `<option value="${u.id}">${escapeHtml(u.name)} (${escapeHtml(u.email)})</option>`).join('')}
                                </select>
                            </div>
                            <div>
                                <label class="label" for="shift-type">${getString('shift_type')}</label>
                                <select id="shift-type" class="select w-full" required aria-required="true">
                                    <option value="">${getString('select_shift_type')}</option>
                                    ${shiftTypes.map(st => `<option value="${st.id}">${escapeHtml(st.label)} (${st.start_hour}:00 - ${st.end_hour}:00)</option>`).join('')}
                                </select>
                            </div>
                        </form>
                        <div class="modal-action">
                            <button type="button" class="btn close-modal" aria-label="${getString('cancel')}">
                                <i class="fas fa-times" aria-hidden="true"></i> ${getString('cancel')}
                            </button>
                            <button type="button" class="btn btn-primary create-shift-btn" aria-label="${getString('create_shift')}">
                                <i class="fas fa-check" aria-hidden="true"></i> ${getString('create')}
                            </button>
                        </div>
                    </div>
                `;
                document.body.appendChild(modal);

                // Clicking the backdrop (outside .modal-box) closes the
                // modal - equivalent to the old .modal-open/.modal-backdrop
                // pattern, but handled natively by <dialog>.
                modal.addEventListener('click', (e) => {
                    if (e.target === modal) {
                        modal.close();
                        announceToScreenReader(getString('shift_creation_cancelled'), 'polite');
                    }
                });

                // "cancel" (Escape) is distinct from "close" - unlike
                // "close", it never fires for a programmatic .close() after
                // a successful save, so there's no risk of announcing
                // "cancelled" right after "created".
                modal.addEventListener('cancel', () => {
                    announceToScreenReader(getString('shift_creation_cancelled'), 'polite');
                });

                // Bind the Vanilla Calendar Pro picker on the two
                // datetime-local inputs - only reachable here, on first
                // build: these inputs don't exist yet at page load, so
                // the generic initDatePickers(document) call in main.js
                // never sees them.
                initDatePicker(modal.querySelector('#shift-start'));
                initDatePicker(modal.querySelector('#shift-end'));
            } else {
                // Update the values, then resync each picker's popup
                // with the new value - setting .value directly (unlike a
                // user's click on a day) doesn't go through the
                // calendar's own change handler.
                const startInput = modal.querySelector('#shift-start');
                const endInput = modal.querySelector('#shift-end');
                startInput.value = formatDateForInput(start);
                endInput.value = formatDateForInput(end);
                syncDatePicker(startInput);
                syncDatePicker(endInput);
            }

            // Open the modal (showModal() natively handles the focus trap
            // and Escape - explicit focus below is a complement, since the
            // browser's default "first focusable element" focus isn't
            // guaranteed identical across engines).
            modal.showModal();
            focusElement(modal.querySelector('#shift-start'));

            // Wire up the buttons
            modal.querySelectorAll('.close-modal').forEach(btn => {
                btn.onclick = () => {
                    modal.close();
                    announceToScreenReader(getString('shift_creation_cancelled'), 'polite');
                };
            });

            modal.querySelector('.create-shift-btn').onclick = () => {
                const userId = modal.querySelector('#shift-user').value;
                const shiftTypeId = modal.querySelector('#shift-type').value;
                const startInput = modal.querySelector('#shift-start').value;
                const endInput = modal.querySelector('#shift-end').value;

                if (!userId || !shiftTypeId || !startInput || !endInput) {
                    announceToScreenReader(getString('fill_required_fields'), 'assertive');
                    return;
                }

                // startInput/endInput ("YYYY-MM-DDTHH:MM", from a native
                // <input type="datetime-local">) must NOT go through
                // `new Date(str)` - that parses a timezone-less string as
                // browser-local time and applies a real UTC conversion,
                // inconsistent with the drag & drop path above (which
                // sends the viewer's literal wall-clock digits, no real
                // conversion, matching the server's expectation - see
                // app/utils/helpers/timezone_helpers.py). Appending
                // seconds + "Z" keeps the same literal-digits contract.
                const toLiteralIso = (value) => `${value}:00Z`;

                // Create the shift via the API
                fetch('/api/shifts', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest',
                        'X-CSRFToken': csrfToken
                    },
                    credentials: 'same-origin',
                    body: JSON.stringify({
                        userId: userId,
                        shiftTypeId: shiftTypeId,
                        start: toLiteralIso(startInput),
                        end: toLiteralIso(endInput)
                    })
                })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            modal.close();
                            console.log('Shift created:', data.message);
                            announceToScreenReader(getString('shift_created'), 'polite');
                            // Reload the page to resync with the backend
                            location.reload();
                        } else {
                            announceToScreenReader(getString('error_prefix') + data.error, 'assertive');
                        }
                    })
                    .catch(error => {
                        console.error('Error:', error);
                        announceToScreenReader(getString('shift_creation_error'), 'assertive');
                    });
            };
        }).catch(error => {
            console.error('Error loading data:', error);
            announceToScreenReader(getString('data_load_error'), 'assertive');
        });
    }

    // Format a date for a datetime-local input
    function formatDateForInput(date) {
        // UTC getters, not local ones: under timeZone: 'UTC' (see the
        // Calendar config above), FullCalendar's Date objects carry the
        // viewer's own wall-clock digits in their UTC components - local
        // getters would reapply the browser's real system offset on top,
        // shifting the digits a second time.
        const pad = (num) => num.toString().padStart(2, '0');
        return `${date.getUTCFullYear()}-${pad(date.getUTCMonth() + 1)}-${pad(date.getUTCDate())}T${pad(date.getUTCHours())}:${pad(date.getUTCMinutes())}`;
    }

    // Handle the Delete key to remove an event (edit mode only)
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Delete' || e.key === 'Suppr') {
            const selectedEvent = window.selectedEvent;
            if (selectedEvent && isAdmin && editModeEnabled) {
                // Determine the event type and the resource ID
                const extendedProps = selectedEvent.extendedProps || {};
                const type = extendedProps.type;
                const resourceId = extendedProps.resourceId;

                let endpoint = '';
                let message = '';

                if (type === 'shift') {
                    endpoint = `/api/shifts/${resourceId}`;
                    message = getString('confirm_delete_shift');
                } else if (type === 'oncall') {
                    endpoint = `/api/oncall/${resourceId}`;
                    message = getString('confirm_delete_oncall');
                } else if (type === 'leave') {
                    endpoint = `/api/leave/${resourceId}`;
                    message = getString('confirm_delete_leave');
                } else {
                    return;
                }

                confirmActionAccessible(message,
                    () => {
                        fetch(endpoint, {
                            method: 'DELETE',
                            headers: {
                                'Content-Type': 'application/json',
                                'X-Requested-With': 'XMLHttpRequest',
                                'X-CSRFToken': csrfToken
                            },
                            credentials: 'same-origin'
                        })
                            .then(response => response.json())
                            .then(data => {
                                if (data.success) {
                                    selectedEvent.remove();
                                    console.log('Event deleted:', data.message);
                                    announceToScreenReader(getString('event_deleted'), 'polite');
                                    // Reload the page to resync with the backend
                                    location.reload();
                                } else {
                                    announceToScreenReader(getString('error_prefix') + data.error, 'assertive');
                                }
                            })
                            .catch(error => {
                                console.error('Error:', error);
                                announceToScreenReader(getString('delete_error'), 'assertive');
                            });
                    },
                    () => {
                        announceToScreenReader(getString('delete_cancelled'), 'polite');
                    }
                );
            }
        }
    });

    // Track the currently selected event
    calendar.on('eventClick', function (info) {
        window.selectedEvent = info.event;
    });
});
