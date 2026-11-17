# Kairos 1.2.0 — unified audit report

This report consolidates both implementation audits, preserving all **21 finding IDs** and distinguishing historical defects from the latest verified behavior. It supersedes the separate reports for review purposes; the underlying evidence remains revision-specific.

| Revision | Audit date | Branch | Exact audited commit |
|---|---|---|---|
| **A — original audit** | 2026-11-12 | `refs/heads/1.2.0` | `e289e0d59e5fb845cde3a4b88537b2e74781501d` |
| **B — repeat audit** | 2026-11-16 | `refs/heads/1.2.0` | `b8c736d224b8aa1e83e7a9a3b82b260e75c0468d` |

Both remote checks identified a **branch**, with no tag named `1.2.0`. “Current,” “latest,” and status below mean **revision B**, not an assertion about any commits published afterward. The five commits between A and B were reviewed.

## Assessment

Revision B materially simplifies generation: the legacy engine and its toggle are removed, preview and execution use the same planner, replacement-scope filtering preserves excluded groups, pre-window history participates in shift-role lookup, rotation priority is corrected, and staffing-capacity fallback avoids dropping a worker's entire day in some cases.

There are **19 active findings at B: 15 carried forward, one partially fixed, and three newly identified in the repeat audit. Two earlier findings are resolved for the verified scenarios.** “Newly identified” does not necessarily mean newly introduced: only F19 is attributed to a regression in the changed fallback code; F20 and F21 describe pre-existing paths newly confirmed by the repeat audit.

The highest priorities are SSO-only login-policy enforcement, configured spacing in manual/gap-fill paths, final-interval rest validation after capacity fallback, overlap enforcement, and transactional protection against stale plans. Passing tests or `safe_to_apply=True` does not establish complete coverage or compliance with all configured rules.

Severity concerns application impact. No legal-compliance conclusion is made: the source's “legal” spacing language is not backed here by a supplied jurisdiction, agreement, or legal requirement. The audit evaluates actual configured behavior without inventing obligations.

## Unified finding register

