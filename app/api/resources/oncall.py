"""
Public read-only API for on-call periods. Registered under
/api/v1/oncall - distinct URL prefix from the internal /api/oncall/<id>
(app/routes/oncall_routes.py, session-cookie auth). Bearer-token auth
only, see app/auth/service_account_auth.py.
"""

from flask.views import MethodView
from flask_smorest import Blueprint, abort

from app import limiter
from app.api.rate_limit import API_RATE_LIMIT, service_account_key
from app.api.resources import all_blueprints
from app.api.schemas.oncall_schema import OnCallListSchema, OnCallSchema
from app.api.schemas.pagination_schema import PageQueryArgsSchema
from app.api.setup import configure_blueprint
from app.repositories.oncall_repository import OnCallRepository
from app.services import SettingsService

blp = Blueprint(
    "oncall",
    __name__,
    url_prefix="/api/v1/oncall",
    description="Read-only access to on-call periods for third-party integrations.",
)
configure_blueprint(blp)
all_blueprints.append(blp)


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


@blp.route("/<int:oncall_id>")
class OnCallDetail(MethodView):
    @limiter.limit(API_RATE_LIMIT, key_func=service_account_key)
    @blp.response(200, OnCallSchema)
    def get(self, oncall_id):
        oncall = OnCallRepository.get_by_id(oncall_id)
        if oncall is None:
            abort(404, message="On-call period not found.")
        return oncall
