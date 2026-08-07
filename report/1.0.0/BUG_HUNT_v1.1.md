# Bug Hunt v1.1

> Follow-up to `BUG_HUNT_v1.0.md`, conducted as part of the
> production-readiness audit (batch 9, see `ROADMAP.md`). Targeted the same
> class of issue the previous pass already caught once (a dangling
> `@property`-based FK reference left unguarded in a template) to check
> whether the fix generalized or was only patched at the one call site
> found back then. Every finding below was verified by direct code reading,
> then reproduced empirically (a real test that fails before the fix,
> passes after) - no speculation.

## Fixed in this PR

### 1. MEDIUM — Deleting a user leaves `SwapRequest.requester`/`target_user` dangling, rendered blank on `/swaps` and `/admin/swaps`

**Files**: `app/services/user_service.py` (`UserService.delete()` only
blocks deletion when the user has `Shift`/`OnCall`/`Leave` rows - never
checks `SwapRequest`), `app/models/swap_request.py` (`requester`/
`target_user` are plain `@property` lookups via `db.session.get()`, same
pattern as `shift`/`target_shift` - see `BUG_HUNT_v1.0.md` finding #1 for
the sibling bug on the shift side), `app/templates/swaps.html`,
`app/templates/admin/swaps.html`, `app/templates/confirm_swap.html`.

Same root cause as `BUG_HUNT_v1.0.md`'s finding #1, on the `User` side
instead of the `Shift` side: `requester_id`/`target_user_id` have no
`db.relationship()` and no cascade tying them to `User`, so nothing stops
a `User` row from being deleted while a `SwapRequest` still references it.
This is directly reachable through a normal, allowed workflow: a one-way
shift give-away, once `APPROVED`, reassigns the shift's `user_id` to the
target - the requester then owns zero shifts of their own. If they also
have no on-calls/leaves, `UserService.delete()`'s only guard
(`ShiftRepository.exists_for_user()`/`OnCallRepository`/`LeaveRepository`)
passes clean, and an admin can delete them through the normal
`/admin/users` flow.

Once deleted, `swap.requester`/`swap.target_user` evaluate to `None` at
render time. Unlike the v1.0 finding (`swap.shift.date` - a two-level
access chased through a Jinja filter, which raised a real
`UndefinedError` and 500'd the page), this one is a single dotted
attribute (`swap.requester.name`) directly printed: Jinja's default
`Undefined` class swallows `None.name` into an **empty string** rather
than raising. So this isn't a crash - it's a silent loss of who
requested/received a resolved swap, on both the user-facing history page
and the admin audit-relevant `/admin/swaps` page (11 unguarded call sites
across the 3 templates, none of them had the `{% if %}` guard already
used for `shift`/`target_shift` in the same files).

Reproduced with a real test: approve a one-way give-away, delete the
now-shift-less requester through `UserService.delete()` (succeeds), then
render `/admin/swaps` - confirmed the name cell rendered blank before the
fix, `swap.requester is None` confirmed directly too. Verified red before
the fix (`git stash` on the template change alone), green after.

**Fix applied**: same treatment as the v1.0 shift-side fix - each of the
11 call sites now falls back to a translated `"Utilisateur supprimé"`/
`"un utilisateur supprimé"` string instead of silently rendering nothing.
No business-rule change to `UserService.delete()` itself (blocking
deletion whenever any `SwapRequest` - including long-resolved ones -
still references the user would be a broader, arguably wrong tradeoff:
a resolved swap's historical record isn't a reason to permanently pin a
user account) - deliberately left out of this PR, consistent with the
same call made for the shift-side fix in v1.0.

## Investigated, confirmed not a bug

- **`SwapRequest.reviewer`** (`reviewed_by_id`, nullable) has the same
  dangling-reference shape as `requester`/`target_user` if the reviewing
  admin is later deleted - but it's never dereferenced in any template
  (confirmed by a repo-wide grep), so there's no rendering call site to
  guard. Left as-is; revisit if a future template starts showing "reviewed
  by".
- **`AuditLog.actor`**: already nullable by design and already handled -
  `AuditLogRepository._preload_related()` (batch 1 of this same audit)
  stashes `None` for a missing actor, and the admin-audit-log template was
  already written to handle a `None` actor gracefully.
- **`NotificationTarget` referenced by a deleted/disabled id in
  `User.apprise_shift_target_ids`/`apprise_oncall_target_ids`**: already
  documented and handled - `AppriseNotificationService.notify_to_targets()`
  re-resolves each id at send time and silently skips one that no longer
  exists (see "External notifications (Apprise)" in `CLAUDE.md`).

## Verdict

One real, reproducible finding, fixed with the same pattern already
established in `BUG_HUNT_v1.0.md` for the sibling case - the fix
generalizes cleanly rather than needing a new approach. Nothing found in
this pass blocks production readiness.
