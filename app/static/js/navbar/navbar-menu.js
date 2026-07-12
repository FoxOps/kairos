/**
 * Gère le menu de navigation mobile (burger Bulma).
 * Bulma masque .navbar-menu par défaut sous 1024px tant que
 * .navbar-menu.is-active n'est pas appliqué - Bulma ne fournit que le
 * CSS, pas le JS de toggle.
 */
export class NavbarMenu {
    constructor() {
        this.burger = document.getElementById('navbar-burger');
        this.menu = document.getElementById('navbar-menu');
        this.init();
    }

    init() {
        if (!this.burger || !this.menu) return;

        this.burger.addEventListener('click', () => this.toggle());

        // Fermer le menu après avoir suivi un lien (évite de laisser le
        // menu ouvert par-dessus la page suivante sur mobile).
        this.menu.querySelectorAll('a.navbar-item, a.navbar-link').forEach((link) => {
            link.addEventListener('click', () => this.close());
        });

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isOpen()) {
                this.close();
                this.burger.focus();
            }
        });
    }

    isOpen() {
        return this.menu.classList.contains('is-active');
    }

    toggle() {
        this.isOpen() ? this.close() : this.open();
    }

    open() {
        this.burger.classList.add('is-active');
        this.menu.classList.add('is-active');
        this.burger.setAttribute('aria-expanded', 'true');
    }

    close() {
        this.burger.classList.remove('is-active');
        this.menu.classList.remove('is-active');
        this.burger.setAttribute('aria-expanded', 'false');
    }
}
