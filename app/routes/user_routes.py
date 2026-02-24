from flask import request
from flask.views import MethodView
from flask_jwt_extended import get_jwt, jwt_required
from flask_smorest import Blueprint, abort

from app.schemas.user_schemas import (
    UserCreateSchema,
    UserPaginationSchema,
    UserSchema,
)
from app.services.user_service import UserService

user_bp = Blueprint(
    "users",
    "users",
)


@user_bp.route("")
class UsersList(MethodView):
    @jwt_required()
    @user_bp.response(200, UserPaginationSchema)
    def get(self):
        claims = get_jwt()
        if not claims.get("is_admin", False):
            abort(403, message="Acesso permitido apenas para administradores.")

        page = request.args.get("page", type=int)
        per_page = request.args.get("per_page", type=int)

        return UserService.list_users(page, per_page)

    @user_bp.arguments(UserCreateSchema)
    @user_bp.response(201, UserSchema)
    @user_bp.alt_response(400, description="Erro de validação/regra de negócio")
    def post(self, payload):
        try:
            return UserService.create_user(payload)
        except ValueError as exc:
            abort(400, message=str(exc))
