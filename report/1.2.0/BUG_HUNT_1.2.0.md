# Bug Hunt — 1.2.0

> This cycle covers a production report against `1.2.0+dev.17.e289e0d`
> ("the new scheduling system generates bad schedules"), the removal of
> the legacy scheduling engine, and the weekly `Tests` workflow, which
> had been failing. The evidence came from the admin: screenshots of
> what the generator produced ("wrong") next to the admin's manual
> correction ("good") for November and December 2026, plus the
> automation rules of all three scopes (organization, RUN, SOCLE), the
> rotation order and the notifications page. Not attached here: they
> contain real names and e-mails.

## Production configuration that reproduced it

- Shifts scheduled per group, on-calls shared across groups.
- Groups: RUN (3 people, on shifts and on-call) and SOCLE (1 person,
  on-call only). On-call rotation order: SOCLE, then the 3 RUN members.
- RUN's staffing maximums: rotation slot 07h-15h = 1, on-call slot
  13h-21h = 1, default slot 09h-17h = 10.
- Weekend = Saturday and Sunday. On-call runs Friday 21:00 to Friday
  07:00. Minimum spacing between two on-calls = 2 weeks. Rest after an
  on-call = 11h.

## Fixed

1. **One RUN user got no shift at all on Mon–Thu of every other week.**
   Severity: high. Every 2-week cycle, a whole person-week of shifts was
   missing from a generated schedule, and the admin got a misleading
   "nobody available" notification listing about 70 dates.
   - **Root cause:**
     `app/utils/automation/planner/shift_planner.py::assign_shift_slots_for_day()`
     rule 2 gave the rotation slot (07h-15h) to everyone who was on-call
     *last* week **or** will be on-call *next* week. That union was
     introduced by commit b2a225c, so that groups with few on-call turns
     wouldn't sit on the default slot forever. When both neighbours of
     the current on-call week are RUN members, two people got the
     rotation slot. RUN caps it at 1, so the second one hit the
     `staffing_max_reached` branch, which dropped them for the whole day
     (`continue`) instead of giving them another slot.
   - **Example:** in the week of Dec 14 (a SOCLE on-call week), last
     week's holder and next week's holder are both RUN members, so one
     of them got nothing Mon–Thu.
   - **Why Fridays were fine:** the next-week half is deliberately off
     on transition Fridays.
   - **Fix:** the rotation slot is now a priority instead of a union:
     last week's holder if they're in scope, else next week's holder,
     else the existing rotation-order fallback ("rule 7"). The admin
     confirmed this rule against all 8 weeks of the corrected
     screenshots.
   - **Defence in depth:** a user over their slot's staffing maximum
     now falls back to the default slot. They are dropped only if the
     default slot is full too.
   - **Regression tests:** `tests/unit/test_planner_rotation_slot_priority.py`
     reproduces the production configuration (Nov 16 2026 to Jan 8 2027)
     and asserts the admin's corrected schedule day by day.

2. **The first week of a window couldn't see its real "last week"
   on-call holder.** Severity: medium. In
   `plan_shifts_for_scope()`, last week's and next week's holders were
   looked up only among the on-calls this plan proposes. The on-call
   already published just before the window was ignored, so the first
   week's rotation slot fell to the next-week holder instead. Fixed by
   seeding the lookup with the pre-window on-calls from
   `existing_oncalls`; proposed on-calls override them for the same
   week. Regression test: `test_pre_window_oncall_counts_as_last_week`.

