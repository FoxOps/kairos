/**
 * Gère le menu de navigation mobile (burger). #navbar-menu est masqué
 * par défaut sous le breakpoint `md` via la classe utilitaire Tailwind
 * `hidden` - ce module ne fait que retirer/remettre cette classe et
 * gérer le focus/aria, Tailwind ne fournit que le CSS responsive.
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
        this.menu.querySelectorAll('a').forEach((link) => {
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
        return !this.menu.classList.contains('hidden');
    }

    toggle() {
        this.isOpen() ? this.close() : this.open();
    }

    open() {
        this.menu.classList.remove('hidden');
        this.burger.setAttribute('aria-expanded', 'true');
    }

    close() {
        this.menu.classList.add('hidden');
        this.burger.setAttribute('aria-expanded', 'false');
    }
}
