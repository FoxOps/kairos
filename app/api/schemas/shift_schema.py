from marshmallow import Schema, fields, validate

from app.api.schemas.filter_schema import DateRangeFilterMixin, UserGroupFilterMixin
from app.api.schemas.pagination_schema import PageQueryArgsSchema
from app.utils.helpers.timezone_helpers import org_aware


class ShiftSchema(Schema):
    id = fields.Int(
        dump_only=True,
        required=True,
        metadata={"description": "Shift identifier.", "example": 101},
    )
    user_id = fields.Int(
        dump_only=True,
        required=True,
        metadata={"description": "Identifier of the assigned user.", "example": 5},
    )
    shift_type_id = fields.Int(
        dump_only=True,
        required=True,
        metadata={"description": "Identifier of the shift type.", "example": 2},
    )
    date = fields.Date(
        dump_only=True,
        required=True,
        metadata={
            "description": "Organization-local calendar date the shift covers.",
            "example": "2026-09-11",
        },
    )
    start_time = fields.Method(
        "get_start_time",
        dump_only=True,
        required=True,
        metadata={
            "type": "string",
            "format": "date-time",
            "description": (
                "Timezone-aware ISO 8601 start (org's default_timezone offset)."
            ),
            "example": "2026-09-11T07:00:00+02:00",
        },
    )
    end_time = fields.Method(
        "get_end_time",
        dump_only=True,
        required=True,
        metadata={
            "type": "string",
            "format": "date-time",
            "description": (
                "Timezone-aware ISO 8601 end (org's default_timezone offset)."
            ),
            "example": "2026-09-11T15:00:00+02:00",
        },
    )
    duration_hours = fields.Method(
        "get_duration_hours",
        dump_only=True,
        required=True,
        metadata={
            "type": "number",
            "format": "float",
            "minimum": 0,
            "description": "Shift duration in hours.",
            "example": 8.0,
        },
    )

    def get_start_time(self, obj) -> str:
        """obj.start_time is a naive org-local wall clock, see
        app/utils/helpers/timezone_helpers.py - same treatment as
        OnCallSchema, for a consistent never-naive contract across
        every public API datetime field (spec: never return ambiguous
        naive timestamps)."""
        return org_aware(obj.start_time).isoformat()

    def get_end_time(self, obj) -> str:
        return org_aware(obj.end_time).isoformat()

    def get_duration_hours(self, obj) -> float:
        return obj.duration()


class ShiftListSchema(Schema):
    items = fields.List(fields.Nested(ShiftSchema), dump_only=True, required=True)
    page = fields.Int(dump_only=True, required=True, metadata={"minimum": 1})
    pages = fields.Int(dump_only=True, required=True, metadata={"minimum": 0})
    per_page = fields.Int(dump_only=True, required=True, metadata={"minimum": 1})
    total = fields.Int(dump_only=True, required=True, metadata={"minimum": 0})


class ShiftQueryArgsSchema(
    PageQueryArgsSchema, DateRangeFilterMixin, UserGroupFilterMixin
):
    shift_type_id = fields.Int(
        load_default=None,
        validate=validate.Range(min=1),
        metadata={"description": "Only include shifts of this shift type."},
    )
