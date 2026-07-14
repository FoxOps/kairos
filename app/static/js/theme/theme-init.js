/**
 * Applique le thème (data-theme) le plus tôt possible, avant le premier
 * rendu - évite le flash de thème (FOUC) qui se produisait quand seul
 * theme-manager.js (chargé en module, après le HTML/CSS) posait
 * l'attribut : le navigateur peignait d'abord le thème par défaut de
 * daisyUI, puis bascule vers le thème choisi une fois le JS exécuté.
 *
 * Chargé en <script> classique (pas type="module", pas defer/async) tout
 * en haut de <head> dans base.html : un script synchrone bloque le
 * parsing/rendu jusqu'à son exécution, donc data-theme est posé avant
 * que quoi que ce soit ne soit peint. Duplique volontairement la logique
 * de résolution de theme-manager.js (localStorage puis
 * prefers-color-scheme) - ce fichier doit rester autonome, sans import,
 * pour s'exécuter sans attendre la résolution d'un module ES6.
 */
(function () {
    try {
        var stored = localStorage.getItem('theme');
        var theme = stored === 'dark' || stored === 'light'
            ? stored
            : (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
        document.documentElement.setAttribute('data-theme', theme);
    } catch (e) {
        // localStorage indisponible (mode privé strict, etc.) - le thème
        // par défaut de daisyUI s'applique, pas d'annonce ni d'erreur bloquante.
    }
})();
