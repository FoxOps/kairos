# Bug Hunt — 1.1.1

> Multi-agent bug-hunt pass over the diff `1.1.0..HEAD` (60 files under
> `app/`, 5539 insertions / 2086 deletions), per
> [`Docs/reference/QA_PROTOCOL.md`](../../Docs/reference/QA_PROTOCOL.md)'s
> Minor tier (chosen despite the patch-numbered version bump: the diff's
> actual scope — a new generation planner, a new API endpoint, and a long
> tail of on-call/rotation fixes — reads as feature-sized). 4 parallel
> `general-purpose` agents, partitioned by area (new planner engine;
> legacy engine + admin services; repositories/routes/API; frontend
> JS/templates + i18n), reviewing for correctness + efficiency only
> (security is a separate major-tier-only pass; style is already
> lint-enforced). A companion documentation-sync pass (2 agents:
> architecture/reference docs, user-facing guides) ran in parallel — its
> findings were folded into `docs:`-equivalent fixes alongside this pass
> rather than a separate report, since most turned out to be one-line
> corrections.

## Fixed in this PR

0. **Delete-confirmation dialog invisible when opened from inside a modal.**
   Found via manual real-browser smoke testing (Playwright driving a real
   Chromium instance through the §4 manual smoke-test checklist), not the
   automated pass above — the Flask test client never executes JS or
   renders layout, so this class of bug is invisible to it and to the
   existing E2E suite's own assertions before this fix. `confirmActionAccessible()`
   (`app/static/js/utils/accessibility.js`) built its confirmation prompt
   as a plain `<div class="modal modal-open">` appended to
   `document.body`. That works fine standalone, but whenever it's
   triggered from inside an already-open **native** `<dialog>` — every one
   of the calendar's new click-to-edit modals for shift/on-call/leave,
   all new this release — it painted *behind* that dialog's browser top
   layer, with no `z-index` able to win against the top layer. The
   confirmation was completely invisible and unreachable by mouse:
   clicking "Supprimer" inside the edit modal appeared to do nothing at
   all, silently defeating delete for these brand-new modals. Fixed by
   making `confirmActionAccessible()` build a native `<dialog>` too (same
   convention as `fullcalendar-config.js::openEditModal`), which gets its
   own top-layer slot and stacks correctly above whichever dialog was
   already open. Updated the 2 pre-existing E2E regression tests
   (`TestDeleteConfirmationModal`) whose selector targeted the old
   div-based markup. Severity: high — this broke the Delete action on
   every new calendar modal for every mouse user, silently (no error, no
   visible feedback at all).

1. **`OnCallService.add_oncall()` hardcoded on-call hours despite a
   configurable anchor weekday.** The weekday check already resolved
   `OnCallAnchorRule.resolve(group=user.group)["weekday"]`, but
   `start_time`/`end_time` were still built with a hardcoded `hour=21`/
   "7 days minus 14 hours" instead of the same rule's own
   `start_hour`/`end_hour`. A group configured with non-default anchor
   hours got on-calls silently created at 21:00→07:00 regardless
   (`can_add_oncall()`'s own hour check then rejected the mismatch,
   which is what surfaced this while writing the regression test).
   Fixed to build both times from the resolved rule, matching the
   existing pattern in `oncall_automation.py`/`shift_planner.py`.
   Regression test: `test_add_oncall_uses_configured_anchor_hours`.

2. **`login_manager.login_message` untranslated for non-French
   visitors.** The message was a raw string literal assigned directly,
   invisible to `pybabel extract` (only calls to a recognized keyword
   are scanned) — its catalog entry had gone obsolete in both `fr.po`
   and `en.po`, so `gettext()` had no live translation and every
   locale saw the raw French text. Wrapped in a new `N_()` identity
   marker (Babel's default `N_` extraction keyword — flags the string
   for extraction without translating it immediately, preserving the
   existing `localize_callback = gettext` lazy-per-request design).
   Catalogs regenerated (fr/en both 0 empty/0 fuzzy). Regression test:
   `test_login_message_renders_in_english`.

3. **`AutomationAdminService.save_rotation_order()` non-atomic.** Wrote
   the rotation epoch and rotation order as two independently
   auto-committing calls (`AutomationConfig.set_config()` commits every
   call); a failure on the second write left the epoch durably
   persisted without its matching order, breaking the invariant the
   whole rotation-offset feature depends on (epoch and order must move
   together). `AutomationConfig.set_config()`/`set_rotation_order()`/
   `set_rotation_epoch()` gained an optional `commit=False`, and the
   service now does both writes in one transaction. Regression test:
   `test_epoch_write_rolled_back_when_order_write_fails`.

