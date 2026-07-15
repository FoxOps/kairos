/**
 * Manages the mobile navigation menu via daisyUI's `drawer` component.
 * `#mobile-drawer` (the checkbox that drives the panel in pure CSS) is
 * driven by this module rather than directly by a <label for> so the
 * burger keeps a real <button> with correct aria-expanded/aria-controls -
 * the checkbox stays the only mechanism that animates the panel, this
 * module just syncs its "checked" state with the button click and the
 * Escape key (a click on daisyUI's own generated overlay checks/unchecks
 * the checkbox directly via its own <label for="mobile-drawer">, without
 * going through this module).
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

        // The daisyUI overlay (or a click on a menu link, which triggers a
        // full navigation anyway) can uncheck the checkbox without going
        // through the burger - keep aria-expanded in sync.
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
