from marshmallow import Schema, fields


class UserSchema(Schema):
    """Deliberately excludes every sensitive/preference field on User
    (password_hash, ics_token, apprise_*_target_ids, timezone/language/
    date_format/time_format, notification opt-outs) - same public
    contract as the internal /api/users endpoint
    (app/routes/shift_routes.py::api_get_users), plus group_id since
    third-party integrations commonly need to map users to teams."""

    id = fields.Int(dump_only=True)
    name = fields.Str(dump_only=True)
    email = fields.Email(dump_only=True)
    group_id = fields.Int(dump_only=True)
    is_admin = fields.Bool(dump_only=True)
