from marshmallow import Schema, fields


class ShiftTypeSchema(Schema):
    id = fields.Int(dump_only=True, required=True, metadata={"example": 2})
    name = fields.Str(dump_only=True, required=True, metadata={"example": "morning"})
    label = fields.Str(dump_only=True, required=True, metadata={"example": "Morning"})
    start_hour = fields.Int(
        dump_only=True,
        required=True,
        metadata={"description": "Start hour, 0-23.", "example": 7},
    )
    end_hour = fields.Int(
        dump_only=True,
        required=True,
        metadata={"description": "End hour, 0-23.", "example": 15},
    )
