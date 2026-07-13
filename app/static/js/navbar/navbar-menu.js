/**
 * Gère le menu de navigation mobile via le composant `drawer` daisyUI.
 * `#mobile-drawer` (la case à cocher qui pilote le panneau en CSS pur)
 * est manipulée par ce module plutôt que directement par un <label for>
 * afin de garder un vrai <button> avec aria-expanded/aria-controls
 * corrects sur le burger - la case reste le seul mécanisme qui anime le
 * panneau, ce module ne fait que synchroniser son état "checked" avec
 * le clic sur le bouton et la touche Échap (le clic sur l'overlay
 * généré par daisyUI, lui, coche/décoche directement la case via son
 * propre <label for="mobile-drawer">, sans passer par ce module).
 */
export class NavbarMenu {
    constructor() {
        this.burger = document.getElementById('navbar-burger');
        this.drawerToggle = document.getElementById('mobile-drawer');
        this.init();
    }

    init() {
        if (!this.burger || !this.drawerToggle) return;

        this.burger.addEventListener('click', () => this.toggle());

        // L'overlay daisyUI (ou un clic sur un lien du menu, qui déclenche
        // une navigation complète de toute façon) peut décocher la case
        // sans passer par le burger - garder aria-expanded synchronisé.
        this.drawerToggle.addEventListener('change', () => this.syncAria());

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isOpen()) {
                this.close();
                this.burger.focus();
            }
        });
    }

    isOpen() {
        return this.drawerToggle.checked;
    }

    toggle() {
        this.isOpen() ? this.close() : this.open();
    }

    open() {
        this.drawerToggle.checked = true;
        this.syncAria();
    }

    close() {
        this.drawerToggle.checked = false;
        this.syncAria();
    }

    syncAria() {
        this.burger.setAttribute('aria-expanded', this.isOpen() ? 'true' : 'false');
    }
}
