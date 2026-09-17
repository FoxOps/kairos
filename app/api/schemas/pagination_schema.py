"""
Shared query-args schema for paginated list endpoints (shifts, oncall,
leave). Mirrors the admin UI's own pagination knobs
(SettingsService.get_items_per_page()/get_max_per_page()) rather than
hardcoding fixed defaults at import time - the resources apply those
settings themselves since they're only known at request time.
"""

from marshmallow import Schema, fields, validate


class PageQueryArgsSchema(Schema):
    page = fields.Int(
        load_default=1,
        validate=validate.Range(min=1),
        metadata={"description": "Page number, starting at 1."},
    )
    per_page = fields.Int(
        load_default=None,
        validate=validate.Range(min=1),
        metadata={
            "description": (
                "Number of records per page. When omitted, the "
                "instance-configured default is used (admin-editable at "
                "/admin/settings, items_per_page). The effective value is "
                "capped at the instance-configured maximum (max_per_page) "
                "- both are runtime settings, not fixed protocol constants."
            )
        },
    )
