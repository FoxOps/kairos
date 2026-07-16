from marshmallow import Schema, fields


class OnCallSchema(Schema):
    id = fields.Int(dump_only=True)
    user_id = fields.Int(dump_only=True)
    start_time = fields.DateTime(dump_only=True)
    end_time = fields.DateTime(dump_only=True)
    duration_hours = fields.Method("get_duration_hours", dump_only=True)

    def get_duration_hours(self, obj) -> float:
        return obj.duration()


class OnCallListSchema(Schema):
    items = fields.List(fields.Nested(OnCallSchema), dump_only=True)
    page = fields.Int(dump_only=True)
    pages = fields.Int(dump_only=True)
    per_page = fields.Int(dump_only=True)
    total = fields.Int(dump_only=True)