4. **`GET /api/v1/oncall/current?group_id=` silently dropped a second
   concurrent on-call.** With `group_id` given, the view returned only
   `oncalls[0]`; a genuinely concurrent second on-call in the same
   group (e.g. an admin-created overlap) was silently invisible to a
   monitoring/alerting integration — exactly the kind of data loss this
   endpoint exists to avoid. Since this endpoint ships for the first
   time in 1.1.1 (no external consumer depends on the documented single-
   object shape yet), fixed the contract directly: falls back to the
   same array shape as the `group_id`-omitted case when more than one
   on-call is active. `Docs/api/API.md` and the `CHANGELOG.md` entry
   updated to match. Regression test:
   `test_two_concurrent_actives_same_group_returns_array`.

Also fixed a stale docstring on
`SettingsService.get_new_automation_engine_enabled()` that claimed
`rebalance_after_leave()` isn't gated by the toggle at all — it is,
since the phase 7 follow-up commit; the docstring just hadn't been
updated to match.

## Documentation fixed alongside this pass

Not bugs in running code, but stale claims the doc-sync pass found
against this same diff (see the two agent reports for the full detail —
summarized here since most were one-line corrections):

- `CLAUDE.md`: `oncall_shift_overlap`'s default flipped to `False` this
  cycle (was documented as "on by default"); `generate_full()`'s
  per-group-loop description was legacy-engine-only, not universal;
  added a full "The new pure planner engine" section (previously
  undocumented entirely — the dual-engine cutover, the
  `new_automation_engine_enabled` toggle's default-off state,
  `GenerationRun`, the `group_id`/`locked` snapshot columns' actual
  purpose); corrected a stale claim that `Shift`/`OnCall` have no
  `group_id` column of their own (they do now — a planner-locking
  snapshot, not a general group-membership field; `count_for_group()`'s
  own docstring in both repositories had the same staleness, fixed too).
- `Docs/architecture/ARCHITECTURE.md`: added `GenerationRun` (models),
  `AutomationApplyService` (services), and `planner/` (utils/automation
  tree) — all missing; corrected "single shift generation engine" (two
  now coexist).
- `Docs/architecture/ERD.md`: added `Shift.group_id`/`.locked` and
  `OnCall.group_id`/`.locked` columns, a `GENERATION_RUN` entity +
  relationship, and a Notes bullet for both.
- `Docs/guides/ADMIN_GUIDE.md`: the on-call-anchor troubleshooting entry
  still claimed a hardcoded Friday error message (now generic, per-group
  configurable); staffing rule wording still described a removed
  min/mandatory shape (max-only since this cycle); the removed
  "Créneaux obligatoires" rule was still documented; `oncall_shift_overlap`
  still said "on by default" (now off); the new
  `new_automation_engine_enabled` toggle wasn't documented at all.
- `Docs/guides/USER_GUIDE.md`: claimed shift generation has "no
  per-day/per-shift-type headcount setting" and is "not independently
  configurable" / "fixed rules, not configurable through the UI" — both
  false (`staffing_limits`/`shift_slots` are admin-editable, predating
  even this cycle); the "Default business rules" section listed rules
  with no mention they're admin-configurable and omitted 2 existing
  rule types (`rest_after_oncall`, `oncall_shift_overlap`) entirely.
- `app/templates/admin/automation/rules.html`: the engine-toggle's own
  in-app description claimed the leave-rebalance "continues to use the
  old engine in all cases" — stale since the phase 7 follow-up gated it
  by the same toggle. Fixed the French copy and added a proper English
  translation (the string had no live `en.po` entry at all before this).

## Investigated, deferred (real but narrow, not fixed this release)

- **`shift_planner.py`: mixed per-group on-call anchor weekdays.** When
  `shift_scheduling_mode="shared"` and `oncall_scheduling_mode="per_group"`
  with two on-call groups configured with *different* `oncall_anchor`
  weekdays/hours, `plan_shifts_for_scope()` uses the shift-scope's own
  resolved rules uniformly for every `oncall_group_ids` entry instead of
  each group's own resolved anchor — plausible that an on-call belonging
  to the non-owning group gets bucketed under the wrong Friday key or a
  mis-reconstructed end time for `rest_after_oncall`. **Not fixed**: the
  new planner is off by default in production (`new_automation_engine_enabled`),
  and this needs all three of (new engine enabled) + (shift shared /
  on-call per-group) + (different per-group anchors) to manifest — a
  narrow combination with zero current production exposure. Worth fixing
  before this engine ever becomes the default; tracked here rather than
  silently dropped.
