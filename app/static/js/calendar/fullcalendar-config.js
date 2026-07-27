/**
 * FullCalendar configuration and interactions (home page).
 *
 * This file was extracted from an inline <script> in index.html so the CSP
 * can enforce a strict `script-src 'self'` (an inline <script> would need
 * 'unsafe-inline' or a nonce). Server-injected data (isAdmin, currentUserId,
 * groupColorMap) is passed via data-* attributes instead of Jinja
 * interpolation directly into JS. The calendar's own events aren't
 * server-injected at all: they're fetched dynamically from /api/shifts (see
 * the `events` function below), for whatever range FullCalendar is
 * currently viewing - not capped by a fixed window baked in at page load.
 *
 * FullCalendar 7.0.1, loaded from jsDelivr rather than cdnjs (cdnjs hosts
 * neither the internal chunks nor the locale files for any version of this
 * package that was tried - consistent 404s).
 *
 * History: 7.0.0 was attempted twice before and reverted both times -
 * "Class constructor ... cannot be invoked without 'new'", thrown from
 * FullCalendar's own compiled code on the first Preact render. Root-caused
 * (see fullcalendar/fullcalendar#7472/#7474 upstream) to jsDelivr's `/+esm`
 * transform endpoint specifically (a Rollup+Terser build/dedup bug on
 * jsDelivr's side, not FullCalendar's) - every prior attempt here loaded it
 * via an ESM import path (plain jsDelivr ESM imports, esm.sh) that goes
 * through that exact endpoint. v7 also still ships a single-file global
 * bundle (`all/global.min.js`, a plain non-module <script>, see index.html)
 * that never touches `/+esm` - confirmed working in a real browser (no
 * console errors, correct rendering, French locale, drag & drop) before
 * this upgrade landed. Still worth re-testing after any future FullCalendar
 * bump: this endpoint-specific root cause is fixed by construction for the
 * global-bundle loading path, but re-verify rather than assume if the
 * loading method ever changes.
 *
 * No more "edit mode" toggle: drag & drop is always live for admins, and
 * clicking any event always opens its view/edit modal (read-only for a
 * non-admin, or for a leave the viewer doesn't own) - see
 * openShiftEditModal/openOnCallEditModal/openLeaveModal below.
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
    const currentUserId = Number(calendarEl.dataset.currentUserId);
    // Group.id -> daisyUI semantic color name (e.g. "primary"), the same
    // map the server used to render the filter/legend dots - reused here
    // so the calendar's own event dots are guaranteed pixel-identical,
    // with zero extra client-server round trip. Read from a JSON <script>
    // block (not a data-* attribute - tojson's raw double quotes would
    // truncate an HTML attribute value early).
    const groupColorMapEl = document.getElementById('group-color-map-data');
    const groupColorMap = groupColorMapEl ? JSON.parse(groupColorMapEl.textContent) : {};
    // Viewer/org-configurable time format (12h AM/PM vs 24h, see
    // app.get_time_format() and base.html's <body data-time-format>) -
    // drives FullCalendar's own event/slot time rendering below.
    const hour12 = (document.body.dataset.timeFormat || '').includes('%I');
    // <html lang="..."> reflects get_locale() (base.html) - "en" needs no
    // extra asset (FullCalendar's own default), "fr" needs the locale
    // file loaded in index.html (locales/fr.global.min.js). Same
    // fallback rule as date-picker.js's currentLocale().
    const calendarLocale = document.documentElement.lang === 'en' ? 'en' : 'fr';
    const csrfToken = document.querySelector('meta[name="csrf-token"]').content;

    const toggleTipsBtn = document.getElementById('toggle-tips');
    const tipsContainer = document.getElementById('tips-container');
    let tipsVisible = false;

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

    // Shared by eventDrop/eventResize/eventClick/the modals'
    // Save/Delete buttons/the Delete keyboard shortcut - the type ->
    // REST endpoint mapping was previously copy-pasted at each call site.
    function resolveEventEndpoint(type, resourceId) {
        if (type === 'shift') return `/api/shifts/${resourceId}`;
        if (type === 'oncall') return `/api/oncall/${resourceId}`;
        if (type === 'leave') return `/api/leave/${resourceId}`;
        return null;
    }

    // Shared by eventDrop/eventResize - both send the exact same PATCH
    // request and handle success/error identically, only the console
    // log label and the error announcement key differ. References
    // `calendar` by closure - safe even though `calendar` itself isn't
    // assigned until below this function declaration, since patchEvent
    // is only ever *called* later, from within the Calendar's own event
    // handlers, by which point `calendar` is fully assigned.
    function patchEvent(info, { logLabel, errorKey }) {
        const event = info.event;
        const eventId = event.id;
        const newStart = event.start;
        const newEnd = event.end;

        if (!eventId || eventId === undefined) {
            // A new event created by an external drop.
            return;
        }

        const extendedProps = event.extendedProps || {};
        const endpoint = resolveEventEndpoint(extendedProps.type, extendedProps.resourceId);
        if (!endpoint) {
            info.revert();
            return;
        }

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
                    console.log(`${logLabel}:`, data.message);
                    // Only refetch the calendar's events (FullCalendar
                    // AJAX request) instead of the whole page, to avoid
                    // losing the user's context (filters, scroll,
                    // current view).
                    calendar.refetchEvents();
                    if (data.rebalance_warning) {
                        announceToScreenReader(getString('rebalance_warning'), 'assertive');
                    }
                } else {
                    info.revert();
                    announceToScreenReader(getString('error_prefix') + data.error, 'assertive');
                }
            })
            .catch(error => {
                info.revert();
                console.error('Error:', error);
                announceToScreenReader(getString(errorKey), 'assertive');
            });
    }

    // Shared by every modal's Delete button and the Delete/Suppr keyboard
    // shortcut - resolves the confirmation message for the event's type,
    // confirms, then DELETEs it. `onSuccess` (optional): closes whichever
    // modal invoked this, a no-op for the keyboard-shortcut call site
    // (which has no modal to close).
    function deleteEvent(event, onSuccess) {
        const extendedProps = event.extendedProps || {};
        const type = extendedProps.type;
        const resourceId = extendedProps.resourceId;
        const endpoint = resolveEventEndpoint(type, resourceId);
        if (!endpoint) {
            return;
        }

        const confirmMessageKeys = {
            shift: 'confirm_delete_shift',
            oncall: 'confirm_delete_oncall',
            leave: 'confirm_delete_leave'
        };
        const message = getString(confirmMessageKeys[type]);

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
                            calendar.refetchEvents();
                            if (onSuccess) onSuccess();
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

    // Group filter - a checkbox per group (server-rendered, see
    // index.html), `change` triggers a refetch. No page reload, no
    // server-side enforcement of which groups a viewer may pick (see
    // dashboard_routes.py::index()'s own docstring) - purely a display
    // convenience, default selection only.
    function getCheckedGroupIds() {
        return Array.from(document.querySelectorAll('.group-filter-checkbox:checked'))
            .map(checkbox => Number(checkbox.value));
    }

    // Swaps the loading skeleton (daisyUI skeleton) for the calendar -
    // idempotent, safe to call more than once (see the loading/datesSet
    // callbacks below, which both call this as independent triggers).
    function revealCalendar() {
        const calendarSkeleton = document.getElementById('calendar-skeleton');
        if (calendarSkeleton) {
            calendarSkeleton.classList.add('hidden');
        }
        calendarEl.classList.remove('hidden');
    }

    document.querySelectorAll('.group-filter-checkbox').forEach(checkbox => {
        checkbox.addEventListener('change', () => calendar.refetchEvents());
    });

    const calendar = new FullCalendar.Calendar(calendarEl, {
        // Event start/end strings from the server are already translated
        // into the viewer's own timezone (server-side, via
        // app/utils/helpers/timezone_helpers.py) - timeZone: 'UTC' tells
        // FullCalendar to display those digits literally instead of
        // reinterpreting them against the browser's own system clock,
        // which would double-convert. No moment-timezone/luxon plugin
        // needed (this app has no build step, CSS/JS loaded via CDN
        // only) - the server does all the real zoneinfo conversion.
        // Every other Date getter/constructor in this file must stay
        // consistent with this (UTC getters, no `new Date(str)` on a
        // timezone-less string) - see formatDateForInput and the
        // shift-creation modal below.
        timeZone: 'UTC',
        initialView: 'dayGridMonth',
        // dayMaxEvents (a "+N de plus" popover capping rows per day cell)
        // was tried to shrink an exploding page height with many events
        // on one day, but real usage reported it hurt clarity more than
        // it helped (a hidden shift is a shift a viewer can miss) - every
        // event stays directly visible instead, unbounded.
        headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,timeGridWeek,timeGridDay'
        },
        // v7 changed the Week view's default titleFormat to omit the day
        // number entirely (month/year only, e.g. "juillet 2026") - with no
        // day range shown, the title alone can no longer tell which week
        // is displayed (confirmed against the official v6->v7 upgrade
        // guide, and empirically: the title stayed identical across
        // Prev/Next clicks within the same month). Restored via a
        // view-specific override; FullCalendar formats the range through
        // the standard Intl API (no more internal range-formatting logic
        // in v7), so a single day-inclusive format here is enough to get
        // a real "20 - 26 juillet 2026"-style range back.
        views: {
            timeGridWeek: {
                titleFormat: { year: 'numeric', month: 'long', day: 'numeric' }
            }
        },
        // Render prev/next as icons instead of the spelled-out "Précédent"/
        // "Suivant" text - v7 dropped the old top-level buttonIcons option
        // (a small built-in icon font), so this is now done per-button via
        // `buttons` (the v7 rename of v6's customButtons; also used to
        // override built-ins, not just add new ones). display:'icon' keeps
        // rendering to iconContent only, but FullCalendar still derives the
        // button's accessible name (aria-label) from its own localized
        // buttonText/buttonHint default - not overridden here - since we
        // only override how it's drawn, not its text/hint. Font Awesome's
        // SVG+JS mode replaces this <i> with an inline <svg> after mount,
        // same as every other icon in this app (see index.html's own
        // fa-chevron-* usage elsewhere) - aria-hidden because the
        // accessible name already lives on the <button> itself.
        buttons: {
            prev: {
                display: 'icon',
                iconContent: { html: '<i class="fas fa-chevron-left" aria-hidden="true"></i>' }
            },
            next: {
                display: 'icon',
                iconContent: { html: '<i class="fas fa-chevron-right" aria-hidden="true"></i>' }
            }
        },
        // Dynamic source (not a static embedded array): fetches
        // /api/shifts for exactly the range FullCalendar is currently
        // viewing, so navigating far into the past/future - e.g. a
        // schedule generated a year ahead - always shows real data
        // instead of being capped by a fixed window baked in at page
        // load. Also what makes calendar.refetchEvents() (called after
        // a drag/drop reschedule or a modal Save/Delete below) actually
        // pull fresh data instead of being a no-op against a static
        // array. The currently-checked group filter is appended as
        // repeated `group_ids` params; if every checkbox is unchecked,
        // short-circuit before the fetch entirely (an empty selection
        // is unambiguous client-side - no request needed to render zero
        // events, and no ambiguous "empty vs. absent" param for the
        // server to guess about).
        events: function (fetchInfo, successCallback, failureCallback) {
            const groupIds = getCheckedGroupIds();
            if (groupIds.length === 0) {
                announceToScreenReader(getString('no_groups_selected'), 'polite');
                successCallback([]);
                return;
            }

            const params = new URLSearchParams({
                start: fetchInfo.startStr,
                end: fetchInfo.endStr
            });
            groupIds.forEach(id => params.append('group_ids', id));

            fetch(`/api/shifts?${params}`, { credentials: 'same-origin' })
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}`);
                    }
                    return response.json();
                })
                .then(successCallback)
                .catch(error => {
                    console.error('Failed to load calendar events:', error);
                    failureCallback(error);
                });
        },
        loading: function (isLoading) {
            if (!isLoading) {
                revealCalendar();
            }
        },
        // Backup trigger for the same reveal: on a slow/flaky events
        // fetch, `loading(false)` can be delayed well past the point the
        // toolbar/grid frame itself has already painted (calendar.render()
        // draws that frame synchronously, independent of the async events
        // source) - datesSet fires once that frame is genuinely on
        // screen for the current view, on first render and on every
        // navigation, so it's a strictly safer/earlier-or-equal signal
        // that the skeleton can be removed. revealCalendar() is
        // idempotent (classList add/remove of an already-set state is a
        // no-op), so having two triggers can't cause a flicker either way.
        datesSet: function () {
            revealCalendar();
        },
        locale: calendarLocale,
        firstDay: 1,
        eventTimeFormat: {
            hour: '2-digit',
            minute: '2-digit',
            hour12: hour12
        },
        // v7 renamed slotLabelFormat -> slotHeaderFormat (confirmed against
        // the official v6->v7 upgrade guide; the old name is silently
        // ignored, only logging a console warning, not an error).
        slotHeaderFormat: {
            hour: '2-digit',
            minute: '2-digit',
            hour12: hour12
        },
        height: 'auto',

        // Drag & drop is always live for admins now - no more "edit
        // mode" toggle to gate it behind.
        editable: isAdmin,
        selectable: isAdmin,
        droppable: isAdmin,

        // Drag & drop configuration
        eventDrop: function (info) {
            patchEvent(info, { logLabel: 'Event updated', errorKey: 'update_error' });
        },

        eventResize: function (info) {
            patchEvent(info, { logLabel: 'Event resized', errorKey: 'resize_error' });
        },

        select: function (info) {
            // Called when a time range is selected (to create a new shift)
            if (!isAdmin) {
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
            // Clicking any event always opens its view/edit modal now -
            // no more edit-mode-gated click-to-delete. Each modal decides
            // internally whether it's editable (admin, or the owning user
            // for a leave) or read-only.
            const event = info.event;
            if (!event.id) {
                return;
            }

            const type = (event.extendedProps || {}).type;
            if (type === 'shift') {
                openShiftEditModal(event, { readOnly: !isAdmin });
            } else if (type === 'oncall') {
                openOnCallEditModal(event, { readOnly: !isAdmin });
            } else if (type === 'leave') {
                const isOwner = event.extendedProps.userId === currentUserId;
                openLeaveModal(event, { canDelete: isAdmin || isOwner });
            }
        },

        eventDidMount: function (info) {
            // Group-accent dot: a fresh <span>, not a change to the
            // event's own background/border-color - dark.css's
            // !important overrides on .fc-event-shift/-oncall/-leave
            // only target those existing selectors, so a brand-new
            // sibling element has nothing to lose a specificity fight
            // against. groupColorMap holds raw hex (GROUP_COLOR_PALETTE,
            // common_helpers.py), not a daisyUI var(--color-<name>)
            // token - a daisyUI token could exactly match the event's
            // own type-background color and become invisible (real bug,
            // confirmed via a real-browser screenshot).
            const groupId = info.event.extendedProps.groupId;
            if (groupId == null) return;

            const wrapper = info.el.querySelector(':scope > div:first-child');
            if (!wrapper) return;

            const dot = document.createElement('span');
            dot.className = 'fc-event-group-dot';
            dot.style.setProperty('--group-dot-color', groupColorMap[groupId] || '#888888');
            dot.setAttribute('aria-hidden', 'true');
            wrapper.insertBefore(dot, wrapper.firstChild);
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
    // Skeleton/calendar visibility swap now happens in the `loading`
    // callback above, once the first events fetch actually settles.

    // Expose the calendar globally
    window.calendar = calendar;

    // Escape a value before interpolating it into the HTML generated below
    // (user names/emails, shift-type labels - server data, but no reason to
    // trust its content when rendered as HTML).
    function escapeHtml(value) {
        const div = document.createElement('div');
        div.textContent = value;
        return div.innerHTML;
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

    // Format a date for a plain <input type="date"> (no time component) -
    // the edit modals only let the *day* change, not the hour (the hour
    // is either preserved from the original event or, for a shift whose
    // type changed, taken from the new type's own configured hours).
    function formatDateOnlyForInput(date) {
        const pad = (num) => num.toString().padStart(2, '0');
        return `${date.getUTCFullYear()}-${pad(date.getUTCMonth() + 1)}-${pad(date.getUTCDate())}`;
    }

    // Combine a "YYYY-MM-DD" date string with `timeSource`'s own UTC
    // hour/minute/second, producing a literal-UTC-digits ISO string (see
    // the timeZone: 'UTC' comment above) - used by the edit modals to
    // change the day while preserving the original event's time of day.
    function combineDateWithTime(dateStr, timeSource) {
        const pad = (num) => num.toString().padStart(2, '0');
        return `${dateStr}T${pad(timeSource.getUTCHours())}:${pad(timeSource.getUTCMinutes())}:${pad(timeSource.getUTCSeconds())}Z`;
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
                            calendar.refetchEvents();
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

    // Shared skeleton for the two edit modals below: build once (native
    // <dialog>, reused/updated on reopen), backdrop-click + Escape
    // handling, wire Close/Save/Delete buttons. `bodyHtml`/`onOpen` let
    // each caller supply its own fields and post-open wiring (data
    // fetch, Save handler) while sharing the modal chrome/lifecycle.
    function openEditModal(modalId, titleId, titleText, bodyHtml, onOpen) {
        let modal = document.getElementById(modalId);
        if (modal) {
            modal.remove();
        }
        modal = document.createElement('dialog');
        modal.id = modalId;
        modal.className = 'modal';
        modal.setAttribute('aria-labelledby', titleId);
        modal.innerHTML = `
            <div class="modal-box">
                <div class="flex items-start justify-between">
                    <h2 id="${titleId}" class="text-lg font-bold">${titleText}</h2>
                    <button type="button" class="btn btn-sm btn-circle btn-ghost close-modal" aria-label="${getString('close')}">&times;</button>
                </div>
                ${bodyHtml}
            </div>
        `;
        document.body.appendChild(modal);

        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.close();
                announceToScreenReader(getString('edit_cancelled'), 'polite');
            }
        });
        modal.addEventListener('cancel', () => {
            announceToScreenReader(getString('edit_cancelled'), 'polite');
        });
        modal.querySelectorAll('.close-modal').forEach(btn => {
            btn.onclick = () => {
                modal.close();
                announceToScreenReader(getString('edit_cancelled'), 'polite');
            };
        });

        modal.showModal();
        onOpen(modal);
        return modal;
    }

    // Click-to-edit modal for a shift: admin can change the date, the
    // person, and the shift type; a delete button; read-only for a
    // non-admin (plain text, no fetches, no Save/Delete).
    function openShiftEditModal(event, { readOnly }) {
        const props = event.extendedProps;
        const titleText = `<i class="fas fa-calendar-check" aria-hidden="true"></i> ${readOnly ? getString('view_shift_title') : getString('edit_shift_title')}`;

        if (readOnly) {
            const bodyHtml = `
                <div class="flex flex-col gap-2 py-4">
                    <p><strong>${getString('owner')}</strong>: ${escapeHtml(props.userName || '')}</p>
                    <p><strong>${getString('shift_type')}</strong>: ${escapeHtml(props.shiftTypeLabel || '')}</p>
                    <p><strong>${getString('shift_date')}</strong>: ${formatDateOnlyForInput(event.start)}</p>
                </div>
                <div class="modal-action">
                    <button type="button" class="btn close-modal">${getString('close')}</button>
                </div>
            `;
            openEditModal('view-shift-modal', 'view-shift-title', titleText, bodyHtml, () => {});
            return;
        }

        const bodyHtml = `
            <div class="flex flex-col gap-4 py-4">
                <div>
                    <label class="label" for="edit-shift-date">${getString('shift_date')}</label>
                    <input type="date" id="edit-shift-date" class="input w-full" value="${formatDateOnlyForInput(event.start)}" required aria-required="true">
                </div>
                <div>
                    <label class="label" for="edit-shift-user">${getString('user')}</label>
                    <select id="edit-shift-user" class="select w-full" required aria-required="true"></select>
                </div>
                <div>
                    <label class="label" for="edit-shift-type">${getString('shift_type')}</label>
                    <select id="edit-shift-type" class="select w-full" required aria-required="true"></select>
                </div>
            </div>
            <div class="modal-action justify-between">
                <button type="button" class="btn btn-error delete-btn">
                    <i class="fas fa-trash" aria-hidden="true"></i> ${getString('delete')}
                </button>
                <div class="flex gap-2">
                    <button type="button" class="btn close-modal">${getString('cancel')}</button>
                    <button type="button" class="btn btn-primary save-btn">
                        <i class="fas fa-check" aria-hidden="true"></i> ${getString('save')}
                    </button>
                </div>
            </div>
        `;

        openEditModal('edit-shift-modal', 'edit-shift-title', titleText, bodyHtml, (modal) => {
            let shiftTypesById = {};

            Promise.all([
                fetch('/api/users').then(r => r.json()),
                fetch('/api/shift-types').then(r => r.json())
            ]).then(([users, shiftTypes]) => {
                shiftTypesById = Object.fromEntries(shiftTypes.map(st => [String(st.id), st]));

                const userSelect = modal.querySelector('#edit-shift-user');
                userSelect.innerHTML = users.map(u =>
                    `<option value="${u.id}" ${u.id === props.userId ? 'selected' : ''}>${escapeHtml(u.name)} (${escapeHtml(u.email)})</option>`
                ).join('');

                const typeSelect = modal.querySelector('#edit-shift-type');
                typeSelect.innerHTML = shiftTypes.map(st =>
                    `<option value="${st.id}" ${st.id === props.shiftTypeId ? 'selected' : ''}>${escapeHtml(st.label)} (${st.start_hour}:00 - ${st.end_hour}:00)</option>`
                ).join('');
            }).catch(error => {
                console.error('Error loading data:', error);
                announceToScreenReader(getString('data_load_error'), 'assertive');
            });

            modal.querySelector('.delete-btn').onclick = () => {
                deleteEvent(event, () => modal.close());
            };

            modal.querySelector('.save-btn').onclick = () => {
                const pickedDate = modal.querySelector('#edit-shift-date').value;
                const userId = modal.querySelector('#edit-shift-user').value;
                const shiftTypeId = modal.querySelector('#edit-shift-type').value;

                if (!pickedDate || !userId || !shiftTypeId) {
                    announceToScreenReader(getString('fill_required_fields'), 'assertive');
                    return;
                }

                const shiftTypeChanged = shiftTypesById[shiftTypeId] && Number(shiftTypeId) !== props.shiftTypeId;
                let start, end;
                if (shiftTypeChanged) {
                    const st = shiftTypesById[shiftTypeId];
                    const pad = (num) => num.toString().padStart(2, '0');
                    start = `${pickedDate}T${pad(st.start_hour)}:00:00Z`;
                    end = `${pickedDate}T${pad(st.end_hour)}:00:00Z`;
                } else {
                    const durationMs = event.end - event.start;
                    start = combineDateWithTime(pickedDate, event.start);
                    end = new Date(new Date(start).getTime() + durationMs).toISOString();
                }

                fetch(`/api/shifts/${props.resourceId}`, {
                    method: 'PATCH',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest',
                        'X-CSRFToken': csrfToken
                    },
                    credentials: 'same-origin',
                    body: JSON.stringify({ start, end, userId, shiftTypeId })
                })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            modal.close();
                            calendar.refetchEvents();
                            announceToScreenReader(getString('shift_updated'), 'polite');
                        } else {
                            announceToScreenReader(getString('error_prefix') + data.error, 'assertive');
                        }
                    })
                    .catch(error => {
                        console.error('Error:', error);
                        announceToScreenReader(getString('shift_update_error'), 'assertive');
                    });
            };
        });
    }

    // Click-to-edit modal for an on-call: admin can change the start day
    // and the on-call person; a delete button; read-only for a
    // non-admin. Only the *day* is editable (the hour is fixed by the
    // group's configured OnCallAnchorRule, validated server-side) - the
    // duration is preserved from the original event.
    function openOnCallEditModal(event, { readOnly }) {
        const props = event.extendedProps;
        const titleText = `<i class="fas fa-moon" aria-hidden="true"></i> ${readOnly ? getString('view_oncall_title') : getString('edit_oncall_title')}`;

        if (readOnly) {
            const bodyHtml = `
                <div class="flex flex-col gap-2 py-4">
                    <p><strong>${getString('owner')}</strong>: ${escapeHtml(props.userName || '')}</p>
                    <p><strong>${getString('start_day')}</strong>: ${formatDateOnlyForInput(event.start)}</p>
                </div>
                <div class="modal-action">
                    <button type="button" class="btn close-modal">${getString('close')}</button>
                </div>
            `;
            openEditModal('view-oncall-modal', 'view-oncall-title', titleText, bodyHtml, () => {});
            return;
        }

        const bodyHtml = `
            <div class="flex flex-col gap-4 py-4">
                <div>
                    <label class="label" for="edit-oncall-date">${getString('start_day')}</label>
                    <input type="date" id="edit-oncall-date" class="input w-full" value="${formatDateOnlyForInput(event.start)}" required aria-required="true">
                </div>
                <div>
                    <label class="label" for="edit-oncall-user">${getString('user')}</label>
                    <select id="edit-oncall-user" class="select w-full" required aria-required="true"></select>
                </div>
            </div>
            <div class="modal-action justify-between">
                <button type="button" class="btn btn-error delete-btn">
                    <i class="fas fa-trash" aria-hidden="true"></i> ${getString('delete')}
                </button>
                <div class="flex gap-2">
                    <button type="button" class="btn close-modal">${getString('cancel')}</button>
                    <button type="button" class="btn btn-primary save-btn">
                        <i class="fas fa-check" aria-hidden="true"></i> ${getString('save')}
                    </button>
                </div>
            </div>
        `;

        openEditModal('edit-oncall-modal', 'edit-oncall-title', titleText, bodyHtml, (modal) => {
            fetch('/api/oncall-users').then(r => r.json()).then(users => {
                const userSelect = modal.querySelector('#edit-oncall-user');
                userSelect.innerHTML = users.map(u =>
                    `<option value="${u.id}" ${u.id === props.userId ? 'selected' : ''}>${escapeHtml(u.name)} (${escapeHtml(u.email)})</option>`
                ).join('');
            }).catch(error => {
                console.error('Error loading data:', error);
                announceToScreenReader(getString('data_load_error'), 'assertive');
            });

            modal.querySelector('.delete-btn').onclick = () => {
                deleteEvent(event, () => modal.close());
            };

            modal.querySelector('.save-btn').onclick = () => {
                const pickedDate = modal.querySelector('#edit-oncall-date').value;
                const userId = modal.querySelector('#edit-oncall-user').value;

                if (!pickedDate || !userId) {
                    announceToScreenReader(getString('fill_required_fields'), 'assertive');
                    return;
                }

                const durationMs = event.end - event.start;
                const start = combineDateWithTime(pickedDate, event.start);
                const end = new Date(new Date(start).getTime() + durationMs).toISOString();

                fetch(`/api/oncall/${props.resourceId}`, {
                    method: 'PATCH',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest',
                        'X-CSRFToken': csrfToken
                    },
                    credentials: 'same-origin',
                    body: JSON.stringify({ start, end, userId })
                })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            modal.close();
                            calendar.refetchEvents();
                            announceToScreenReader(getString('oncall_updated'), 'polite');
                        } else {
                            announceToScreenReader(getString('error_prefix') + data.error, 'assertive');
                        }
                    })
                    .catch(error => {
                        console.error('Error:', error);
                        announceToScreenReader(getString('oncall_update_error'), 'assertive');
                    });
            };
        });
    }

    // View/delete modal for a leave - no date-editing UI (not requested;
    // leave dates stay drag/resize-only, unchanged). Replaces the old
    // "click a leave in edit mode -> instant delete-with-confirm, no
    // visibility into what you're deleting" behavior, for both admins
    // and owning non-admins.
    function openLeaveModal(event, { canDelete }) {
        const props = event.extendedProps;
        const titleText = `<i class="fas fa-umbrella-beach" aria-hidden="true"></i> ${getString('view_leave_title')}`;
        const periodEnd = new Date(event.end.getTime() - 86400000); // allDay end is exclusive
        const bodyHtml = `
            <div class="flex flex-col gap-2 py-4">
                <p><strong>${getString('owner')}</strong>: ${escapeHtml(props.userName || '')}</p>
                <p><strong>${getString('period')}</strong>: ${formatDateOnlyForInput(event.start)} - ${formatDateOnlyForInput(periodEnd)}</p>
            </div>
            <div class="modal-action ${canDelete ? 'justify-between' : ''}">
                ${canDelete ? `<button type="button" class="btn btn-error delete-btn"><i class="fas fa-trash" aria-hidden="true"></i> ${getString('delete')}</button>` : ''}
                <button type="button" class="btn close-modal">${getString('close')}</button>
            </div>
        `;
        openEditModal('view-leave-modal', 'view-leave-title', titleText, bodyHtml, (modal) => {
            const deleteBtn = modal.querySelector('.delete-btn');
            if (deleteBtn) {
                deleteBtn.onclick = () => {
                    deleteEvent(event, () => modal.close());
                };
            }
        });
    }

    // Handle the Delete key to remove the currently-selected event -
    // admin, or the owning user for a leave (matches the delete
    // capability each modal itself offers - see eventClick above).
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Delete' || e.key === 'Suppr') {
            const selectedEvent = window.selectedEvent;
            if (!selectedEvent) return;
            const props = selectedEvent.extendedProps || {};
            const canDelete = isAdmin || (props.type === 'leave' && props.userId === currentUserId);
            if (canDelete) {
                deleteEvent(selectedEvent);
            }
        }
    });

    // Track the currently selected event
    calendar.on('eventClick', function (info) {
        window.selectedEvent = info.event;
    });
});
