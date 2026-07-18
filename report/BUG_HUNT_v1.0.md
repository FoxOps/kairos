# Bug Hunt v1.0

> Targeted pass on the app's most recent features (multi-timezone,
> multi-language, date/time formats, audit trail, Apprise notifications,
> 3-party shift-swap workflow, public REST API v1, MySQL/MariaDB support,
> `SettingsService`, backups) - the youngest, and therefore least
> battle-tested. The historical core of the scheduling feature has already
> been through several documented passes (`report/BUG_HUNT_REPORT.md`,
> `report/CHASSE_AU_BUG.md`) and isn't repeated here. Every finding was
> verified by direct code reading then, when possible, reproduced
> empirically (a real test that fails before the fix, passes after) - no
> speculation.

## Fixed in this PR

### 1. HIGH — Deleting a shift referenced by an active swap crashes `/swaps`, `/admin/swaps` and `/swaps/<id>/confirm`

**Files**: `app/services/shift_service.py` (no deletion path checks
active `SwapRequest`s), `app/models/swap_request.py` (`SwapRequest.shift`
is a plain `@property` doing `db.session.get(Shift, self.shift_id)` - not
an ORM relationship, see the model's docstring),
`app/templates/swaps.html`, `app/templates/admin/swaps.html`,
`app/templates/confirm_swap.html`.

None of `ShiftService`'s deletion paths (single or bulk - day/week/user/
everything) check whether a `SwapRequest` still references the shift.
Once the `Shift` row is deleted, `swap.shift` silently returns `None`.
All three templates dereferenced `swap.shift.date`/
`swap_request.shift.date` **with no guard at all** - unlike
`target_shift`, always protected by `{% if swap.target_shift %}`. Result:
`jinja2.exceptions.UndefinedError: 'None' has no attribute 'date'`, an
unhandled exception that crashes **the entire page** for every user with
that request in their list (including every admin on `/admin/swaps`) -
not just the affected row. Reproduced and confirmed with a real test
(direct deletion of the referenced shift, then `GET /swaps` ->
`UndefinedError`) before the fix.

Plausible and common triggering scenario: an admin's bulk deletion of a
week/user, with no warning about an ongoing swap.

**Fix applied**: defensive guard in the 4 affected template spots
(`{% if swap.shift %}...{% else %}<span>Deleted shift</span>{% endif %}`),
same pattern already used for `target_shift`. The service layer was
already correct on its side: `POST /swaps/<id>/confirm` goes through
`SwapService.confirm_swap()` -> `_validation_error()`, which already
handles `shift is None` cleanly (`"Shift not found"`) - only the `GET`
render (raw display in the template) had the gap. No business-rule change
(blocking the deletion, auto-cancelling the request): a broader product
decision, deliberately left out of this PR - see "Not addressed" below.

Regression tests added: `tests/integration/test_swap_routes.py`
(`test_swaps_page_survives_deleted_shift`,
`test_confirm_page_survives_deleted_shift`,
`test_admin_swaps_page_survives_deleted_shift`).

### 2. MEDIUM — The audit log's domain filter silently drops 2 real domains

**File**: `app/routes/admin_audit_routes.py`

`ACTION_DOMAINS` (used to populate the filter dropdown on
`/admin/audit-log`) listed `auth, group, leave, oncall, profile, setting,
shift, shift_type, swap, user` - but `AuditService.log()` is indeed
called with `"service_account.*"`
(`app/services/service_account_service.py`) and
`"notification_target.*"` (`app/routes/admin_notification_target_routes.py`),
two domains introduced by recent features. An admin therefore couldn't
filter the history on API-key or external notification-target activity -
and worse, `action_prefix = f"{domain}." if domain in ACTION_DOMAINS else
None` (line 50) means a hand-built `?action_domain=service_account` URL
neither filters nor errors: it silently returns the full unfiltered list,
which could wrongly suggest the filter worked.

**Fix**: added `"service_account"` and `"notification_target"` to
`ACTION_DOMAINS`. The template already consumes this list dynamically
(`{% for domain in action_domains %}`), no template change needed.

### 3. LOW — `SettingsService.get_public_base_url()` violates its own documented "a present Setting always wins" rule

**File**: `app/services/settings_service.py`

`set_public_base_url(None)` stores an empty string (`url or ""`) - the
only setter in this module that deliberately persists a falsy value, to
represent "explicitly cleared". But `get_public_base_url()` did
`if value: return str(value)`, so an empty `Setting` row was treated as
"absent" and silently fell back to the `PUBLIC_BASE_URL` environment
variable. An admin who explicitly clears the value via `/admin/settings`
therefore doesn't get "no override" as expected, but silently gets the
previous environment value - contradicting the rule documented in
CLAUDE.md ("Configuration: two parallel systems"): *"a Setting row, if
present, always wins"*.

**Fix**: `if value is not None` (instead of `if value:`) -
`Setting.get()` only returns `None` when no row exists at all at all (see
its own docstring), so this check correctly distinguishes "never
configured" from "explicitly cleared". Regression test added
(`tests/unit/test_settings_service.py::test_explicit_clear_does_not_fall_back_to_env`).

### 4. Cross-cutting bug found while digging into Bandit B104: `PROMETHEUS_ENABLED` never wired up

