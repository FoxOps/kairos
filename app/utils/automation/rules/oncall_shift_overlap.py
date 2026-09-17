"""Configurable "block a shift and an on-call overlapping in time for
the same user" guard.

Policy reversal (automation engine rework, phase 1-3): a week-long
on-call naturally overlaps its holder's normal daytime shift hours -
this is expected, not a conflict, so `block` now defaults to False.
This flips the rule's original default (True), which treated any
shift/on-call overlap for the same user as a data-integrity problem to
reject. On reflection there is no other genuine double-booking case
left for this rule to guard: shift-vs-shift and oncall-vs-oncall
double-booking are already unconditionally prevented elsewhere
(`uq_shift_user_date`/`uq_oncall_user_start_time` unique constraints,
and the unconditional overlapping-on-call/overlapping-shift checks in
`can_add_oncall`/`is_user_on_shift`) - the only thing this rule has
ever actually gated is a shift and an on-call for the same user
overlapping, which is normal on-call operation, not a bug. Some
organizations may still want the old stricter behavior (e.g.
contractual reasons unrelated to Kairos's own on-call/shift slot
design) - enabling `block` per-group restores it exactly as before,
evaluated identically (shift-vs-oncall overlap for the same user only).
"""

from app.utils.automation.rules.base import AutomationRuleType


class OnCallShiftOverlapRule(AutomationRuleType):
    """`block`: whether creating a shift/on-call that overlaps the
    same user's existing on-call/shift is rejected. Off by default -
    on-call duty coexists with normal shifts."""

    rule_type = "oncall_shift_overlap"

    @classmethod
    def default_params(cls) -> dict:
        return {"block": False}

    @classmethod
    def validate_params(cls, params: dict) -> list[str]:
        errors = []
        if not isinstance(params.get("block"), bool):
            errors.append("block must be a boolean")
        return errors
