"""
Public read-only API for leave. Registered under /api/v1/leave -
distinct URL prefix from the internal /api/leave/<id>
(app/routes/leave_routes.py, session-cookie auth). Bearer-token auth
only, see app/auth/service_account_auth.py.
"""

from flask.views import MethodView
from flask_smorest import Blueprint, abort

from app import limiter
from app.api.rate_limit import API_RATE_LIMIT, service_account_key
from app.api.resources import all_blueprints
from app.api.schemas.leave_schema import LeaveListSchema, LeaveSchema
from app.api.schemas.pagination_schema import PageQueryArgsSchema
from app.api.setup import configure_blueprint
from app.repositories.leave_repository import LeaveRepository
from app.services import SettingsService

blp = Blueprint(
    "leave",
    __name__,
    url_prefix="/api/v1/leave",
    description="Read-only access to leave for third-party integrations.",
)
configure_blueprint(blp)
all_blueprints.append(blp)


@blp.route("/")
class LeaveList(MethodView):
    @limiter.limit(API_RATE_LIMIT, key_func=service_account_key)
    @blp.arguments(PageQueryArgsSchema, location="query")
    @blp.response(200, LeaveListSchema)
    def get(self, args):
        per_page = args["per_page"] or SettingsService.get_items_per_page()
        per_page = min(per_page, SettingsService.get_max_per_page())
        pagination = LeaveRepository.list_paginated(args["page"], per_page)
        return {
            "items": pagination.items,
            "page": pagination.page,
            "pages": pagination.pages,
            "per_page": pagination.per_page,
            "total": pagination.total,
        }


@blp.route("/<int:leave_id>")
class LeaveDetail(MethodView):
    @limiter.limit(API_RATE_LIMIT, key_func=service_account_key)
    @blp.response(200, LeaveSchema)
    def get(self, leave_id):
        leave = LeaveRepository.get_by_id(leave_id)
        if leave is None:
            abort(404, message="Leave not found.")
        return leave