- **`oncall_automation.py`: weaker fairness-key branch-and-bound
  pruning.** The new `fairness_key` tie-break path (only ever supplied
  by the new planner) relaxes pruning from `<=` to `<`, exploring more
  of the search tree for the same input under the unchanged
  `_MAX_SEARCH_NODES` (200,000) cap — plausible that a large
  window/candidate pool now hits the cap before exploring enough of the
  tree for a fair assignment, with no signal to the caller that the
  search was cut short. **Not fixed**: same off-by-default exposure as
  above, and this app's real-world team sizes are well below what would
  approach the cap (see `Docs/reference/PERFORMANCE_OPTIMIZATION.md`'s
  stated scale). Worth a `nodes_explored` warning log if the new engine
  becomes default.
- **Efficiency-only findings, all in code paths gated off by default or
  already small at this app's scale** (per this project's stated
  "acceptable at this app's scale" philosophy — see
  `Docs/reference/PERFORMANCE_OPTIMIZATION.md`): `shift_planner.py`'s
  `staffing_limits` current-count scan (O(days²×users) worst case,
  re-scans `proposed` per user per day instead of maintaining a
  counter); `automation_apply_service.py`'s per-diff-entry
  `db.session.get()`/lookup queries instead of a batch prefetch;
  `presentation.py`'s per-id `User`/`ShiftType` lookups instead of one
  `IN` query (partially mitigated by SQLAlchemy's identity map);
  `GenerationRun._cached_actor`'s unused preload sentinel (copied from
  `AuditLog`, but no repository sets it yet — latent, not a bug today,
  since no listing UI exists for `GenerationRun` yet);
  `OnCallRepository.list_active()`'s `joinedload` + explicit `.join()`
  producing a redundant double-join to `user` — confirmed this is the
  **same pre-existing pattern** as `list_all_with_user()` in the same
  file (predates this diff), so left as-is for consistency rather than
  a one-off fix.

## Investigated, confirmed not a bug

- **Legacy engine reachability.** `AdvancedShiftAutomation.generate_full_schedule`/
  `OnCallAutomation.generate_oncall_schedule` are confirmed still
  reachable and are in fact the *default* production path
  (`new_automation_engine_enabled` defaults `False`) — not dead code.
  Only the already-removed `mandatory_shift`/`staffing_limits`-min
  coverage-gap helpers (documented in `CHANGELOG.md`) were genuinely
  dead and correctly removed.
- **`generate_full()`'s dry-run preview always uses the new engine,
  even when the toggle is off for real generation.** Acknowledged
  directly in the method's own docstring as intentional: an admin
  previewing before opting in sees exactly what they'd get if they did.
  A diagnostic legacy-vs-new comparison script
  (`scripts/compare_automation_engines.py`) exists specifically because
  the two engines are different implementations by construction and can
  diverge — not a bug, the documented purpose of that tool.
- **`handle_two_users_case()` appearing to give every user the same
  "07h-15h" slot on every day, initially flagged as a severe
  regression.** First smoke-test pass hit this via an artificial
  sequence: generate on-calls/shifts for a single user only (leaving
  the surrounding month with no on-call coverage at all), add a second
  user afterward, then add a leave — the ±30-day automatic rebalance
  window landed almost entirely on days with no on-call holder at all,
  and the 2-user role-split code path (correctly) has no defined
  behavior for "2 available users, nobody on-call that day," falling
  back to 07h-15h for both. **Retested end-to-end from a clean 2-user
  setup** (both users present before the first generation, normal
  on-call coverage throughout): the 13h-21h/07h-15h split works
  correctly for every day, including through a leave-triggered
  rebalance. Not a regression — confirmed by re-running the full
  smoke-test checklist start to finish a second time. The narrow
  "2 users, no on-call active that day" fallback behavior is still
  worth a follow-up decision (split 07h-15h/09h-17h instead of doubling
  up?) but isn't release-blocking and wasn't introduced this cycle.

## Verdict

5 real, user/admin-facing bugs fixed with regression tests (all green,
2008 unit+integration tests plus 20 e2e browser tests, `make all` clean)
— 4 from the automated multi-agent pass and 1 (the highest-severity one)
from manual real-browser smoke testing, underscoring why that step stays
manual/real-browser rather than something the automated pass alone can
catch. 2 more small fixes (stale min/mandatory-staffing text on the
automation dashboard, a corrupted/duplicated `en.po` translation) found
and fixed during a full second smoke-test redo requested to double-check
the release. 2 additional plausible-but-narrow findings documented and
deliberately deferred — both require the new planner engine to be turned
on, which it isn't by default in production, so current release risk is
zero; both are tracked here for whoever eventually flips that toggle to
default-on. One initially-alarming finding (2-user shift assignment
appearing broken) turned out to be a false alarm from an artificial
repro sequence, not a real regression — confirmed via a clean retest,
see above. A double-digit set of documentation staleness findings
(architecture docs, admin/user guides, in-app UI strings) fixed
alongside. No blockers for the 1.1.1 release.
