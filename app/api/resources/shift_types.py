"""
Public read-only API for shift types. Registered under
/api/v1/shift-types - distinct URL prefix from the internal
/api/shift-types (app/routes/shift_routes.py::api_get_shift_types,
session-cookie auth). List-only, same choice as the internal endpoint.
Deliberately unpaginated - small configuration resource, see
Docs/api/API.md.
"""

from flask.views import MethodView
from flask_smorest import Blueprint

from app import limiter
from app.api.rate_limit import api_rate_limit, service_account_key
from app.api.resources import all_blueprints
from app.api.responses import document_errors
from app.api.schemas.shift_type_schema import ShiftTypeSchema
from app.api.setup import configure_blueprint
from app.repositories.shift_repository import ShiftTypeRepository

blp = Blueprint(
    "shift_types",
    __name__,
    url_prefix="/api/v1/shift-types",
    description="Read-only access to shift types for third-party integrations.",
)
configure_blueprint(blp, scope="read:shift_types")
all_blueprints.append(blp)


@blp.route("/")
class ShiftTypeList(MethodView):
    @limiter.limit(api_rate_limit, key_func=service_account_key)
    @blp.response(200, ShiftTypeSchema(many=True))
    @blp.doc(
        operationId="listShiftTypes",
        summary="List shift types",
        description="Every shift type. Unpaginated (small configuration resource).",
    )
    @document_errors(blp)
    def get(self):
        return ShiftTypeRepository.get_all()
