from flask.views import MethodView
from flask_jwt_extended import jwt_required
from flask_smorest import Blueprint, abort

from app.schemas.login import ChangePasswordSchema, LoginRequestSchema, TokenSchema
from app.schemas.user_schemas import UserSchema
from app.services.auth import AuthService

auth_bp = Blueprint(
    "auth",
    "auth",
)


@auth_bp.route("/login")
class Login(MethodView):
    @auth_bp.arguments(LoginRequestSchema)
    @auth_bp.response(200, TokenSchema)
    @auth_bp.alt_response(401, description="Falha de autenticação")
    @auth_bp.alt_response(403, description="Conta inativa")
    def post(self, payload):
        try:
            return AuthService.login(payload["email"], payload["password"])
        except PermissionError as exc:
            abort(403, message=str(exc))
        except ValueError as exc:
            abort(401, message=str(exc))


@auth_bp.route("/refresh")
class RefreshToken(MethodView):
    @jwt_required(refresh=True)
    @auth_bp.response(200, TokenSchema)
    @auth_bp.alt_response(401, description="Falha ao renovar token")
    @auth_bp.alt_response(403, description="Conta inativa")
    def post(self):
        try:
            return AuthService.refresh()
        except PermissionError as exc:
            abort(403, message=str(exc))
        except ValueError as exc:
            abort(401, message=str(exc))


@auth_bp.route("/me")
class CurrentUser(MethodView):
    @jwt_required()
    @auth_bp.response(200, UserSchema)
    @auth_bp.alt_response(404, description="Usuário não encontrado")
    def get(self):
        try:
            return AuthService.get_current_user()
        except ValueError as exc:
            abort(404, message=str(exc))


@auth_bp.route("/change-password")
class ChangePassword(MethodView):
    @jwt_required()
    @auth_bp.arguments(ChangePasswordSchema)
    @auth_bp.response(200, TokenSchema)
    @auth_bp.alt_response(400, description="Senha atual inválida")
    @auth_bp.alt_response(403, description="Conta inativa")
    @auth_bp.alt_response(404, description="Usuário não encontrado")
    def post(self, payload):
        try:
            return AuthService.change_password(
                current_password=payload["current_password"],
                new_password=payload["new_password"],
            )
        except PermissionError as exc:
            abort(403, message=str(exc))
        except ValueError as exc:
            message = str(exc)
            if message == "Usuário não encontrado.":
                abort(404, message=message)
            abort(400, message=message)
