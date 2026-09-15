"""
Public read-only API for on-call periods. Registered under
/api/v1/oncall - distinct URL prefix from the internal /api/oncall/<id>
(app/routes/oncall_routes.py, session-cookie auth). Bearer-token auth
only, see app/auth/service_account_auth.py.
"""

from flask import jsonify
from flask.views import MethodView
from flask_smorest import Blueprint, abort
from marshmallow import Schema, fields

from app import limiter
from app.api.rate_limit import API_RATE_LIMIT, service_account_key
from app.api.resources import all_blueprints
from app.api.schemas.oncall_schema import OnCallListSchema, OnCallSchema
from app.api.schemas.pagination_schema import PageQueryArgsSchema
from app.api.setup import configure_blueprint
from app.models import OnCall
from app.repositories.oncall_repository import OnCallRepository
from app.services import SettingsService
from app.utils.helpers.timezone_helpers import org_aware

blp = Blueprint(
    "oncall",
    __name__,
    url_prefix="/api/v1/oncall",
    description="Read-only access to on-call periods for third-party integrations.",
)
configure_blueprint(blp)
all_blueprints.append(blp)


class OnCallCurrentQueryArgsSchema(Schema):
    group_id = fields.Int(load_default=None)


class OnCallCurrentSchema(Schema):
    """Shape of one element returned by GET /api/v1/oncall/current -
    every field besides `active` is only present when a shift is
    currently active (allow_none since {"active": false} omits them
    entirely; a client must check `active` first). group_id omitted
    returns a JSON array of these; group_id given returns a single one
    (either the active shift, or just {"active": false})."""

    active = fields.Bool(dump_only=True)
    id = fields.Int(dump_only=True, allow_none=True)
    user_id = fields.Int(dump_only=True, allow_none=True)
    name = fields.Str(dump_only=True, allow_none=True)
    email = fields.Email(dump_only=True, allow_none=True)
    group_id = fields.Int(dump_only=True, allow_none=True)
    start_time = fields.Str(dump_only=True, allow_none=True)
    end_time = fields.Str(dump_only=True, allow_none=True)
    timezone = fields.Str(dump_only=True, allow_none=True)


_CURRENT_ACTIVE_EXAMPLE = {
    "active": True,
    "id": 41,
    "user_id": 5,
    "name": "John Doe",
    "email": "john.doe@example.com",
    "group_id": 2,
    "start_time": "2026-09-11T21:00:00+02:00",
    "end_time": "2026-09-18T07:00:00+02:00",
    "timezone": "Europe/Paris",
}


def _serialize_current(oncall: OnCall) -> dict:
    user = oncall.user
    return {
        "active": True,
        "id": oncall.id,
        "user_id": oncall.user_id,
        "name": user.name,
        "email": user.email,
        "group_id": user.group_id,
        "start_time": org_aware(oncall.start_time).isoformat(),
        "end_time": org_aware(oncall.end_time).isoformat(),
        "timezone": SettingsService.get_default_timezone(),
    }


@blp.route("/")
class OnCallList(MethodView):
    @limiter.limit(API_RATE_LIMIT, key_func=service_account_key)
    @blp.arguments(PageQueryArgsSchema, location="query")
    @blp.response(200, OnCallListSchema)
    def get(self, args):
        per_page = args["per_page"] or SettingsService.get_items_per_page()
        per_page = min(per_page, SettingsService.get_max_per_page())
        pagination = OnCallRepository.list_paginated(args["page"], per_page)
        return {
            "items": pagination.items,
            "page": pagination.page,
            "pages": pagination.pages,
            "per_page": pagination.per_page,
            "total": pagination.total,
        }


@blp.route("/current")
class OnCallCurrent(MethodView):
    """Currently active on-call shift(s), resolved using the org's
    configured timezone (OnCallRepository.list_active(), same comparison
    as OnCall.is_active()). The response shape genuinely changes with
    group_id (array vs. single object vs. {"active": false}), which
    doesn't fit flask-smorest's one-schema-serializes-the-return-value
    model - the view builds+returns its own flask.jsonify(...) Response
    instead of a plain dict/list, and @blp.response below is used purely
    for OpenAPI documentation: per flask_smorest.Blueprint.response's
    own docstring, "If the decorated
    function returns a Response object, the schema and status_code
    parameters are only used to document the resource" (no re-dump, no
    interference with the shape actually sent)."""

    @limiter.limit(API_RATE_LIMIT, key_func=service_account_key)
    @blp.arguments(OnCallCurrentQueryArgsSchema, location="query")
    @blp.response(
        200,
        OnCallCurrentSchema(many=True),
        description=(
            "group_id omitted: JSON array of every currently active "
            "on-call shift (0+ items - more than one only possible in "
            "per_group on-call scheduling mode). group_id given: a "
            "single object of this same per-item shape - either the "
            'active shift for that group, or just {"active": false} '
            "when nothing is currently active for it."
        ),
        example=[_CURRENT_ACTIVE_EXAMPLE],
    )
    def get(self, args):
        group_id = args["group_id"]
        oncalls = OnCallRepository.list_active(group_id=group_id)
        if group_id is not None:
            if not oncalls:
                return jsonify({"active": False})
            return jsonify(_serialize_current(oncalls[0]))
        return jsonify([_serialize_current(oc) for oc in oncalls])


@blp.route("/<int:oncall_id>")
class OnCallDetail(MethodView):
    @limiter.limit(API_RATE_LIMIT, key_func=service_account_key)
    @blp.response(200, OnCallSchema)
    def get(self, oncall_id):
        oncall = OnCallRepository.get_by_id(oncall_id)
        if oncall is None:
            abort(404, message="On-call period not found.")
        return oncall
