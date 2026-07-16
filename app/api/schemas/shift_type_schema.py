from marshmallow import Schema, fields


class ShiftTypeSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(dump_only=True)
    label = fields.Str(dump_only=True)
    start_hour = fields.Int(dump_only=True)
    end_hour = fields.Int(dump_only=True)
