"""
Public read-only API for shifts. Registered under /api/v1/shifts (see
app/api/__init__.py) - distinct URL prefix from the internal /api/shifts
(app/routes/shift_routes.py, session-cookie auth). Bearer-token auth
only, see app/auth/service_account_auth.py.
"""

from flask.views import MethodView
from flask_smorest import Blueprint, abort

from app import limiter
from app.api.rate_limit import API_RATE_LIMIT, service_account_key
from app.api.resources import all_blueprints
from app.api.schemas.pagination_schema import PageQueryArgsSchema
from app.api.schemas.shift_schema import ShiftListSchema, ShiftSchema
from app.api.setup import configure_blueprint
from app.repositories.shift_repository import ShiftRepository
from app.services import SettingsService

blp = Blueprint(
    "shifts",
    __name__,
    url_prefix="/api/v1/shifts",
    description="Read-only access to shifts for third-party integrations.",
)
configure_blueprint(blp)
all_blueprints.append(blp)


@blp.route("/")
class ShiftList(MethodView):
    @limiter.limit(API_RATE_LIMIT, key_func=service_account_key)
    @blp.arguments(PageQueryArgsSchema, location="query")
    @blp.response(200, ShiftListSchema)
    def get(self, args):
        per_page = args["per_page"] or SettingsService.get_items_per_page()
        per_page = min(per_page, SettingsService.get_max_per_page())
        pagination = ShiftRepository.list_paginated(args["page"], per_page)
        return {
            "items": pagination.items,
            "page": pagination.page,
            "pages": pagination.pages,
            "per_page": pagination.per_page,
            "total": pagination.total,
        }


@blp.route("/<int:shift_id>")
class ShiftDetail(MethodView):
    @limiter.limit(API_RATE_LIMIT, key_func=service_account_key)
    @blp.response(200, ShiftSchema)
    def get(self, shift_id):
        shift = ShiftRepository.get_by_id(shift_id)
        if shift is None:
            abort(404, message="Shift not found.")
        return shift
