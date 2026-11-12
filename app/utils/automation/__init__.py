"""
Automation utilities for Kairos.

Shift/on-call generation lives in the pure planner
(app/utils/automation/planner/), fed by the rule engine
(app/utils/automation/rules/) and the DB lookups in queries.py.
"""

from app.utils.automation.status import get_automation_status

__all__ = [
    "get_automation_status",
]
