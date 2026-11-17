from marshmallow import Schema, fields

from app.api.schemas.filter_schema import DateRangeFilterMixin, UserGroupFilterMixin
from app.api.schemas.pagination_schema import PageQueryArgsSchema
from app.utils.helpers.timezone_helpers import org_aware


class OnCallSchema(Schema):
    id = fields.Int(
        dump_only=True,
        required=True,
        metadata={"description": "On-call period identifier.", "example": 41},
    )
    user_id = fields.Int(
        dump_only=True,
        required=True,
        metadata={"description": "Identifier of the on-call user.", "example": 5},
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
            "example": "2026-09-11T21:00:00+02:00",
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
            "example": "2026-09-18T07:00:00+02:00",
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
            "description": "On-call period duration in hours.",
            "example": 154.0,
        },
    )

    def get_start_time(self, obj) -> str:
        """Timezone-aware ISO 8601 (org's default_timezone offset) -
        obj.start_time is a naive org-local wall clock, see
        app/utils/helpers/timezone_helpers.py."""
        return org_aware(obj.start_time).isoformat()

    def get_end_time(self, obj) -> str:
        return org_aware(obj.end_time).isoformat()

    def get_duration_hours(self, obj) -> float:
        return obj.duration()


class OnCallListSchema(Schema):
    items = fields.List(fields.Nested(OnCallSchema), dump_only=True, required=True)
    page = fields.Int(dump_only=True, required=True, metadata={"minimum": 1})
    pages = fields.Int(dump_only=True, required=True, metadata={"minimum": 0})
    per_page = fields.Int(dump_only=True, required=True, metadata={"minimum": 1})
    total = fields.Int(dump_only=True, required=True, metadata={"minimum": 0})


class OnCallQueryArgsSchema(
    PageQueryArgsSchema, DateRangeFilterMixin, UserGroupFilterMixin
):
    pass
