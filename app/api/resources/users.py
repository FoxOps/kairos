"""
Public read-only API for users. Registered under /api/v1/users -
distinct URL prefix from the internal /api/users
(app/routes/shift_routes.py::api_get_users, session-cookie auth), same
public field contract (see app/api/schemas/user_schema.py). Paginated,
with an optional group_id filter, same as shifts/oncall/leave -
previously a bare unpaginated array (a documented breaking change, see
CHANGELOG.md).
"""

from flask.views import MethodView
from flask_smorest import Blueprint, abort

from app import limiter
from app.api.rate_limit import api_rate_limit, service_account_key
from app.api.resources import all_blueprints
from app.api.responses import document_errors
from app.api.schemas.user_schema import UserListSchema, UserQueryArgsSchema, UserSchema
from app.api.setup import configure_blueprint
from app.repositories.user_repository import UserRepository
from app.services import SettingsService

blp = Blueprint(
    "users",
    __name__,
    url_prefix="/api/v1/users",
    description="Read-only access to users for third-party integrations.",
)
configure_blueprint(blp, scope="read:users")
all_blueprints.append(blp)


@blp.route("/")
class UserList(MethodView):
    @limiter.limit(api_rate_limit, key_func=service_account_key)
    @blp.arguments(UserQueryArgsSchema, location="query")
    @blp.response(200, UserListSchema)
    @blp.doc(
        operationId="listUsers",
        summary="List users",
        description="Paginated list of users, optionally filtered by group.",
    )
    @document_errors(blp, validation=True)
    def get(self, args):
        per_page = args["per_page"] or SettingsService.get_items_per_page()
        per_page = min(per_page, SettingsService.get_max_per_page())
        pagination = UserRepository.list_paginated(
            args["page"], per_page, group_id=args["group_id"]
        )
        return {
            "items": pagination.items,
            "page": pagination.page,
            "pages": pagination.pages,
            "per_page": pagination.per_page,
            "total": pagination.total,
        }


@blp.route("/<int:user_id>")
class UserDetail(MethodView):
    @limiter.limit(api_rate_limit, key_func=service_account_key)
    @blp.response(200, UserSchema)
    @blp.doc(
        operationId="getUser",
        summary="Get a user",
        description="A single user by id.",
    )
    @document_errors(blp, not_found=True)
    def get(self, user_id):
        user = UserRepository.get_by_id(user_id)
        if user is None:
            abort(404, message="User not found.")
        return user
