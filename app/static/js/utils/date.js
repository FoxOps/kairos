/**
 * Date formatting helpers, following the viewer/org-configurable
 * date_format/time_format setting (see app.get_date_format()/
 * get_time_format(), CLAUDE.md's date/time format section) rather than
 * a fixed fr-FR locale. The pattern comes from base.html's
 * <body data-date-format data-time-format> attributes - only 3 date
 * patterns and 2 time patterns are ever configurable (see
 * SettingsService.SUPPORTED_DATE_FORMATS/SUPPORTED_TIME_FORMATS), so a
 * plain switch is simpler and more predictable here than trying to
 * reproduce a strftime engine in JS.
 */

function pad2(n) {
    return String(n).padStart(2, '0');
}

/**
 * Format a date for display, using UTC getters - callers pass either a
 * date-only ISO string ("2026-07-16", parsed by JS as UTC midnight) or
 * an already-UTC-normalized Date (see fullcalendar-config.js's
 * top-of-file comment on why UTC getters are mandatory here: local
 * getters would reinterpret against the browser's own timezone and
 * shift the day).
 * @param {Date|string} date - Date to format
 * @returns {string} Formatted date
 */
export function formatDate(date) {
    if (!date) return '';
    if (typeof date === 'string') date = new Date(date);
    const dd = pad2(date.getUTCDate());
    const mm = pad2(date.getUTCMonth() + 1);
    const yyyy = date.getUTCFullYear();

    switch (document.body.dataset.dateFormat) {
        case '%m/%d/%Y':
            return `${mm}/${dd}/${yyyy}`;
        case '%Y-%m-%d':
            return `${yyyy}-${mm}-${dd}`;
        default:
            return `${dd}/${mm}/${yyyy}`;
    }
}

/**
 * Format a time for display.
 * @param {Date|string} date - Date to format
 * @returns {string} Formatted time
 */
export function formatTime(date) {
    if (!date) return '';
    if (typeof date === 'string') date = new Date(date);
    const hours24 = date.getUTCHours();
    const minutes = pad2(date.getUTCMinutes());

    if (document.body.dataset.timeFormat === '%I:%M %p') {
        const period = hours24 < 12 ? 'AM' : 'PM';
        const hours12 = hours24 % 12 || 12;
        return `${pad2(hours12)}:${minutes} ${period}`;
    }
    return `${pad2(hours24)}:${minutes}`;
}

/**
 * Format a date and time for display.
 * @param {Date|string} date - Date to format
 * @returns {string} Formatted date and time
 */
export function formatDateTime(date) {
    if (!date) return '';
    if (typeof date === 'string') date = new Date(date);
    return `${formatDate(date)} ${formatTime(date)}`;
}
