from flask.views import MethodView
from flask_jwt_extended import get_jwt, jwt_required
from flask_smorest import Blueprint, abort

from app.schemas.login import AdminResetPasswordSchema
from app.schemas.user_schemas import (
    UserCreateSchema,
    UserListQuerySchema,
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
    @user_bp.arguments(UserListQuerySchema, location="query")
    @user_bp.response(200, UserPaginationSchema)
    @user_bp.alt_response(400, description="Parâmetros inválidos")
    def get(self, query_params):
        claims = get_jwt()
        if not claims.get("is_admin", False):
            abort(403, message="Acesso permitido apenas para administradores.")

        try:
            return UserService.list_users(
                page=query_params.get("page"),
                per_page=query_params.get("per_page"),
                search=query_params.get("search"),
                is_active=query_params.get("is_active"),
            )
        except ValueError as exc:
            abort(400, message=str(exc))

    @user_bp.arguments(UserCreateSchema)
    @user_bp.response(201, UserSchema)
    @user_bp.alt_response(400, description="Erro de validação/regra de negócio")
    def post(self, payload):
        try:
            return UserService.create_user(payload)
        except ValueError as exc:
            abort(400, message=str(exc))


@user_bp.route("/<string:user_id>/approve")
@user_bp.route("/<string:user_id>/activate")
class ApproveUser(MethodView):
    @jwt_required()
    @user_bp.response(200, UserSchema)
    @user_bp.alt_response(403, description="Acesso permitido apenas para administradores")
    @user_bp.alt_response(404, description="Usuário não encontrado")
    def patch(self, user_id):
        claims = get_jwt()
        if not claims.get("is_admin", False):
            abort(403, message="Acesso permitido apenas para administradores.")

        try:
            return UserService.approve_user(user_id)
        except ValueError as exc:
            abort(404, message=str(exc))


@user_bp.route("/<string:user_id>/deactivate")
class DeactivateUser(MethodView):
    @jwt_required()
    @user_bp.response(200, UserSchema)
    @user_bp.alt_response(403, description="Acesso permitido apenas para administradores")
    @user_bp.alt_response(404, description="Usuário não encontrado")
    def patch(self, user_id):
        claims = get_jwt()
        if not claims.get("is_admin", False):
            abort(403, message="Acesso permitido apenas para administradores.")

        try:
            return UserService.deactivate_user(user_id)
        except ValueError as exc:
            abort(404, message=str(exc))


@user_bp.route("/<string:user_id>/reset-password")
class ResetUserPassword(MethodView):
    @jwt_required()
    @user_bp.response(200, AdminResetPasswordSchema)
    @user_bp.alt_response(403, description="Acesso permitido apenas para administradores")
    @user_bp.alt_response(404, description="Usuário não encontrado")
    def post(self, user_id):
        claims = get_jwt()
        if not claims.get("is_admin", False):
            abort(403, message="Acesso permitido apenas para administradores.")

        try:
            return UserService.admin_reset_password(user_id)
        except ValueError as exc:
            abort(404, message=str(exc))