| ID | Severity | Finding | Status at B |
|---|---|---|---|
| [F01](#f01) | High | SSO-only password-login policy bypass | Open |
| [F02](#f02) | High, conditional | Unverified OIDC email links to local account | Open; IdP-dependent risk |
| [F03](#f03) | High | Manual on-call writes omit spacing | Open |
| [F04](#f04) | High | Locked/published weeks absent from spacing search | Open |
| [F05](#f05) | High in A | Preview and execution use different engines | Fixed in B |
| [F06](#f06) | High | Planner ignores work/on-call overlap block | Open |
| [F07](#f07) | High | Stale plan applied without input-version validation | Open |
| [F08](#f08) | High in A | Regeneration removes excluded-group assignments | Fixed in B for tested scenario |
| [F09](#f09) | Medium | Actual intervals differ from validated intervals | Open |
| [F10](#f10) | Medium | Coverage disappears after user exclusions | Partially fixed in B |
| [F11](#f11) | Medium | Non-Friday anchors misidentify shift roles | Open; historical lookup subcase improved |
| [F12](#f12) | Medium | Diff omits actual interval changes | Open |
| [F13](#f13) | Medium | Include checkbox does not exclude eligible users | Open |
| [F14](#f14) | Medium | Dry run persists order and resets epoch | Open |
| [F15](#f15) | Medium | Swap constraint gaps and same-day uniqueness failure | Open |
| [F16](#f16) | Medium | Leave ICS omits inclusive final day | Open |
| [F17](#f17) | Low/medium | Fairness denominator and label mislead | Open |
| [F18](#f18) | Low | Migrated and model-created schemas differ | Open |
| [F19](#f19) | High | Capacity fallback can persist insufficient rest | New regression identified in B |
| [F20](#f20) | Medium | Later locked shift exceeds staffing maximum | Newly confirmed in B; pre-existing gap |
| [F21](#f21) | Medium | Unsafe leave rebalance reported as success | Newly confirmed in B; pre-existing path |

The detailed findings include executable scenario names, impact, and suggested correction. A passing defect proof means the undesired behavior was reproduced; it is not a successful fix test.

## Verification across both revisions

| Check | Revision A | Revision B |
|---|---|---|
| Existing unit/integration selection | 2,042 passed; template lint sandbox-blocked | 1,958 passed; template lint sandbox-blocked |
| Isolated template-lint rerun outside sandbox | 1 passed | 1 passed |
| Total existing tests validated across run + rerun | **2,043** | **1,959** |
| Additional focused existing selection | 94 passed, overlapping the full selection | Included in current full selection; no separate total claimed |
| Synthetic audit scenarios | **22 passed**, asserting observed defects | **31 passed**, covering defects and confirmed fixes |
| Fresh SQLite migrations | Upgrade completed; F18 schema drift reproduced | Upgrade completed; F18 schema drift reproduced |
| Bandit | 0 findings | 0 findings |
| Archived tracked-file integrity | 511 files matched A | 509 files matched B |

The lower existing-test count at B reflects removal/replacement of legacy engine code and tests; raw counts do not establish coverage quality. The template failures were sandbox socket restrictions, not template-rule failures, and both passed without application changes on isolated reruns.

The following shared implementation/workflow sections describe **B**. Historical differences are retained explicitly under F05, F08, F10 and the revision notes for other findings.

## Boundaries and reproducibility

No applicable `AGENTS.md` was found in ancestor directories or either repository tree, including hidden-file searches. Existing local untracked files were preserved. Source was extracted with `git archive <SHA>` into `/tmp/kairos-audit-b8c736d`; the previous archive and report remain intact. No application code or existing tests were edited during either audit. This unified Markdown report is a documentation-only deliverable added afterward. The only source-tree addition is `tests/test_audit_reproductions.py`, containing synthetic audit scenarios. No production database, identity provider, notification target, or deployment was contacted. No push or publication occurred.

Review covered current implementation, the five commits since baseline, documentation, configuration, dependency declarations, models/repositories, migrations, planner/solver, manual APIs, swaps, display/export, authentication, permissions, and tests. Existing instance data, environment secrets, backups, screenshots, and operational logs were not used as audit data. Some committed project regression tests describe an operational incident; no personal names or screenshots from that material are reproduced here.

**Validation on this revision:**

- Existing unit/integration suite: **1,958 passed, one template-lint failure** in 133.47 seconds with four pytest workers. The failure was the sandbox denying djlint's multiprocessing socket, not a failed template rule.
- That template-lint test outside the sandbox: **one passed** in 1.06 seconds. Thus all **1,959 existing tests** in the selected suite were validated across the full run and isolated rerun.
- Audit scenarios: **31 passed** in 2.71 seconds. These include both assertions reproducing defects and assertions confirming fixes; they do not mean the defects have been corrected.
- Fresh empty SQLite migrations completed; comparison against model metadata still reproduces F18.
- Python **3.14.8**. All **70 requirement entries** across `requirements.txt` and `docker/requirements.txt` were satisfied by the installed environment, including updated Werkzeug 3.1.9, Authlib 1.9.1, and Black 26.10.1. The repeated entries are not 70 distinct packages. Versions are recorded in the B dependency manifest linked below.
- Bandit: **zero reported findings**. Findings here derive from implementation behavior rather than that scanner.

Reproduce from an isolated checkout/archive of the SHA, copy the accompanying test file into `tests/`, install declared requirements in a virtual environment, and run:

```bash
TEST_DATABASE_URL=sqlite:///:memory: python -m pytest tests/test_audit_reproductions.py -q
TEST_DATABASE_URL=sqlite:///:memory: python -m pytest tests/unit tests/integration -q -n 4
```

The explicit disposable database is important: the repository's testing fixture drops/recreates its test database. Use no production URL. See the revision-specific evidence links below for artifact instructions and logs. The baseline's tests were adapted only for removed interfaces and for fixed assertions; import failures were not counted as reproduced defects.

Limitations: no browser run, real IdP flow, actual reverse-proxy/TLS deployment, external notification/backup delivery, PostgreSQL/MySQL runtime, or dependency-vulnerability database query was performed. No assertion of “no vulnerable dependencies” is made. Top-level version compatibility is verified; the dependency lists are not a complete transitive lock. CI's Python 3.11 was not separately exercised.

## Current components, model, permissions, and workflow

**Stack and entry points.** Flask, SQLAlchemy/Flask-SQLAlchemy, Alembic/Flask-Migrate, Flask-Login, Flask-WTF CSRF, Babel, Flask-Limiter, Talisman, CORS, flask-smorest/Marshmallow, requests/Authlib OIDC integration, icalendar, and Apprise. Jinja pages use Tailwind/daisyUI and FullCalendar CDN assets without a Node build. SQLite is default; PostgreSQL/MySQL drivers are declared. `app/__init__.py:create_app()` wires extensions and blueprints and creates a module-level app. `run.py` supplies migrations/default-data bootstrap and the direct server entry. Docker launches Gunicorn with one worker/four threads; cron handles notifications, backup and retention.

**Model.** A User belongs to one Group; Group independently participates in on-call and work schedules. ShiftType contains same-day integer start/end hours. Shift stores user/type/date, actual datetimes, group snapshot, and locked flag. OnCall stores user/actual datetimes/group snapshot/lock. Leave is an inclusive date span with no approval state or separate absence subtype. Tables also cover swaps, settings/configuration/rules, service accounts/scopes, notifications/targets, audit events and generation outcomes. Shift is unique by `(user_id,date)`; OnCall by `(user_id,start_time)`, not scope/week. There are no required skills, qualifications, personal working patterns, contractual quotas, incident-load records, holidays or many-to-many team memberships.

**Roles.** Admin is a global Boolean, not a team-scoped role. Admins generate/configure schedules and mutate shifts/on-calls. Regular users manage their own leave/profile and join the target-confirmation/admin-approval swap workflow; team calendar visibility is broad. Public read-only `/api/v1/*` uses hashed bearer service-account tokens with scopes, expiration and revocation. Session `/api/shifts` is a separate calendar endpoint. ICS tokens are separate bearer capabilities, can expire, and can request `scope=all`. Display group filters are not tenant authorization. Broad team visibility is implemented behavior, not automatically a vulnerability without a narrower privacy requirement.

**Generation path.** `admin_automation_routes.py:automation_full()` parses action/dates/rotation fields. `AutomationAdminService.generate_full()` saves order and epoch even for preview, then `_build_plan()` aligns the on-call range to an existing straddling assignment while preserving the requested shift start. `planner/adapters.py:build_planning_request()` selects shared/per-group scopes, users, history/leaves, published assignments and locks. `rule_resolution.py` resolves effective group/global rules and type IDs; fallback type resolution may flush new rows. `plan_schedule()` first plans on-calls, merges scope/date→holder mappings in memory, then plans shifts from that same proposed state. `diff.py` compares with publication, and `AutomationApplyService.apply_plan()` persists the diff and a GenerationRun. Full generation/refresh uses an atomic schedule transaction; configuration saves are separate. Preview uses the same algorithm but is recomputed for later execution rather than persisting/replaying an immutable approved snapshot.

`refresh_shifts()` expresses its on-call modes through extra locks: none locks every date, fill_gaps locks published keys, regenerate adds no locks. Leave is committed first; `AutomationAdminService.rebalance_after_leave()` then replans a restricted window with per-entry savepoints. A failed rebalance does not revoke leave. The leave-triggered window still contains Friday-specific expansion arithmetic despite configurable anchors.

Persisted rows feed list pages and `ScheduleService` → FullCalendar JSON. Shift/OnCall datetimes are naive organization-local wall clocks; timezone helpers translate viewer digits, and FullCalendar UTC mode is a serialization convention. ICS attaches the organization zone. Changing the organization timezone reinterprets existing naive datetimes rather than migrating their instants.

**Current generation responsibilities.** `queries.py:get_oncall_users/get_schedule_users/get_rotation_order/align_regeneration_start`; `oncall_planner.py:plan_oncalls_for_scope`; `oncall_solver.py:AvailabilityIndex/_solve_max_filled_weeks`; `shift_planner.py:assign_shift_slots_for_day/plan_shifts_for_scope`; orchestration in `plan_schedule.py`, snapshot construction in `adapters.py`, persistence in `AutomationApplyService`. `oncall_automation.py`, `advanced_shift_automation.py`, their runtime toggle, and the engine-comparison script are gone.

## Business rules actually enforced

| Area | Documented/configured rule | Executable behavior / uncertainty |
|---|---|---|
| Eligibility | Participating groups; Include checkbox | Population comes from group flags. Missing IDs are appended to configured order; checkbox exclusion is ineffective (F13). No skill checks. |
| On-call interval | Default Friday 21:00 → following Friday 07:00; anchor configurable | 154 naive wall-clock hours, with 14 hours between weekly periods. Continuous 24/7 coverage is not represented by on-call alone; intended transition coverage is unspecified. |
| Spacing | Default 2 weeks, configurable integer ≥1 | Solver checks end-to-start gap in both time directions using whole days. Default allows one holder every third weekly anchor. Manual writes bypass it; locked in-window rows do not constrain search. |
| Leave/availability | Inclusive leave dates | On-call excluded by any included date overlapping its period; work excluded by start date. No other personal availability/exclusion source. |
| Shift roles | On-call, rotation, default; configurable type IDs | Today’s holder gets oncall role. Other available last-week holders get rotation; if none, next-week holders; else published/order fallback. Incoming holder now participates on transition Friday. Others get default. |
| Capacity | Per-type daily maxima; rotation coverage described as mandatory | Type cap enforced against already-proposed rows, then fallback to default. No general minimum-by-type or interval coverage optimizer. F19/F20 show validation gaps. |
| Rest | Optional after on-call, default 0 | Filtered for non-oncall roles before capacity fallback; oncall role explicitly exempt. No shift-to-shift recovery, max consecutive workdays, or actual standby-incident workload. |
| Overlap | Coexistence default; optional block | Manual paths partly check it; planner ignores the resolved flag. No arbitrary multi-day interval validator. |
| Weekends | Configurable set, default Saturday/Sunday | Planner skips those days. All eligible users on leave now generates an uncovered-day requirement. No population at all is not reported as a requirement; the intended obligation in that case is unspecified. |
| Locks/manual edits | Lock columns and preserving modes | No lock-setting UI found. Carried locked rows bypass some validations; occupancy not reserved upfront. Manual service writes do not enforce locks. |
| Teams | Shared/per-group modes independently configurable | Ordinary combinations are represented; excluded-scope deletion scenario is fixed. Cross-scope anchor/end-hour interpretation remains ambiguous. |
| Leave minimum | At least one available worker | Uses pooled eligible users even in per-group mode; ignores rest/capacity exclusions. This is not proof of staffed per-team coverage. |

No business specification establishes holiday coverage, skill mixes, maximum hours, standby workload, personal contractual availability, or legal recovery obligations. These are absent capabilities/parameters, not assumed violations. Resolve them before presenting the engine as a general legal-compliance or complete-coverage solver.

## Detailed findings, including resolved history

<a id="f01"></a>

### F01 — High: SSO-only mode still accepts local password login

**Status at B:** Open.

**Revision history:** observed at A and reproduced at B with adapted synthetic scenarios.

`app/routes/auth.py:login` (89 onward) redirects when basic auth is disabled **unless `oidc_error` is present**. That exception also reaches the POST credential handler. Set OIDC enabled and disable basic auth, then POST valid local credentials to `/login?oidc_error=1`: `_user_id` is established. Proof: `test_oidc_only_mode_bypassed_with_error_parameter`.

This still requires a valid local password; it does not authenticate arbitrary users without credentials. It defeats the configured policy and can bypass IdP MFA/access restrictions for accounts retaining a password, including bootstrap admins. Keep an error display path but reject local credential POSTs independently of query parameters when basic auth is disabled. Any emergency local-login capability should be explicit and separate.

<a id="f02"></a>

### F02 — High, conditional: OIDC links an unverified email to an existing local account

**Status at B:** Open; IdP-dependent risk.

**Revision history:** observed at A and reproduced at B with adapted synthetic scenarios.

`oidc_auth.py:extract_user_info_from_token` (326) extracts email/name/roles but drops `sub` and `email_verified`. `user_manager.py:sync_user_from_oidc` (20) finds the local account by email alone and retains admin rights if no role claim is supplied. Proof: `test_oidc_unverified_email_links_local_admin` feeds synthetic userinfo with a different subject and `email_verified=False`; it resolves to the existing local admin.

Exploitability depends on whether the trusted IdP lets a claimant supply the victim email without verifying ownership. The audit did not exercise a real IdP and does not claim all deployments are exploitable. Bind external identity to issuer+subject, define an explicit verified-email linking policy, and reject missing/unverified email when email is used for linking. Validate the full OIDC flow with provider-backed tests. This finding does not rely on accepting an arbitrary unsigned JWT: the code deliberately uses the authenticated userinfo endpoint rather than decoding JWT payloads.

<a id="f03"></a>

### F03 — High: manual on-call creation bypasses the spacing rule

**Status at B:** Open.

**Revision history:** observed at A and reproduced at B with adapted synthetic scenarios.

`OnCallService.add_oncall` → `common_helpers.py:can_add_oncall` (349) checks anchor, leave, overlapping on-calls, and optional work overlap; it never checks `OnCallSpacingRule`. Update has the same omission. Create the same user's on-calls on 2 January and 9 January 2026: both commit, with only **14 hours** between them despite the default two-week gap. Proof: `test_manual_oncall_ignores_spacing`.

Run a single interval validator for manual creation, updates, automation, and swaps as applicable. If manual override is intended, it needs an explicit exception parameter, reason, and visible violation rather than silently ignoring the configured rule.

<a id="f04"></a>

### F04 — High: locked/published weeks do not constrain gap filling

**Status at B:** Open.

**Revision history:** observed at A and reproduced at B with adapted synthetic scenarios.

`adapters.py` excludes every in-window on-call from `existing_oncalls`. `oncall_planner.py:plan_oncalls_for_scope` (100) skips locked weeks in the candidate matrix, then carries them through only after solving. Their holders/intervals are never seeded into solver occupancy. Current `fill_gaps` uses this same locking mechanism for all published weeks.

Proofs: `test_locked_week_not_in_spacing_solver` proposes the same sole user in two consecutive weeks. `test_fill_gaps_doublebooks_locked_holder` reproduces it through the real service: existing 2 January assignment, others on leave for 9 January, refresh with `fill_gaps`; the existing holder receives 9 January too. Both rows commit, violating spacing. Seed fixed locked intervals into search state, count them in fairness, and independently validate the final combined plan.

<a id="f05"></a>

### F05 — High at A, resolved at B: default preview and actual generation execute different rules

**Status at B:** Fixed in B.

**Behavior at A.**
`AutomationAdminService.generate_full` (394), `SettingsService.get_new_automation_engine_enabled` (427): previews always use the new planner; real execution defaults to legacy. Proof: `test_new_engine_default_preview_and_apply_disagree` configures rotation-slot maximum 0. Preview suppresses that slot; real generation creates it. `test_legacy_ignores_staffing_max` directly confirms bypass.

Legacy daily generation constructs Shift objects directly without the manual staffing/rest/overlap checks. Therefore changing a rule in the admin UI does not establish that default generation follows it. Preview and execution must select the same engine/version and input snapshot; expose the selected engine while both implementations exist. Switching to new alone still leaves F04/F06 and other defects.

**Verified change at B.** The legacy generation code and its runtime selection toggle have been removed. `generate_full`, refresh and leave rebalance all use the planner; preview and real generation share `_build_plan`. `test_preview_apply_use_same_staffing_rules` confirms that a capped rotation slot produces the same user/type/date assignments in preview and persistence. The old direct-legacy proof is inapplicable because that implementation no longer exists; this is a verified fix rather than an import failure counted as a result.

Preview and apply are still separate computations and preview still writes configuration (F14); stale input remains possible (F07). Those are separate active findings, not evidence that the old engine-divergence defect remains.

<a id="f06"></a>

### F06 — High: automation ignores the configured on-call/work overlap block

**Status at B:** Open.

**Revision history:** observed at A and reproduced at B with adapted synthetic scenarios.

`ResolvedRules.oncall_shift_overlap_block` is resolved but never consumed by `shift_planner.py`; the on-call planner has no existing-shift snapshots either. With block true, an on-call holder receives a 13–21 Monday shift inside their on-call interval, without a violation. Proof: `test_overlap_block_unused_by_planner`.

Enforce overlap in both planning directions, including existing shifts outside the replacement set. Define how strict block interacts with the “on-call role” work slot; the current flag promises a restriction the planner ignores. Manual on-call overlap checks also use inclusive calendar dates rather than precise actual shift intervals and can reject non-overlapping boundary-day shifts.

<a id="f07"></a>

### F07 — High: snapshot application has no stale-input protection

**Status at B:** Open.

**Revision history:** observed at A and reproduced at B with adapted synthetic scenarios.

`AutomationApplyService.apply_plan` (89) trusts `safe_to_apply`, applies the precomputed diff, and stores the fingerprint without comparing it to current state. There is no row/version guard or scope-level lock. The scope/week uniqueness assumed by the planner is absent from the database.

`test_new_leave_between_plan_and_apply_not_checked`: plan, then commit leave for the chosen holder, then apply—the conflicting on-call commits. `test_two_plans_create_two_shared_oncalls`: two snapshots of an empty window choose different holders; applying both succeeds in an on-call-only population and creates two rows in one shared week. This is a deterministic simulation of an interleaving, not a probabilistic thread race. Normal weekday shifts can cause uniqueness failure and roll back the second whole run, but do not provide a general concurrency guarantee. Gunicorn's four threads permit overlapping requests.

Validate a schedule version/fingerprint under transactional protection before mutation; serialize changes per affected scope/window and enforce the intended slot identity. Reject/replan stale snapshots. Full transaction atomicity alone does not prevent stale decisions.

<a id="f08"></a>

### F08 — High at A, resolved at B: new planner can delete rows outside eligible scopes

**Status at B:** Fixed in B for tested scenario.

**Behavior at A.**
`adapters.py:build_planning_request` (54) derives scopes from currently eligible groups but, without `restrict_to_group_id`, loads **all** published rows in the date range. Rows from a group toggled out of scheduling have no corresponding proposal and become removals. Proof: `test_ineligible_groups_existing_rows_removed` creates an existing shift, disables its group's eligibility, selects per-group scheduling, and gets a removal diff with `safe_to_apply=True`.

This contradicts the scope-preservation intent documented on `clear_period` and differs from the scoped legacy deletion. Restrict replaceable published rows to exactly the scopes being replanned; preserve excluded-scope history unless the administrator explicitly requests deletion.

**Verified change at B.** `adapters.py` restricts published on-calls to planned scopes and anchors within the request; published shifts are restricted to planned eligible shift users. `test_ineligible_groups_existing_rows_preserved` confirms that the earlier excluded-group shift is no longer proposed for removal. The on-call scope filter also falls back to live membership when a row lacks a group snapshot. This resolves the reported scenario; it is not a blanket proof for every team migration or configuration change.

<a id="f09"></a>

### F09 — Medium: interval validation uses different data from what is persisted

**Status at B:** Open.

**Revision history:** observed at A and reproduced at B with adapted synthetic scenarios.

`OnCallService.api_update` checks weekday but not positive duration, configured anchor hour, or expected weekly end. `ShiftService.api_create/api_update` validate rest/overlap using ShiftType's nominal hours but save the supplied actual datetimes.

`test_end_before_start_accepted` saves an on-call ending before it begins. `test_shift_update_checks_type_hours_not_actual_hours` configures five hours' rest after a 07:00 end, then creates an actual 08:00 shift of a nominal 13–21 type; it passes using six nominal hours rather than the actual one hour. Validate actual intervals, positive duration, and explicit date/type consistency. Decide whether arbitrary duration is allowed and enforce that decision consistently. Normal ShiftType administration does reject overnight/inverted hour pairs; that safeguard does not protect these APIs.

<a id="f10"></a>

### F10 — Medium: role coverage is still not repaired after rest exclusions

**Status at B:** Partially fixed in B.

**History at A.** The original coverage finding included a missing uncovered-day signal and assignment-before-exclusion behavior. Its `test_empty_workday_not_reported` used an empty eligible population. That proof alone establishes absence of a requirement, not an independently specified duty to staff a scope with no eligible population. The repeat audit narrows the active finding to the reproducible role-coverage failure after rest exclusion. For the concrete all-eligible-users-on-leave case, B now emits `no_available_user` and the corresponding notification, verified by `test_all_eligible_users_on_leave_reported`.

The all-eligible-users-on-leave case is now reported correctly. That is a confirmed fix, not an active finding. However, `shift_planner.py:plan_shifts_for_scope` selects role holders before filtering rest. If the selected rotation holder is excluded, another available worker can remain on default while rotation coverage is missing.

Proof: `test_rest_exclusion_does_not_repair_rotation_coverage` uses a valid Monday-anchor on-call ending Monday 5 January at 07:00, a two-hour configured rest, and two eligible workers. The former holder is selected for 07–15 and then excluded; the other worker stays 09–17. The result has a rest warning but no unfilled requirement and no rotation shift, although the second worker has no conflicting constraint and could cover it. Re-run role coverage after all filtering and select a feasible replacement. A sole on-call holder likewise cannot cover both roles; the priority and the expected degraded coverage need an explicit rule.

The leave minimum remains pooled across groups (`common_helpers.py:leave_keeps_minimum_headcount`) even in per-group mode; group B's availability can allow group A's last eligible worker to take leave. That count also ignores rest/capacity. Define coverage scope and check resulting staffed intervals, not only nominal available headcount.

<a id="f11"></a>

### F11 — Medium: configurable anchor weekday still misidentifies the current shift role

**Status at B:** Open; historical lookup subcase improved.

**Revision history:** the primary non-Friday-anchor fault was observed at A and reproduced at B; external historical-role lookup was improved at B as qualified below.

`shift_planner.py:_covering_friday` (505) anchors to the working week's Monday and backs up to the configured weekday. This preserves the special Friday working-week convention but does not generalize to arbitrary anchors.

Proof: `test_nonfriday_anchor_shift_roles_are_wrong`: an on-call starts Wednesday 7 January, and Thursday 8 January lies inside it. The role lookup points to Wednesday 31 December instead; the current holder does not receive the oncall role. Derive roles from actual intervals with an explicit transition-day policy, rather than treating arbitrary anchor weekdays as previous-working-week anchors.

The previous external-history lookup gap is fixed for the tested shared-scope case. A separate cross-scope issue remains visible in source: shift planning reconstructs proposed on-call end times and indexes historical anchors using the **shift scope's** anchor rules. If the actual on-call scope has different anchor/end-hour overrides, that reconstruction can disagree with the on-call proposal. Carry actual proposed intervals across the phase boundary. Exact desired role transitions for differing anchors are unconfirmed business semantics, not assumed Friday requirements.

<a id="f12"></a>

### F12 — Medium: “unchanged” ignores actual times and other persisted attributes

**Status at B:** Open.

**Revision history:** observed at A and reproduced at B with adapted synthetic scenarios.

Published-shift snapshots contain only type ID; published-oncall snapshots contain only user ID. Diff/change-type comparison therefore cannot detect changed actual times or anchor settings. Proof: `test_shift_time_edits_invisible_to_diff` changes a persisted shift's start to 02:00; the proposed start differs, yet change type is unchanged. Apply skips it, so regeneration does not repair the discrepancy. Changing ShiftType hours or on-call anchor hours can similarly produce a plan whose displayed intervals differ from saved rows.

Snapshot and compare all scheduling-relevant fields, including interval, lock, scope, and stable identity. Display the actual apply diff rather than silently discarding attribute changes.

<a id="f13"></a>

### F13 — Medium: “Include” checkboxes do not exclude users

**Status at B:** Open.

**Revision history:** observed at A and reproduced at B with adapted synthetic scenarios.

`queries.py:get_rotation_order` (41) appends every eligible user missing from supplied rotation IDs. The form calls those fields `include_<id>` and the admin guide explicitly says check to include. Proof: `test_unchecked_rotation_user_is_added_back` omits one user, but the returned rotation still includes them. An empty list falls back to everyone alphabetically.

Represent population selection and ordering separately. Decide whether deselection excludes the user or just moves them to the end, then align UI, persisted configuration, planner, and documentation.

<a id="f14"></a>

### F14 — Medium: dry run writes configuration and resets rotation phase

**Status at B:** Open.

**Revision history:** observed at A and reproduced at B with adapted synthetic scenarios.

`generate_full` saves/commits order and epoch before testing `dry_run`; it ignores the error string returned by `save_rotation_order`. Rule resolution can also create/flush fallback ShiftTypes; those rows are not independently committed by the resolver. Proof: `test_preview_mutates_rotation_config` confirms preview persists order and epoch without creating OnCall rows.

A preview of another date range can consequently alter later refresh/rebalance behavior. The source explicitly acknowledges that resetting epoch on every generation sacrifices the older overlapping-range rotation guarantee; this is an intentional tradeoff, not an undiscovered randomization bug. Make the tradeoff visible and keep preview configuration in the planning request rather than writing it. Configuration-save failure should abort generation.

<a id="f15"></a>

### F15 — Medium: swaps bypass constraints, and ordinary same-day exchanges fail

**Status at B:** Open.

**Revision history:** observed at A and reproduced at B with adapted synthetic scenarios.

`SwapService._validation_error` (55) checks ownership, leave, and another same-day shift; it does not run configured rest, overlap, eligibility/weekend, or lock checks. Approval updates user IDs without updating group snapshots. Revert deliberately skips validation, although new leave/assignments can arise after approval.

Proof: `test_swapping_same_day_shifts_hits_unique_constraint`: two users each have a shift on the same day, reciprocal exchange is awaiting admin; approval raises SQLite IntegrityError because updates temporarily collide with `(user_id,date)`. No final reassignment commits after rollback. Swaps should validate the resulting schedule and use a safe exchange strategy compatible with immediate uniqueness constraints. Define whether reassignment should preserve the original scope or update its group snapshot; current code mixes those meanings.

<a id="f16"></a>

### F16 — Medium: leave ICS export truncates the inclusive leave interval

**Status at B:** Open.

**Revision history:** observed at A and reproduced at B with adapted synthetic scenarios.

`ics_exporter.py:generate_ics_standard` (15) serializes leave start/end as midnight of start_date/end_date, despite inclusive Leave semantics. Proof: `test_single_day_leave_ics_has_zero_duration` parses the generated ICS and finds identical DTSTART/DTEND for a one-day leave. Multi-day exports omit the final day. Calendar display uses a different inclusive-end adjustment.

Use date-valued all-day events with an exclusive end of `end_date + 1 day`, and test exact parsed values rather than only the presence of DTEND.

<a id="f17"></a>

### F17 — Low/medium: fairness indicators overstate what is measured

**Status at B:** Open.

**Revision history:** observed at A and reproduced at B with adapted synthetic scenarios.

`planner/fairness.py:compute_fairness_metrics` (29) only includes users receiving an on-call or positive undesirable weight. Four eligible people with one assigned week yield one count and **stddev 0**, hiding three zeros. Proof: `test_fairness_omits_zero_assignment_users`. “rotation_adherence_ratio” actually measures non-reassignment against published state; a wholly new arbitrary plan scores 1.0. Shift undesirability weights are hardcoded 0/1/2 and represent role labels, not user preference or legal burden.

Include every eligible user, label stability separately from rotation adherence, and show denominator/history horizon. Do not imply fairness across teams from per-scope counts with different coverage demands.

<a id="f18"></a>

### F18 — Low: migrated schema and model-created schema differ

**Status at B:** Open.

**Revision history:** observed at A and reproduced at B with adapted synthetic scenarios.

`test_fresh_migrations_have_schema_drift` successfully applies all migrations to empty SQLite, then compares Alembic metadata: the migrated database has `ix_automation_rules_rule_type_group_id`, absent from model metadata, and a nonunique token-hash index plus a separate unique constraint where the model uses a unique index. There are three compare operations. **Token hash uniqueness is still enforced**; this is not a missing-uniqueness security finding.

Keep model/index definitions aligned and validate both fresh upgrades and representative version-to-version upgrades. `db.create_all()` tests alone miss this drift. The duplicate-cleanup migration intentionally deletes all but the lowest-ID shift/on-call duplicate; deployments with such historical data need an explicit migration impact review.

<a id="f19"></a>

### F19 — High: the new staffing fallback can persist an insufficient-rest shift

**Status at B:** New regression identified in B.

**New regression in the changed capacity-fallback branch.** `shift_planner.py` validates rest against the initially selected role around lines 371–423, then changes role/type/hours around 426–450 if capacity is full. It does not rerun rest against the replacement interval.

Three proofs establish both variants and persistence:

- `test_fallback_default_bypasses_rest_check`: Monday-anchor on-call ends 5 January 07:00; rest minimum 5h; configured rotation starts 13:00, so the original interval passes with 6h rest. Rotation maximum 0 forces the 09:00 default. The output has only 2h rest and no violation.
- `test_oncall_role_fallback_loses_rest_exemption_justification`: default Friday transition, oncall role maximum 0, rest minimum 11h. The original role is exempt from rest; its replacement becomes a regular 09–17 default shift, 2h after the 07:00 end, still without validation.
- `test_fallback_rest_violation_persists_through_refresh`: the same Friday/cap/rest combination through `AutomationAdminService.refresh_shifts(..., 'none')` actually commits the 09:00 shift. This is not merely an unused pure-planner possibility.

Run every hard constraint on the final interval after any fallback/reassignment. If it fails, try another feasible slot or emit a precise uncovered requirement. Only grant a role-specific exception while the final assignment actually satisfies its documented exception conditions.

<a id="f20"></a>

### F20 — Medium: locked work shifts do not reserve capacity before other users are assigned

**Status at B:** Newly confirmed in B; pre-existing gap.

`shift_planner.py` counts rows already appended to the proposal when enforcing a type maximum. The locked-row branch carries a published type through without checking that maximum. Therefore the outcome depends on user iteration order and can exceed capacity when a locked row is encountered later.

Proof: `test_locked_shift_processed_late_exceeds_staffing_max`: two workers, rotation maximum 1, first worker is last week's holder and receives rotation; the later worker has a locked published rotation shift. Both are proposed in rotation, count 2. Reserve and validate all locked occupancy before assigning unlocked users. If locks intentionally override capacity, report that exception explicitly and avoid assigning additional capacity on top of it. Lock flags have no normal setting UI in this revision; applicability is to existing/programmatically pinned rows, not every default deployment.

<a id="f21"></a>

### F21 — Medium: leave rebalance ignores a whole-plan safety rejection and reports success

**Status at B:** Newly confirmed in B; pre-existing path.

`AutomationAdminService.rebalance_after_leave` calls `AutomationApplyService.apply_plan(..., atomic=False)` but never checks `apply_result.success`. An unsafe plan returns `success=False` before any writes, with an error and empty failed_entries. Rebalance only inspects failed_entries, returns proposal-based results with no failure dates, and `LeaveService` treats the call as successful.

Proofs: `test_leave_rebalance_silently_ignores_unsafe_apply` and `test_leave_api_reports_success_when_locked_rebalance_is_unsafe`. Generate a shift, mark it locked, then add leave on that day. The planner excludes the unavailable worker and detects removal of their locked shift, so application rejects the whole plan. The original shift remains assigned during leave. The leave service returns a nonfailure result; updating the same leave returns `rebalance_failed=False` as well. No failure notification is triggered by the empty failure lists.

Check overall success before interpreting per-entry results. Propagate safety reasons and a rebalance warning through the leave response and notifications. Define the precedence between newly accepted leave and locks; if a conflict requires manual intervention, represent it explicitly. This path existed in the previous optional planner implementation; the repeat audit newly confirms it, rather than claiming the latest commit introduced it.

## Fairness and solver quality at revision B

The solver maximizes filled on-call weeks first. Equal-coverage plans are ranked by variance of prior+proposed counts, then the sum of selected users' positions in the **unrotated** configured order. Candidate traversal is date/epoch rotated. A sum of static positions favors earlier users when counts tie; it is not a measure of whether each week's holder matches that week's rotated first choice.

Prior counts include all loaded external assignments, before or after the window, with no defined lookback horizon or duration weighting. In-window published rows are excluded, including fixed locked weeks (F04). Retention purges therefore change the fairness input. This is count balancing against retained state, not lifetime fairness, hours fairness, incident-load fairness, holiday fairness or entitlement adjusted for availability. Work shifts are assigned by role/priority, with a published-holder/order fallback; there is no horizon-wide shift-burden optimizer. Per-group rotations are not normalized for group size or workload.

New synthetic measurements, no leave/history, default spacing:

| Eligible users | Weeks | Filled | Gaps | Assignment counts |
|---:|---:|---:|---:|---|
| 1 | 12 | 4 | 8 | 4 |
| 2 | 12 | 8 | 4 | 4, 4 |
| 3 | 12 | 12 | 0 | 4, 4, 4 |
| 4 | 12 | 12 | 0 | 3, 3, 3, 3 |
| 5 | 52 | 52 | 0 | 11, 11, 10, 10, 10 |
| 8 | 52 | 52 | 0 | 7, 7, 7, 7, 6, 6, 6, 6 |

The gaps for one/two users follow the configured spacing, not a demonstrated optimization failure. These samples match the baseline distribution; the on-call solver was moved essentially unchanged into `planner/oncall_solver.py`. Existing tests also exercise asymmetric leave, insufficient users, external past/future history, deterministic repeated requests, per-group scoping, and anchor/DST calendar arithmetic.

The search still caps itself at **200,000 recursive nodes**, returning the best plan found without an exhaustion/optimality indicator or gap bound. Claims that an uncovered week proves no legal permutation exists are too strong for arbitrary inputs. Five/eight-user 52-week samples took about 2.54/3.24 seconds locally; these are illustrative single-run measurements, not a production performance guarantee. No explicit generation-range bound was found in the route. Long horizons can encounter recursion depth or large per-user/day work; expose solver termination status and validate horizons.

Pure planning is deterministic for identical full requests excluding generated_at. That does not imply stability across changed windows/history, preview-mutated epoch, order changes or concurrent writes. Scope-independent planning depends on the single-group membership invariant in the present model. F17's zero-denominator omission and mislabeled stability indicator still make displayed fairness look stronger than what is measured.

## Additional robustness, security, and unused-code review

Controls preserved and supported by current source/tests include disabled public registration, password hashing and strength checks, forced changes for assigned passwords, CSRF on session mutations, leave ownership checks, admin-gated schedule writes, safe post-login redirect checks, bearer scope/expiry/revocation checks, and escaping user labels in inspected calendar edit dialogs. No direct user-label XSS exploit was established from those innerHTML paths. The zero Bandit finding count does not contradict the behavioral authentication bugs.

The IdP remains a trust boundary: the custom flow uses token/userinfo endpoints and does not decode arbitrary JWT payloads as trusted claims. Nevertheless local identity is email-linked rather than issuer/subject-linked (F02), `verify_token()` is only a supplied-expiry check, and the callback still logs received/session state at INFO. Remove state values from logs; no real state/token value is reproduced here. Validate full provider policy/flow rather than assuming an Authlib dependency supplies checks the custom path does not call.

Default secure-cookie/HTTPS flags and one-hop ProxyFix trust depend on deployment topology. Admin-managed Apprise URLs intentionally grant outbound destinations; no unprivileged arbitrary-destination configuration path was established. Backup path containment, filesystem symlinks, real external deliveries, and real TLS ingress were not exercised. These are limits of verification, not fabricated remote exploits. Upgrading Werkzeug/Authlib does not change the unchanged application policy flaws reproduced by F01/F02.

Full generation now avoids the baseline's destructive legacy clear-then-commit loop: one atomic apply handles schedule changes. This is a real robustness improvement. It does not solve F07's stale-input decisions; a fingerprint is stored but not checked transactionally. Failed-run recording can still raise if the database stays unavailable after rollback. Leave is accepted/committed before rebalance, so conflict/error reporting is essential (F21). Partial apply counters are incremented before a nested transaction might roll back, and leave presentation is built from proposed rather than committed rows; intended and successful work should be distinguished.

Database uniqueness protects one per-user/day shift and exact duplicate user/on-call starts. It does not enforce scope/week occupancy, full interval overlap, staffing-count races, or simultaneous leave/minimum-headcount decisions. Most validation remains check-then-write. The final safe_to_apply check is an internal consistency/locked-diff guard, not an independent whole-schedule validator. It does not recompute rest, overlap, capacity or coverage from final proposed intervals.

DST tests prove naive wall-calendar boundary construction, not actual elapsed rest across transitions or resolution of nonexistent/ambiguous local hours. Configurable anchor/slot hours can fall in those transitions. Decide elapsed-versus-wall-clock semantics and explicit fold/gap handling if those configurations matter. No legal obligation is assumed.

Confirmed reference-analysis candidates for cleanup or clearer contracts:

- `_SLOT_RANK` in `shift_planner.py` is defined but never read there. Its comments promise weighting/tie-breaking absent from that module's executable code; fairness.py has a separate live copy.
- `ShiftSnapshot` is exported but not instantiated by application code; its absence from requests matters for overlap and actual-interval diffing.
- `AvailabilityIndex.record_assignment()` and `meets_spacing_constraint()` have no production callers found; current search uses its own interval stack/spacing closure. Tests/direct consumers may still use them. Consolidate duplicated predicates before deleting public helpers.
- `run.py:check_database_integrity()` has test callers but no production caller found and checks table names rather than actual database integrity.
- `PlanningRequest.eligible_oncall_users` helps adapter population/fingerprints, while actual assignment follows rotation_order; validate or unify those population representations.
- OIDC group synchronization logs group claims without mapping group membership. It is not implemented membership synchronization.
- Several phase-era comments are now misleading: the apply service still says nothing calls it in production. Update contracts and comments around current behavior.

The old engines and comparison script are actually removed, not candidates for removal anymore. Stored old toggle values, if any, are not read by the current scheduling path. Lower existing-test count than the previous audit reflects test/engine removal and replacement, not a claim of broader coverage from the raw count.

## Recommended order of work

1. Close SSO-only password POSTs and define verified issuer/subject account linking; remove state logging.
2. Fix F19 immediately: validate **final** intervals after fallback, with regression checks through actual persistence. Use a shared validator across manual writes, planner output and swaps.
3. Seed fixed on-call/work occupancy before solving or counting capacity. Define lock-versus-leave precedence and propagate safety rejections instead of success.
4. Add transactional version/locking checks for stale plans; enforce scope/week identity and final whole-plan validity.
5. Preserve actual intervals in snapshots and diffs; re-evaluate role coverage after rest/capacity filtering. Define minima, transition coverage, and team-scoped obligations explicitly.
6. Fix Include semantics, same-day exchanges, and inclusive leave ICS export. Make preview configuration ephemeral and handle configuration-save failure.
7. Align migration/model indexes and add migration-backed fixtures. Correct fairness denominators/labels, define the history horizon, expose search exhaustion and bound generation horizons.

Retain the confirmed fixes and their current regression tests. Audit tests deliberately asserting defects should be inverted to require intended behavior when each fix lands; the positive fix assertions should continue passing unchanged.

## Immutable source evidence index

All links pin the audited commit. The detailed scenarios above identify the relevant path within each function.

| Finding | Source entry |
|---|---|
| F01 | [app/routes/auth.py:91](https://github.com/FoxOps/kairos/blob/b8c736d224b8aa1e83e7a9a3b82b260e75c0468d/app/routes/auth.py#L91) |
| F02 | [app/auth/user_manager.py:20](https://github.com/FoxOps/kairos/blob/b8c736d224b8aa1e83e7a9a3b82b260e75c0468d/app/auth/user_manager.py#L20) |
| F03 | [app/utils/helpers/common_helpers.py:349](https://github.com/FoxOps/kairos/blob/b8c736d224b8aa1e83e7a9a3b82b260e75c0468d/app/utils/helpers/common_helpers.py#L349) |
| F04 | [app/utils/automation/planner/oncall_planner.py:100](https://github.com/FoxOps/kairos/blob/b8c736d224b8aa1e83e7a9a3b82b260e75c0468d/app/utils/automation/planner/oncall_planner.py#L100) |
| F06 | [app/utils/automation/planner/rule_resolution.py:33](https://github.com/FoxOps/kairos/blob/b8c736d224b8aa1e83e7a9a3b82b260e75c0468d/app/utils/automation/planner/rule_resolution.py#L33) |
| F07 | [app/services/automation_apply_service.py:89](https://github.com/FoxOps/kairos/blob/b8c736d224b8aa1e83e7a9a3b82b260e75c0468d/app/services/automation_apply_service.py#L89) |
| F09 | [app/services/shift_service.py:141](https://github.com/FoxOps/kairos/blob/b8c736d224b8aa1e83e7a9a3b82b260e75c0468d/app/services/shift_service.py#L141) |
| F10 | [app/utils/automation/planner/shift_planner.py:161](https://github.com/FoxOps/kairos/blob/b8c736d224b8aa1e83e7a9a3b82b260e75c0468d/app/utils/automation/planner/shift_planner.py#L161) |
| F11 | [app/utils/automation/planner/shift_planner.py:505](https://github.com/FoxOps/kairos/blob/b8c736d224b8aa1e83e7a9a3b82b260e75c0468d/app/utils/automation/planner/shift_planner.py#L505) |
| F12 | [app/utils/automation/planner/diff.py:30](https://github.com/FoxOps/kairos/blob/b8c736d224b8aa1e83e7a9a3b82b260e75c0468d/app/utils/automation/planner/diff.py#L30) |
| F13 | [app/utils/automation/queries.py:38](https://github.com/FoxOps/kairos/blob/b8c736d224b8aa1e83e7a9a3b82b260e75c0468d/app/utils/automation/queries.py#L38) |
| F14 | [app/services/automation_admin_service.py:192](https://github.com/FoxOps/kairos/blob/b8c736d224b8aa1e83e7a9a3b82b260e75c0468d/app/services/automation_admin_service.py#L192) |
| F15 | [app/services/swap_service.py:255](https://github.com/FoxOps/kairos/blob/b8c736d224b8aa1e83e7a9a3b82b260e75c0468d/app/services/swap_service.py#L255) |
| F16 | [app/utils/export/ics_exporter.py:15](https://github.com/FoxOps/kairos/blob/b8c736d224b8aa1e83e7a9a3b82b260e75c0468d/app/utils/export/ics_exporter.py#L15) |
| F17 | [app/utils/automation/planner/fairness.py:29](https://github.com/FoxOps/kairos/blob/b8c736d224b8aa1e83e7a9a3b82b260e75c0468d/app/utils/automation/planner/fairness.py#L29) |
| F18 | [migrations/versions/b94031831198_add_service_account_table.py:28](https://github.com/FoxOps/kairos/blob/b8c736d224b8aa1e83e7a9a3b82b260e75c0468d/migrations/versions/b94031831198_add_service_account_table.py#L28) |
| F19 | [app/utils/automation/planner/shift_planner.py:161](https://github.com/FoxOps/kairos/blob/b8c736d224b8aa1e83e7a9a3b82b260e75c0468d/app/utils/automation/planner/shift_planner.py#L161) |
| F20 | [app/utils/automation/planner/shift_planner.py:161](https://github.com/FoxOps/kairos/blob/b8c736d224b8aa1e83e7a9a3b82b260e75c0468d/app/utils/automation/planner/shift_planner.py#L161) |
| F21 | [app/services/automation_admin_service.py:472](https://github.com/FoxOps/kairos/blob/b8c736d224b8aa1e83e7a9a3b82b260e75c0468d/app/services/automation_admin_service.py#L472) |

See the revision-specific evidence bundles below.


## Historical source evidence for resolved findings

- F05 at A: [engine dispatch and preview/generation split](https://github.com/FoxOps/kairos/blob/e289e0d59e5fb845cde3a4b88537b2e74781501d/app/services/automation_admin_service.py#L394), [default engine setting](https://github.com/FoxOps/kairos/blob/e289e0d59e5fb845cde3a4b88537b2e74781501d/app/services/settings_service.py#L427).
- F08 at A: [published-snapshot construction](https://github.com/FoxOps/kairos/blob/e289e0d59e5fb845cde3a4b88537b2e74781501d/app/utils/automation/planner/adapters.py#L54).
- Resolution at B: [single-planner service dispatch](https://github.com/FoxOps/kairos/blob/b8c736d224b8aa1e83e7a9a3b82b260e75c0468d/app/services/automation_admin_service.py#L192), [scope filtering](https://github.com/FoxOps/kairos/blob/b8c736d224b8aa1e83e7a9a3b82b260e75c0468d/app/utils/automation/planner/adapters.py#L208).

## Revision-specific evidence bundles

Synthetic scenarios must run against their corresponding revision. The original suite references legacy interfaces removed at B; the B suite includes positive assertions for confirmed fixes. Neither suite should be interpreted as an interchangeable all-revision test file.

| Evidence | Revision A | Revision B |
|---|---|---|
| Reproduction instructions | [A instructions](/tmp/kairos-audit-artifacts/README.md) | [B instructions](/tmp/kairos-audit-b8c736d-artifacts/README.md) |
| Synthetic test source | [A: 22 proofs](/tmp/kairos-audit-artifacts/test_audit_reproductions.py) | [B: 31 scenarios](/tmp/kairos-audit-b8c736d-artifacts/test_audit_reproductions.py) |
| Synthetic results | [A results](/tmp/kairos-audit-artifacts/reproduction-tests.log) | [B results](/tmp/kairos-audit-b8c736d-artifacts/reproduction-tests.log) |
| Existing-suite log | [A tests](/tmp/kairos-audit-artifacts/existing-tests.log) | [B tests](/tmp/kairos-audit-b8c736d-artifacts/existing-tests.log) |
| Template-lint rerun | [A rerun](/tmp/kairos-audit-artifacts/template-lint-recheck.log) | [B rerun](/tmp/kairos-audit-b8c736d-artifacts/template-lint-recheck.log) |
| Distribution samples | [A measurements](/tmp/kairos-audit-artifacts/distribution.txt) | [B measurements](/tmp/kairos-audit-b8c736d-artifacts/distribution.txt) |
| Dependency manifest | Matching exact top-level pins recorded in A report | [B installed versions](/tmp/kairos-audit-b8c736d-artifacts/dependencies.json) |
| Source integrity | [511 unchanged files](/tmp/kairos-audit-artifacts/source-integrity.txt) | [509 unchanged files](/tmp/kairos-audit-b8c736d-artifacts/source-integrity.json) |

These evidence links refer to existing local audit artifacts under `/tmp`; copy those bundles when archiving or sharing this report. The report's explanations, scenarios and immutable source links remain readable independently of those local files. No additional test run or new code audit was performed merely to consolidate the reports.
