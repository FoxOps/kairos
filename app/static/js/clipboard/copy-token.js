/**
 * Copie-vers-presse-papiers pour la page de token ICS
 * (app/templates/auth/ics_token.html).
 *
 * Externalisé depuis un <script> inline (Phase 6 a mis en place une CSP
 * script-src 'self' stricte - ce bloc était bloqué silencieusement par le
 * navigateur, cassant tous les boutons "Copier" de cette page).
 */

function copyInputValue(inputId, button) {
    const input = document.getElementById(inputId);
    input.select();
    document.execCommand('copy');

    const originalText = button.innerHTML;
    button.innerHTML = '<span class="icon"><i class="fas fa-check"></i></span><span>Copié !</span>';

    setTimeout(() => {
        button.innerHTML = originalText;
    }, 2000);
}

export function copyToken(event) {
    copyInputValue('tokenInput', event.target.closest('button'));
}

export function copyUrlShiftsAll(event) {
    copyInputValue('urlShiftsAllInput', event.target.closest('button'));
}

export function copyUrlShiftsMy(event) {
    copyInputValue('urlShiftsMyInput', event.target.closest('button'));
}

export function copyUrlOncallAll(event) {
    copyInputValue('urlOncallAllInput', event.target.closest('button'));
}

export function copyUrlOncallMy(event) {
    copyInputValue('urlOncallMyInput', event.target.closest('button'));
}

export function copyUrlLeavesAll(event) {
    copyInputValue('urlLeavesAllInput', event.target.closest('button'));
}

export function copyUrlLeavesMy(event) {
    copyInputValue('urlLeavesMyInput', event.target.closest('button'));
}
