from flask import request
from flask.views import MethodView
from flask_smorest import Blueprint

from app.schemas.user_schemas import UserPaginationSchema
from app.services.user_service import list_users

user_bp = Blueprint(
    "users",
    "users",
    url_prefix="/users",
    description="Operações relacionadas aos usuários",
)


@user_bp.route("")
class UsersList(MethodView):
    @user_bp.response(200, UserPaginationSchema)
    def get(self):
        page = request.args.get("page", type=int)
        per_page = request.args.get("per_page", type=int)

        return list_users(page, per_page)
