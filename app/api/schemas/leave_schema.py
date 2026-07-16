from marshmallow import Schema, fields


class LeaveSchema(Schema):
    id = fields.Int(dump_only=True)
    user_id = fields.Int(dump_only=True)
    start_date = fields.Date(dump_only=True)
    end_date = fields.Date(dump_only=True)
    duration_days = fields.Method("get_duration_days", dump_only=True)

    def get_duration_days(self, obj) -> int:
        return obj.duration()


class LeaveListSchema(Schema):
    items = fields.List(fields.Nested(LeaveSchema), dump_only=True)
    page = fields.Int(dump_only=True)
    pages = fields.Int(dump_only=True)
    per_page = fields.Int(dump_only=True)
    total = fields.Int(dump_only=True)
