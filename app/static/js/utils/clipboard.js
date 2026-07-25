/**
 * Copy-to-clipboard helpers shared by copy-token.js (profile ICS-token
 * page, fixed input ids) and the ICS export modal (dynamic input ids,
 * many buttons reusing the same partial across several pages).
 */

import { getString } from './i18n.js';

export function copyInputValue(inputId, button) {
    const input = document.getElementById(inputId);
    input.select();
    document.execCommand('copy');

    const originalText = button.innerHTML;
    button.innerHTML = `<span class="icon"><i class="fas fa-check"></i></span><span>${getString('copied')}</span>`;

    setTimeout(() => {
        button.innerHTML = originalText;
    }, 2000);
}

export function copyByTarget(event) {
    const button = event.currentTarget;
    copyInputValue(button.dataset.copyTarget, button);
}
