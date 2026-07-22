/**
 * Reads the server-rendered translation dict (see
 * app/utils/helpers/js_translations.py, injected via base.html's
 * #i18n-strings JSON script tag) - this app has no build step (CSS/JS
 * loaded via CDN only), so there's no i18next-style pipeline
 * available; translation happens server-side
 * (gettext) and ships to the browser as plain JSON, once at page load -
 * unlike the calendar's own events (fullcalendar-config.js), which
 * fetch dynamically from /api/shifts since they depend on whatever
 * date range is currently being viewed.
 */

let _translations = null;

/**
 * Look up a translated string by key.
 * @param {string} key - Key from app/utils/helpers/js_translations.py
 * @returns {string} The translated string, or the key itself if missing
 *   (fails loud-ish in dev without crashing the page in prod).
 */
export function getString(key) {
    if (_translations === null) {
        const el = document.getElementById('i18n-strings');
        _translations = el ? JSON.parse(el.textContent) : {};
    }
    return _translations[key] || key;
}