Documented and fixed in `report/SECURITY_AUDIT_v1.0.md` (section
"Fixes applied") rather than repeated here - found during the security
audit, not this pass, but worth a cross-reference: the `/metrics`
feature was structurally unreachable in a real deployment, masked by a
test that bypassed the real `create_app()` path.

## Not addressed (identified, documented, product decision out of scope)

### LOW/MEDIUM — No optimistic locking on swap-workflow transitions

**File**: `app/services/swap_service.py` (`approve_swap`, `confirm_swap`)

Each transition method reads `swap_request.status`, validates, then
writes - with no row lock (`SELECT ... FOR UPDATE`) nor version check
between the read and the `commit()`. Two genuinely concurrent requests
(two admins clicking "Approve" at the same time, or a double submission
of `/confirm`) can both pass the `is_awaiting_admin()`/
`is_awaiting_target()` checks before either commits, leading to double
processing (shift reassigned twice, duplicated notifications).
*Sequential* double submissions are already safe (the second request
re-reads the already-updated status and is correctly rejected) - only
real concurrency is at risk. Not exploitable for a privilege escalation,
but a real data-integrity gap in a workflow whose whole point is "3-party
validation, re-validated at every step". A fix (row lock or version
counter) was deliberately not applied here - a transactional-behavior
change that deserves its own review, not a one-off fix in a bug-hunt
pass.

### LOW — `SettingsService.set_pagination()`/`set_backup_retention()` aren't atomic across their two settings

**File**: `app/services/settings_service.py`,
`app/models/setting.py::Setting.set()`

`Setting.set()` commits internally on every call. `set_pagination()`
validates `items_per_page <= max_per_page` together then calls
`Setting.set()` twice - two independent transactions, each already
committed. If the second call fails after the first succeeded, the
`except` only rolls back the current session: the first value stays
durably committed, leaving the two settings in a combination that was
never validated together. Low probability (requires a transient DB error
mid-request), but a real gap given the validation is explicitly presented
as a joint constraint. Not fixed: would require either a single explicit
transaction in `Setting.set()` (a structural change affecting every
caller), or validating before any `commit()` in each affected setter - an
architecture decision, not an isolated fix.

### LOW — API key expiry at midnight UTC, not end of day

**File**: `app/routes/admin_service_account_routes.py`,
`app/models/service_account.py`

The admin form takes a plain date (`<input type="date">`), converted to
a `datetime` at midnight. An admin who picks "2026-08-01" thinking the
key works until the end of that day will find it already invalid at
00:00 UTC that same day. Errs on the safe side (expires early, never
late) so not a security issue, but a real semantic gap between what the
UI suggests and what the check actually does. Not fixed: changing this
(moving to 23:59:59 or end-of-day in the admin's timezone) is a minor but
visible product choice, deserving explicit confirmation rather than a
silent change to credential-expiry behavior.

## Verified and dismissed (investigated, code correct)

- **API rate limiting keyed by service account vs IP**
  (`app/api/rate_limit.py`, `app/auth/service_account_auth.py`): initial
  suspicion that the blueprint's `before_request` hook would run after
  the app-level rate-limit check, disabling the per-account key. Verified
  in Flask/Flask-Limiter's source: route-level `@limiter.limit()`
  decorators are deliberately deferred to the view call (after every
  blueprint `before_request` hook) - confirmed empirically.
  `g.service_account` is indeed populated before the per-account limit
  applies. Not a bug.
- **Multi-timezone conversion** (symmetric read/write, org-tz <->
  viewer-tz): consistent on both sides; DST edge cases are an inherent
  trade-off of any `zoneinfo`-based system, already an accepted and
  documented compromise, not a regression.
- **`force_locale()` in notifications** (weekly emails, in-app
  notifications): every persisted/multi-recipient message is indeed built
  per-recipient inside its own `force_locale()` block.
- **`flask.g` cache for `get_date_format()`/`get_time_format()`**:
  correctly scoped per request, no risk of a stale value.
- **Path traversal / S3 temp-file cleanup in `BackupService`**: the
  final `startswith(local_dir + os.sep)` check correctly catches `../`
  and absolute-path injection (verified directly); the S3 temp file is
  cleaned up via `response.call_on_close()`.
- **Double booking of the same shift as `target_shift` by two concurrent
  requests**: reachable at confirmation time, but `approve_swap()`
  correctly re-validates and rejects the second request at approval time
  - a UX annoyance, not data corruption.
- **`normalize_database_uri()` for MySQL/MariaDB**: correctly rewrites
  bare schemes, leaves an already-explicit `+driver` untouched; no raw
  dialect-dependent SQL found elsewhere in `app/`.

## Verdict

The recent features are, overall, well built: consistent error-handling
conventions (fire-and-forget vs raising, documented and followed),
systematic re-validation at every step of the swap workflow, symmetric
and correct timezone/language handling. The only **high-severity** issue
(#1) was fixed in this PR - it was a real gap (nothing in the shift
deletion path knew a `SwapRequest` could reference it) and its failure
mode (a whole page 500ing, unrecoverable without DB access) justified a
fix before v1.0 rather than a mere writeup. The three unaddressed items
are documented with their reason for being set aside (a product decision
or a broader structural change, not an oversight) - to be explicitly
decided before or after the v1.0 launch, depending on the team's risk
tolerance.
