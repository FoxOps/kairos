from marshmallow import Schema, fields, validate

from app.api.schemas.pagination_schema import PageQueryArgsSchema


class UserSchema(Schema):
    """Deliberately excludes every sensitive/preference field on User
    (password_hash, ics_token, apprise_*_target_ids, timezone/language/
    date_format/time_format, notification opt-outs) - same public
    contract as the internal /api/users endpoint
    (app/routes/shift_routes.py::api_get_users), plus group_id since
    third-party integrations commonly need to map users to teams."""

    id = fields.Int(
        dump_only=True,
        required=True,
        metadata={"description": "User identifier.", "example": 5},
    )
    name = fields.Str(
        dump_only=True,
        required=True,
        metadata={"description": "Display name.", "example": "Jane Doe"},
    )
    email = fields.Email(
        dump_only=True,
        required=True,
        metadata={"example": "jane.doe@example.com"},
    )
    group_id = fields.Int(
        dump_only=True,
        required=True,
        allow_none=True,
        metadata={"description": "Identifier of the user's group.", "example": 2},
    )
    is_admin = fields.Bool(dump_only=True, required=True)


class UserListSchema(Schema):
    items = fields.List(fields.Nested(UserSchema), dump_only=True, required=True)
    page = fields.Int(dump_only=True, required=True, metadata={"minimum": 1})
    pages = fields.Int(dump_only=True, required=True, metadata={"minimum": 0})
    per_page = fields.Int(dump_only=True, required=True, metadata={"minimum": 1})
    total = fields.Int(dump_only=True, required=True, metadata={"minimum": 0})


class UserQueryArgsSchema(PageQueryArgsSchema):
    group_id = fields.Int(
        load_default=None,
        validate=validate.Range(min=1),
        metadata={"description": "Only include users in this group."},
    )
