/**
 * Applies the theme (data-theme) as early as possible, before the first
 * paint - avoids the theme flash (FOUC) that used to happen when only
 * theme-manager.js (loaded as a module, after the HTML/CSS) set the
 * attribute: the browser would first paint daisyUI's default theme, then
 * switch to the chosen theme once the JS ran.
 *
 * Loaded as a plain <script> (not type="module", not defer/async) at the
 * very top of <head> in base.html: a synchronous script blocks
 * parsing/rendering until it runs, so data-theme is set before anything
 * gets painted. Deliberately duplicates theme-manager.js's resolution
 * logic (localStorage then prefers-color-scheme) - this file must stay
 * standalone, with no import, so it can run without waiting on an ES6
 * module to resolve.
 */
(function () {
    try {
        var stored = localStorage.getItem('theme');
        var theme = stored === 'dark' || stored === 'light'
            ? stored
            : (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
        document.documentElement.setAttribute('data-theme', theme);
    } catch (e) {
        // localStorage unavailable (strict private mode, etc.) - daisyUI's
        // default theme applies, no announcement or blocking error.
    }
})();
