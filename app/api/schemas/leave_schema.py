from marshmallow import Schema, fields

from app.api.schemas.filter_schema import DateRangeFilterMixin, UserGroupFilterMixin
from app.api.schemas.pagination_schema import PageQueryArgsSchema


class LeaveSchema(Schema):
    id = fields.Int(
        dump_only=True,
        required=True,
        metadata={"description": "Leave identifier.", "example": 7},
    )
    user_id = fields.Int(
        dump_only=True,
        required=True,
        metadata={"description": "Identifier of the user on leave.", "example": 5},
    )
    start_date = fields.Date(
        dump_only=True,
        required=True,
        metadata={
            "description": "First day of leave (inclusive).",
            "example": "2026-08-03",
        },
    )
    end_date = fields.Date(
        dump_only=True,
        required=True,
        metadata={
            "description": "Last day of leave (inclusive).",
            "example": "2026-08-07",
        },
    )
    duration_days = fields.Method(
        "get_duration_days",
        dump_only=True,
        required=True,
        metadata={
            "type": "integer",
            "minimum": 0,
            "description": "Number of calendar days covered (inclusive).",
            "example": 5,
        },
    )

    def get_duration_days(self, obj) -> int:
        return obj.duration()


class LeaveListSchema(Schema):
    items = fields.List(fields.Nested(LeaveSchema), dump_only=True, required=True)
    page = fields.Int(dump_only=True, required=True, metadata={"minimum": 1})
    pages = fields.Int(dump_only=True, required=True, metadata={"minimum": 0})
    per_page = fields.Int(dump_only=True, required=True, metadata={"minimum": 1})
    total = fields.Int(dump_only=True, required=True, metadata={"minimum": 0})


class LeaveQueryArgsSchema(
    PageQueryArgsSchema, DateRangeFilterMixin, UserGroupFilterMixin
):
    pass
