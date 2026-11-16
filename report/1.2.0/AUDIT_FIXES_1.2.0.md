# Kairos 1.2.0 — audit fixes

Companion to [`AUDIT_REPORT_1.2.0.md`](AUDIT_REPORT_1.2.0.md) (the unified
audit, revision B = `b8c736d`, committed unchanged). Every active finding
is mapped below to its fix and to the regression tests that now assert the
intended behavior.

**Branch:** `audit-fixes-1.2.0`, experimental, opened as a draft PR into
`1.2.0`. Do not merge it as-is.

**Method:** the auditor's 31 synthetic proofs
(`/tmp/kairos-audit-b8c736d/tests/test_audit_reproductions.py`) were copied
to `tests/integration/test_audit_1_2_0_regressions.py`. All 31 reproduced
on `b8c736d` before any change. Each assertion that described a defect was
inverted into the intended behavior as its fix landed. The four
assertions that confirmed earlier fixes (F05, F08, the all-on-leave
report and the transition-Friday rule) were kept unchanged. Tests named
`test_fNN_*` are new or inverted.

## Decisions taken with the maintainer

| Topic | Decision |
|---|---|
| F13 "Inclure" | Unticked means **excluded** from on-call rotation. Users who join later are included by default. An empty selection is refused. |
| F03/F09 manual writes | Hard block, with a message naming the rule that blocked the write. |
| F02 identity | Accounts are bound to the issuer and `sub`. `email_verified` is checked only when an existing local account is linked for the first time. `OIDC_TRUST_UNVERIFIED_EMAIL` is an escape hatch for Keycloak, whose admin-created users default to unverified. |
| F15 snapshot | `Shift.group_id` follows the new owner on approve and revert. |

## Finding → fix → tests

| ID | Fix (main files) | Regression tests |
|---|---|---|
| F01 | `app/routes/auth.py::login`: a password POST is refused in SSO-only mode whatever the query string. `auth/login.html` hides the form there. `oidc_auth.py` no longer logs state, compares it in constant time and makes it single-use. | `test_f01_*` |
| F02 | New `User.oidc_issuer` and `User.oidc_subject` columns plus a unique constraint (migration `7d2c1e9a5b30`). `UserManager.sync_user_from_oidc` matches on issuer and subject, refuses a missing `sub`, refuses an account bound to another subject, and refuses `email_verified=false` when linking an existing local account unless `OIDC_TRUST_UNVERIFIED_EMAIL` is set. | `test_f02_*` |
| F03 | `common_helpers.oncall_validation_error()` is the single manual validator and checks spacing. `rules/predicates.oncall_violates_spacing` is shared with the solver. | `test_f03_*` |
| F04 | `oncall_planner.plan_oncalls_for_scope` seeds locked weeks into the `AvailabilityIndex` and the fairness prior counts. | `test_f04_*` |
| F05 | Already fixed at B. | `test_preview_apply_use_same_staffing_rules` (unchanged) |
| F06 | `shift_planner` excludes a shift that overlaps one of the user's on-calls when the block is on. The manual check compares real shift intervals. | `test_f06_*`, `tests/unit/test_helpers.py::test_boundary_day_shift_not_an_overlap` |
| F07 | `SchedulePlan.state_fingerprint` hashes the DB-derived inputs. `AutomationApplyService.apply_plan` serializes applies (process lock and a `FOR UPDATE` sentinel row), rebuilds the request and refuses a stale plan (`ApplyResult.stale`). | `test_f07_*` |
| F08 | Already fixed at B. | `test_ineligible_groups_existing_rows_preserved` (unchanged) |
| F09 | On-call moves check positive duration, the anchor day and hour, and the configured weekly end. `ShiftService.api_create` and `api_update` reject an end at or before the start and multi-day intervals, and check rules on the actual datetimes. | `test_f09_*` |
| F10 | `shift_planner._repair_rotation_coverage` promotes a feasible user from the default slot, or reports `role_uncovered`. `leave_keeps_minimum_headcount` counts per group in `per_group` mode. | `test_f10_*` |
| F11 | `_covering_anchor()` is the latest anchor weekday strictly before the day. The real proposed on-call intervals are carried into shift planning. The leave rebalance window follows `OnCallAnchorRule`. | `test_f11_*` |
| F12 | The request carries the published intervals. A row whose hours differ gets the new `ChangeType` `"updated"`, and `apply_plan` rewrites its times in place. | `test_f12_*` |
| F13 | `AutomationConfig` key `oncall_rotation_excluded`. `queries.get_rotation_order(..., excluded_ids)`, form parsing, templates. | `test_f13_*` |
| F14 | A dry run plans with `rotation_*_override` and persists nothing. A real run aborts if saving the order fails. | `test_f14_*` |
| F15 | `SwapService._new_owner_error` checks the lock, weekend and configured rules. `_exchange_owners` parks the rows on placeholder dates so the swap is safe, and updates the snapshot. Revert re-validates. | `test_f15_*` |
| F16 | Leaves are exported as `VALUE=DATE` all-day events with DTEND = `end_date + 1`. | `test_f16_*`, `tests/unit/test_ics_export.py` |
| F17 | `compute_fairness_metrics` counts every eligible user, including zeros. `rotation_adherence_ratio` is renamed `assignment_stability_ratio`. | `test_f17_*` |
| F18 | The models declare the composite `automation_rules` index and the `ServiceAccount` unique constraint plus plain index, exactly as migrated. | `test_f18_*` (a fresh upgrade has zero autogenerate diffs) |
| F19 | The staffing fallback is resolved before the rest check. The on-call exemption only applies while the final slot is `oncall`. | `test_f19_*` |
| F20 | Locked users are placed first each day and keep their real persisted interval. | `test_f20_*` |
| F21 | `rebalance_after_leave` checks `apply_result.success`. `LeaveService` returns a failure and notifies admins. | `test_f21_*` |

The report's cleanup suggestions also landed. The dead `_SLOT_RANK` was
removed from `shift_planner.py`. The stale "not wired" docstring of
`automation_apply_service.py` was rewritten. An unknown refresh
`oncall_mode` is refused instead of falling through to "regenerate".

## Behavior changes worth knowing before merging

- An on-call can no longer be resized off its configured weekly end.
- For any anchor weekday, the anchor day itself belongs to the departing
  holder, as it already did with Friday. With a Monday anchor, that
  Monday's on-call role now goes to the departing holder.
- A user excluded from rotation is also never the rule-7 rotation-slot
  fallback for shifts.
- A leave whose automatic rebalance fails, partly or fully, now reports
  `rebalance_failed=True` and shows the existing "échoué" flash.
- `GenerationRun` gets an extra `failed` row whenever a stale plan is
  refused.

## Not addressed (out of scope or business decision pending)

- DB-level scope/week uniqueness for on-calls. The F07 check covers the
  reproduced interleavings, but the database still enforces only
  `(user_id, start_time)`.
- Solver termination status and a bound on the generation horizon (the
  200,000-node cap, report §solver quality).
- Holiday, skills and legal-rest semantics that the report lists as
  absent capabilities.
- Retention-dependent fairness history horizon.

## Verification

- `pytest tests/unit tests/integration -n auto`: 2016 passed.
- `tests/integration/test_audit_1_2_0_regressions.py`: 56 tests, all
  passing.
- `ruff`, `black` and `mypy app/` are clean.
- fr/en catalogs: 0 empty and 0 fuzzy entries.
