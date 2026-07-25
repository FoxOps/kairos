/**
 * Copy-to-clipboard for the ICS token page
 * (app/templates/auth/ics_token.html).
 *
 * This file was extracted from an inline <script>: under a strict
 * `script-src 'self'` CSP, an inline block like this one is silently
 * blocked by the browser, which broke every "Copy" button on that page.
 */

import { copyInputValue } from '../utils/clipboard.js';

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
