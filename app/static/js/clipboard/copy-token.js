/**
 * Copy-to-clipboard for the ICS token page's raw token input
 * (app/templates/auth/ics_token.html) - the per-resource export URLs
 * on that page now go through the shared _ics_export_buttons.html
 * partial (same Kairos.copyByTarget(event) as /schedule, /oncall,
 * /leave), so this file only covers the one input that partial
 * doesn't own.
 *
 * This file was extracted from an inline <script>: under a strict
 * `script-src 'self'` CSP, an inline block like this one is silently
 * blocked by the browser, which broke every "Copy" button on that page.
 */

import { copyInputValue } from '../utils/clipboard.js';

export function copyToken(event) {
    copyInputValue('tokenInput', event.target.closest('button'));
}
