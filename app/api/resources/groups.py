"""
Public read-only API for groups. Registered under /api/v1/groups - there
is no internal /api/groups equivalent this mirrors (groups aren't a
first-class internal JSON resource today). Resolves the group_id values
already present in Shift/OnCall/Leave/User public API responses, which
otherwise gave third-party integrations no normal way to look up a
group's name. Unpaginated, same choice as shift-types (small
configuration resource).
"""

from flask.views import MethodView
from flask_smorest import Blueprint, abort

from app import limiter
from app.api.rate_limit import api_rate_limit, service_account_key
from app.api.resources import all_blueprints
from app.api.responses import document_errors
from app.api.schemas.group_schema import GroupSchema
from app.api.setup import configure_blueprint
from app.repositories.user_repository import GroupRepository

blp = Blueprint(
    "groups",
    __name__,
    url_prefix="/api/v1/groups",
    description="Read-only access to groups for third-party integrations.",
)
configure_blueprint(blp, scope="read:groups")
all_blueprints.append(blp)


@blp.route("/")
class GroupList(MethodView):
    @limiter.limit(api_rate_limit, key_func=service_account_key)
    @blp.response(200, GroupSchema(many=True))
    @blp.doc(
        operationId="listGroups",
        summary="List groups",
        description="Every group. Unpaginated (small configuration resource).",
    )
    @document_errors(blp)
    def get(self):
        return GroupRepository.get_all()


@blp.route("/<int:group_id>")
class GroupDetail(MethodView):
    @limiter.limit(api_rate_limit, key_func=service_account_key)
    @blp.response(200, GroupSchema)
    @blp.doc(
        operationId="getGroup",
        summary="Get a group",
        description="A single group by id.",
    )
    @document_errors(blp, not_found=True)
    def get(self, group_id):
        group = GroupRepository.get_by_id(group_id)
        if group is None:
            abort(404, message="Group not found.")
        return group