3. **Misleading "Aucun shift généré automatiquement (aucun utilisateur
   disponible)" notification.** Severity: medium, because it sent the
   admin hunting for absences that didn't exist. A reached staffing
   maximum was reported through the same notification as "nobody
   available". Meanwhile the planner never reported the real "nobody
   available" case (every eligible user on leave), which the legacy
   engine did. Fixed: a new `no_available_user` unfilled requirement
   feeds that notification and a matching `[WARN]` message. A reached
   staffing maximum is now only a `[WARN]` in the generation result
   (manual assignment would breach the admin's own cap anyway). Tests:
   `test_no_available_user_days_feed_the_unfilled_notification`,
   `test_day_with_every_user_on_leave_is_reported_no_available_user`,
   and the pre-existing
   `test_automation_full_post_generate_notifies_admins_on_shift_unfilled`,
   which now runs on the planner.

4–6. **Three planner adapter bugs that deleted data**, all in
   `app/utils/automation/planner/adapters.py::build_planning_request()`.
   They were hidden while `new_automation_engine_enabled` defaulted to
   off, because every integration test still ran the legacy engine.
   Removing the legacy engine pointed those existing tests at the
   planner, and they failed. Severity: high, since the planner deletes
   whatever it diffs as `removed`.

   4. **With `per_group` on-calls, another group's on-call was deleted.**
      `published_oncalls` was keyed by each row's `group_id` snapshot,
      which is `None` for rows created manually or before the column
      existed. Two groups' concurrent on-calls for the same Friday both
      landed on `(friday, None)`, one overwrote the other, and the
      leftover was diffed `removed`. Fixed: the scope falls back to the
      user's current group, and only on-calls whose scope this request
      actually plans are diffed. Caught by
      `test_rebalance_after_leave_per_group_mode_does_not_lose_other_groups_oncall`.

   5. **The previous week's on-call was deleted.** The datetime-overlap
      query also returns the on-call ending 07:00 on the window's first
      anchor day, which the planner never re-proposes. Appending a
      second "Générer" right after a first one deleted the first one's
      earlier on-call. Fixed: only on-calls *anchored* inside the window
      are diffed; earlier ones are history, already carried by
      `existing_oncalls`. Caught by
      `test_second_generate_after_first_has_no_gap_and_correct_boundary_rotation`.

   6. **Shifts of a group toggled out of the schedule were deleted.**
      Published shifts were only filtered under `restrict_to_group_id`.
      Fixed: published shifts are limited to users that a planned shift
      scope actually includes. Caught by
      `test_generate_full_preserves_shift_for_group_toggled_out_of_schedule`
      and `test_refresh_shifts_shift_recompute_preserves_shift_for_ineligible_group`.

7. **Weekly `Tests` workflow red since 2026-10-12.** Only the `security`
   job failed: `pip-audit` found 11 known vulnerabilities in Werkzeug
   3.1.8, Authlib 1.7.2 and black 26.5.1. Bumped to 3.1.9, 1.9.1 and
   26.10.1, identical across the requirements files. The OIDC unit,
   integration and e2e tests pass on Authlib 1.9.1.

## Legacy engine removal (decisions)

- **Deleted:**
  - `AdvancedShiftAutomation` and `OnCallAutomation`
  - `AutomationAdminService._generate_full_legacy`, `_refresh_shifts_legacy`
    and `clear_period`
  - the `new_automation_engine_enabled` setting with its getter/setter,
    rules-page card and route branch
  - `scripts/compare_automation_engines.py`
- **Relocated, behaviour unchanged:**

  | What | New location |
  |---|---|
  | On-call solver (`AvailabilityIndex`, now snapshot-only; `_solve_max_filled_weeks`) | `planner/oncall_solver.py` |
  | Eligibility, rotation order, gap detection and regeneration-start alignment queries | `app/utils/automation/queries.py` |
  | Role-slot ShiftType resolution | `rules/shift_slots.py::get_shift_type_for_role()` |
  | Leave rebalance (planner path only, no `dry_run`) | `AutomationAdminService.rebalance_after_leave()` |

- **Why a `queries.py` module instead of the existing repositories:**
  `UserRepository.get_for_schedule_group()` sorts by name, while the
  query the planner used doesn't sort at all. The rule-7 fallback
  breaks ties by that order, so moving the queries as-is guarantees an
  unchanged planner population and ordering.
- **No migration:** a leftover `new_automation_engine_enabled` setting
  row is never read.
- **Tests:** legacy-only test files and classes were removed. Those
  that checked engine-agnostic behaviour were ported to the planner:
  - leave rebalance → `tests/unit/test_leave_rebalance.py`
  - shift-type and schedule-user lookups → `tests/unit/test_automation_queries.py`
  - per-group rule overrides → `tests/unit/test_automation_group_scoping.py`
  - N+1 guard → `test_planner_query_count_stable_across_period_length`

  Two tests asserted legacy-specific behaviour and were rewritten to
  the planner's documented contract:
  - The regenerate test now expects "the rotation order decides",
    after the 1.1.1 fix that made the configured order win over the
    current holder. It used to expect the existing holder to be kept.
  - The per-group refresh test now expects one rotation slot per group.
    The legacy engine had a special case that put both people of a
    2-person pair on it.

## Result

- 1990 tests passing (1044 unit, 914 integration, 32 e2e).
- ruff, mypy, black and bandit (`app/`) clean.
- `pip-audit`: 0 known vulnerabilities.
- fr/en catalogs: 0 empty, 0 fuzzy.
