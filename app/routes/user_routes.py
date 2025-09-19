from flask import request
from flask.views import MethodView
from flask_smorest import Blueprint

from app.schemas.user_schemas import UserPaginationSchema
from app.services.user_service import list_users
from app.utils.require_api_key import require_api_key

user_bp = Blueprint(
    "users",
    "users",
    url_prefix="/users",
)


@user_bp.route("")
@require_api_key
class UsersList(MethodView):
    decorators = [require_api_key]

    @user_bp.response(200, UserPaginationSchema)
    def get(self):
        page = request.args.get("page", type=int)
        per_page = request.args.get("per_page", type=int)

        return list_users(page, per_page)
