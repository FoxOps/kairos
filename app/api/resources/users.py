"""
Public read-only API for users. Registered under /api/v1/users -
distinct URL prefix from the internal /api/users
(app/routes/shift_routes.py::api_get_users, session-cookie auth), same
public field contract (see app/api/schemas/user_schema.py). Not
paginated, same choice as the internal endpoint it mirrors.
"""

from flask.views import MethodView
from flask_smorest import Blueprint, abort

from app import limiter
from app.api.rate_limit import API_RATE_LIMIT, service_account_key
from app.api.resources import all_blueprints
from app.api.schemas.user_schema import UserSchema
from app.api.setup import configure_blueprint
from app.repositories.user_repository import UserRepository

blp = Blueprint(
    "users",
    __name__,
    url_prefix="/api/v1/users",
    description="Read-only access to users for third-party integrations.",
)
configure_blueprint(blp)
all_blueprints.append(blp)


@blp.route("/")
class UserList(MethodView):
    @limiter.limit(API_RATE_LIMIT, key_func=service_account_key)
    @blp.response(200, UserSchema(many=True))
    def get(self):
        return UserRepository.get_all()


@blp.route("/<int:user_id>")
class UserDetail(MethodView):
    @limiter.limit(API_RATE_LIMIT, key_func=service_account_key)
    @blp.response(200, UserSchema)
    def get(self, user_id):
        user = UserRepository.get_by_id(user_id)
        if user is None:
            abort(404, message="User not found.")
        return user
