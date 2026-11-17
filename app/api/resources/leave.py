"""
Public read-only API for leave. Registered under /api/v1/leave -
distinct URL prefix from the internal /api/leave/<id>
(app/routes/leave_routes.py, session-cookie auth). Bearer-token auth
only, see app/auth/service_account_auth.py.
"""

from flask.views import MethodView
from flask_smorest import Blueprint, abort

from app import limiter
from app.api.rate_limit import api_rate_limit, service_account_key
from app.api.resources import all_blueprints
from app.api.responses import document_errors
from app.api.schemas.leave_schema import (
    LeaveListSchema,
    LeaveQueryArgsSchema,
    LeaveSchema,
)
from app.api.setup import configure_blueprint
from app.repositories.leave_repository import LeaveRepository
from app.services import SettingsService

blp = Blueprint(
    "leave",
    __name__,
    url_prefix="/api/v1/leave",
    description="Read-only access to leave for third-party integrations.",
)
configure_blueprint(blp, scope="read:leave")
all_blueprints.append(blp)


@blp.route("/")
class LeaveList(MethodView):
    @limiter.limit(api_rate_limit, key_func=service_account_key)
    @blp.arguments(LeaveQueryArgsSchema, location="query")
    @blp.response(200, LeaveListSchema)
    @blp.doc(
        operationId="listLeave",
        summary="List leave",
        description=(
            "Paginated list of leave periods, optionally filtered by "
            "date range (overlap semantics), user, or group."
        ),
    )
    @document_errors(blp, validation=True)
    def get(self, args):
        per_page = args["per_page"] or SettingsService.get_items_per_page()
        per_page = min(per_page, SettingsService.get_max_per_page())
        pagination = LeaveRepository.list_paginated(
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


@blp.route("/<int:leave_id>")
class LeaveDetail(MethodView):
    @limiter.limit(api_rate_limit, key_func=service_account_key)
    @blp.response(200, LeaveSchema)
    @blp.doc(
        operationId="getLeave",
        summary="Get a leave period",
        description="A single leave period by id.",
    )
    @document_errors(blp, not_found=True)
    def get(self, leave_id):
        leave = LeaveRepository.get_by_id(leave_id)
        if leave is None:
            abort(404, message="Leave not found.")
        return leave
