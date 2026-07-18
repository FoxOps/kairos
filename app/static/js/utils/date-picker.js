/**
 * Wires Vanilla Calendar Pro (https://github.com/uvarov-frontend/vanilla-calendar-pro)
 * onto every native <input type="date">/<input type="datetime-local">
 * in the page, replacing the browser's own picker with a daisyUI-themed
 * popup calendar - see theme-colors.css/vanilla-calendar-overrides.css
 * for the Dracula/Alucard styling.
 *
 * `inputMode: true` binds the calendar directly to the real input and
 * writes the selected date back into `input.value` using the exact
 * format the input's own `type` expects (ISO "YYYY-MM-DD" for `date`,
 * "YYYY-MM-DDTHH:MM" for `datetime-local`) - the same contract Flask's
 * forms and `date_str=...`/`datetime-local` value parsing already rely
 * on (see CLAUDE.md's "Date/time display format" section), so no
 * template or backend change is needed: this only replaces the picker
 * UI, never the value format.
 *
 * The CDN build must be the real ES module (`index.mjs`) - the
 * "index.min.js" jsDelivr resolves by default for this package is a
 * UMD bundle (`export` throws `does not provide an export named
 * 'Calendar'` under a native `import`), confirmed by testing both
 * directly in a browser.
 */
import { Calendar } from 'https://cdn.jsdelivr.net/npm/vanilla-calendar-pro@3.1.0/index.mjs';

const CALENDAR_SELECTOR = 'input[type="date"], input[type="datetime-local"]';

// Tracks which <input> elements already have a Calendar instance bound,
// so re-running initDatePickers() (e.g. after a modal is rebuilt) never
// double-initializes an input that's still in the DOM.
const instances = new WeakMap();

function currentLocale() {
    // <html lang="{{ get_locale() }}"> - see base.html/app/__init__.py's
    // get_locale(). Only "fr"/"en" are supported catalogs (see
    // CLAUDE.md's "Multi-language support"); Vanilla Calendar Pro
    // resolves both natively via Intl.
    return document.documentElement.lang === 'en' ? 'en' : 'fr';
}

// By design, `inputMode: true` does NOT write the picked date into the
// input's `.value` on its own ("By default, the calendar does not write
// any values to the Input field, giving you unique control over what
// you want to see in the value" - official docs). The write-back must
// happen in onChangeToInput, reading self.context.selectedDates[0]
// ("YYYY-MM-DD") - confirmed against the library's own
// type-default-in-input.ts example. For a datetime-local input, the
// time half comes from self.context.selectedTime ("HH:MM" in 24h mode,
// see selectionTimeMode below).
function writeBackToInput(self) {
    const input = self.context.inputElement;
    if (!input) return;
    const [selectedDate] = self.context.selectedDates;

    if (!selectedDate) {
        input.value = '';
    } else if (input.type === 'datetime-local') {
        input.value = `${selectedDate}T${self.context.selectedTime || '00:00'}`;
    } else {
        input.value = selectedDate;
        // Date-only picker: closing after a pick matches the native
        // <input type="date"> UX. A datetime-local input stays open so
        // the user can still pick a time.
        self.hide();
    }

    // WTForms/native form submission and any other listener (e.g. this
    // app's own change handlers) read the input the normal way -
    // dispatching "change" (not "input") keeps that contract, since
    // setting .value programmatically fires neither event on its own.
    input.dispatchEvent(new Event('change', { bubbles: true }));
}

// Splits a native input's current .value into the calendar's own
// selectedDates/selectedTime shape - "YYYY-MM-DD" (+ "THH:MM" for
// datetime-local). Used both to seed the initial selection (server-
// rendered forms often pre-fill a value, e.g. an edit form) and to
// resync after a programmatic .value assignment (syncDatePicker below).
function dateAndTimeFromValue(input) {
    if (!input.value) return { selectedDates: [], selectedTime: undefined };
    if (input.type === 'datetime-local') {
        const [datePart, timePart] = input.value.split('T');
        return { selectedDates: [datePart], selectedTime: timePart };
    }
    return { selectedDates: [input.value], selectedTime: undefined };
}

// A native <dialog> opened via showModal() (e.g. the shift-creation
// modal in fullcalendar-config.js) is promoted to the browser's own
// "top layer" - everything outside that dialog, however high its
// z-index, renders BELOW it. The calendar popup is appended as a plain
// sibling under <body> (confirmed by inspecting the live DOM - it is
// not a child of the input, and the library has no "container" option
// to redirect that), so inside a modal it would otherwise be created
// but end up entirely hidden behind the dialog. Fix: on each show,
// reparent the popup into the dialog itself, so it inherits the top
// layer promotion. `position: fixed` (not the library's own
// `absolute`) keeps its viewport-relative coordinates - already
// computed by positionToInput: 'auto' - correct after the move, since
// a plain <dialog> (no transform/filter) doesn't establish a new
// containing block for `fixed` descendants the way it would for
// `absolute` ones.
function reparentIntoDialog(self) {
    const dialog = self.context.inputElement?.closest('dialog');
    const popup = self.context.mainElement;
    if (!dialog || !popup || popup.parentElement === dialog) return;
    dialog.appendChild(popup);
    popup.style.position = 'fixed';
}

function buildOptions(input) {
    const { selectedDates, selectedTime } = dateAndTimeFromValue(input);
    return {
        inputMode: true,
        positionToInput: 'auto',
        // Matches theme-manager.js, which sets data-theme="dark"/"light"
        // on <html> - a CSS-selector-shaped string ("tag[attribute]"),
        // not a bare attribute name. This is already the library's
        // documented default; set explicitly for clarity/robustness
        // against a future default change.
        themeAttrDetect: 'html[data-theme]',
        locale: currentLocale(),
        firstWeekday: 1, // Monday - matches the app's Monday-anchored week (see CLAUDE.md)
        selectionTimeMode: input.type === 'datetime-local' ? 24 : false,
        selectedDates,
        selectedTime,
        onChangeToInput: writeBackToInput,
        onShow: reparentIntoDialog,
    };
}

/**
 * Bind a single input, if not already bound.
 * @param {HTMLInputElement} input
 */
export function initDatePicker(input) {
    if (!input || instances.has(input)) return;
    const calendar = new Calendar(input, buildOptions(input));
    calendar.init();
    instances.set(input, calendar);
}

/**
 * Bind every native date/datetime-local input under `root` (defaults to
 * the whole document). Safe to call repeatedly - already-bound inputs
 * are skipped.
 * @param {ParentNode} [root]
 */
export function initDatePickers(root = document) {
    root.querySelectorAll(CALENDAR_SELECTOR).forEach(initDatePicker);
}

/**
 * Re-sync an already-bound calendar's popup with its input's current
 * `.value` (e.g. after setting `input.value` programmatically, which -
 * unlike a user pick - does not go through the calendar's own click
 * handler). Binds the input first if it isn't tracked yet.
 * @param {HTMLInputElement} input
 */
export function syncDatePicker(input) {
    if (!input) return;
    const calendar = instances.get(input);
    if (!calendar) {
        initDatePicker(input);
        return;
    }
    calendar.set(dateAndTimeFromValue(input));
}
