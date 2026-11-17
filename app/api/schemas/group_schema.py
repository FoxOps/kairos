from marshmallow import Schema, fields


class GroupSchema(Schema):
    id = fields.Int(
        dump_only=True,
        required=True,
        metadata={"description": "Group identifier."},
    )
    name = fields.Str(
        dump_only=True,
        required=True,
        metadata={"description": "Group name."},
    )
    is_part_of_schedule = fields.Bool(
        dump_only=True,
        required=True,
        metadata={
            "description": "Whether members of this group are included "
            "in shift scheduling - relevant when interpreting a shift's "
            "group_id."
        },
    )
    is_part_of_oncall = fields.Bool(
        dump_only=True,
        required=True,
        metadata={
            "description": "Whether members of this group are included "
            "in on-call rotations - relevant when interpreting an "
            "on-call period's group_id."
        },
    )
