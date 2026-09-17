"""
Public read-only API for on-call periods. Registered under
/api/v1/oncall - distinct URL prefix from the internal /api/oncall/<id>
(app/routes/oncall_routes.py, session-cookie auth). Bearer-token auth
only, see app/auth/service_account_auth.py.
"""

from flask import jsonify
from flask.views import MethodView
from flask_smorest import Blueprint, abort
from marshmallow import Schema, fields, validate

from app import limiter
from app.api.rate_limit import api_rate_limit, service_account_key
from app.api.resources import all_blueprints
from app.api.responses import document_errors
from app.api.schemas.oncall_schema import (
    OnCallListSchema,
    OnCallQueryArgsSchema,
    OnCallSchema,
)
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
configure_blueprint(blp, scope="read:oncall")
all_blueprints.append(blp)


class OnCallCurrentQueryArgsSchema(Schema):
    group_id = fields.Int(
        load_default=None,
        validate=validate.Range(min=1),
        metadata={"description": "Only consider on-call periods for this group."},
    )


class OnCallCurrentItemSchema(Schema):
    """One currently-active on-call period. Always nested inside
    OnCallCurrentListSchema's items - see that schema for why the
    top-level response shape is always {"items": [...], "count": N}
    regardless of group_id."""

    id = fields.Int(dump_only=True, required=True)
    user_id = fields.Int(dump_only=True, required=True)
    name = fields.Str(dump_only=True, required=True)
    email = fields.Email(dump_only=True, required=True)
    group_id = fields.Int(dump_only=True, required=True, allow_none=True)
    start_time = fields.Str(
        dump_only=True,
        required=True,
        metadata={"type": "string", "format": "date-time"},
    )
    end_time = fields.Str(
        dump_only=True,
        required=True,
        metadata={"type": "string", "format": "date-time"},
    )
    timezone = fields.Str(
        dump_only=True,
        required=True,
        metadata={
            "description": "IANA timezone name the times above are expressed in.",
            "example": "Europe/Paris",
        },
    )


class OnCallCurrentListSchema(Schema):
    items = fields.List(
        fields.Nested(OnCallCurrentItemSchema), dump_only=True, required=True
    )
    count = fields.Int(dump_only=True, required=True, metadata={"minimum": 0})


_CURRENT_ACTIVE_EXAMPLE = {
    "items": [
        {
            "id": 41,
            "user_id": 5,
            "name": "Jane Doe",
            "email": "jane.doe@example.com",
            "group_id": 2,
            "start_time": "2026-09-11T21:00:00+02:00",
            "end_time": "2026-09-18T07:00:00+02:00",
            "timezone": "Europe/Paris",
        }
    ],
    "count": 1,
}


def _serialize_current(oncall: OnCall) -> dict:
    user = oncall.user
    return {
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
    @limiter.limit(api_rate_limit, key_func=service_account_key)
    @blp.arguments(OnCallQueryArgsSchema, location="query")
    @blp.response(200, OnCallListSchema)
    @blp.doc(
        operationId="listOnCallPeriods",
        summary="List on-call periods",
        description=(
            "Paginated list of on-call periods, optionally filtered by "
            "date range (overlap semantics), user, or group."
        ),
    )
    @document_errors(blp, validation=True)
    def get(self, args):
        per_page = args["per_page"] or SettingsService.get_items_per_page()
        per_page = min(per_page, SettingsService.get_max_per_page())
        pagination = OnCallRepository.list_paginated(
            args["page"],
            per_page,
            user_id=args["user_id"],
            group_id=args["group_id"],
            date_from=args["start"],
            date_to=args["end"],
        )
        return {
            "items": pagination.items,
            "page": pagination.page,
            "pages": pagination.pages,
            "per_page": pagination.per_page,
            "total": pagination.total,
        }


@blp.route("/current")
class OnCallCurrent(MethodView):
    """Currently active on-call period(s), resolved using the org's
    configured timezone (OnCallRepository.list_active(), same comparison
    as OnCall.is_active()). Always returns the same stable shape,
    {"items": [...], "count": N} - items is empty when nothing is
    currently active, and can hold more than one entry if group_id is
    omitted (per_group scheduling mode) or if more than one on-call is
    genuinely concurrent within a given group (a rare admin-created
    overlap) - a monitoring/alerting integration should never have to
    branch on the JSON type to read this endpoint."""

    @limiter.limit(api_rate_limit, key_func=service_account_key)
    @blp.arguments(OnCallCurrentQueryArgsSchema, location="query")
    @blp.response(
        200,
        OnCallCurrentListSchema,
        description=(
            "Every currently active on-call period, optionally scoped to "
            "one group. 0+ items - more than one only possible when "
            "group_id is omitted (per_group scheduling mode) or when "
            "more than one on-call is genuinely concurrent within the "
            "given group."
        ),
        example=_CURRENT_ACTIVE_EXAMPLE,
    )
    @blp.doc(
        operationId="getCurrentOnCall",
        summary="Get the currently active on-call period(s)",
    )
    @document_errors(blp, validation=True)
    def get(self, args):
        oncalls = OnCallRepository.list_active(group_id=args["group_id"])
        items = [_serialize_current(oc) for oc in oncalls]
        return jsonify({"items": items, "count": len(items)})


@blp.route("/<int:oncall_id>")
class OnCallDetail(MethodView):
    @limiter.limit(api_rate_limit, key_func=service_account_key)
    @blp.response(200, OnCallSchema)
    @blp.doc(
        operationId="getOnCallPeriod",
        summary="Get an on-call period",
        description="A single on-call period by id.",
    )
    @document_errors(blp, not_found=True)
    def get(self, oncall_id):
        oncall = OnCallRepository.get_by_id(oncall_id)
        if oncall is None:
            abort(404, message="On-call period not found.")
        return oncall
