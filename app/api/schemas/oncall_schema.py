from marshmallow import Schema, fields

from app.utils.helpers.timezone_helpers import org_aware


class OnCallSchema(Schema):
    id = fields.Int(dump_only=True)
    user_id = fields.Int(dump_only=True)
    start_time = fields.Method("get_start_time", dump_only=True)
    end_time = fields.Method("get_end_time", dump_only=True)
    duration_hours = fields.Method("get_duration_hours", dump_only=True)

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
    items = fields.List(fields.Nested(OnCallSchema), dump_only=True)
    page = fields.Int(dump_only=True)
    pages = fields.Int(dump_only=True)
    per_page = fields.Int(dump_only=True)
    total = fields.Int(dump_only=True)
