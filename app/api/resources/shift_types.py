"""
Public read-only API for shift types. Registered under
/api/v1/shift-types - distinct URL prefix from the internal
/api/shift-types (app/routes/shift_routes.py::api_get_shift_types,
session-cookie auth). List-only, same choice as the internal endpoint.
"""

from flask.views import MethodView
from flask_smorest import Blueprint

from app import limiter
from app.api.rate_limit import API_RATE_LIMIT, service_account_key
from app.api.resources import all_blueprints
from app.api.schemas.shift_type_schema import ShiftTypeSchema
from app.api.setup import configure_blueprint
from app.repositories.shift_repository import ShiftTypeRepository

blp = Blueprint(
    "shift_types",
    __name__,
    url_prefix="/api/v1/shift-types",
    description="Read-only access to shift types for third-party integrations.",
)
configure_blueprint(blp)
all_blueprints.append(blp)


@blp.route("/")
class ShiftTypeList(MethodView):
    @limiter.limit(API_RATE_LIMIT, key_func=service_account_key)
    @blp.response(200, ShiftTypeSchema(many=True))
    def get(self):
        return ShiftTypeRepository.get_all()
