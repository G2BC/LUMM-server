from app.repositories.user_repository import UserRepository
from flask_jwt_extended import create_access_token, create_refresh_token, get_jwt_identity


class AuthService:
    @classmethod
    def login(cls, email: str, password: str):
        user = UserRepository.get_by_email(email)

        if not user or not user.check_password(password):
            raise ValueError("Credenciais inválidas.")

        identity = str(user.id)
        additional_claims = {"is_admin": user.is_admin, "email": user.email}

        return {
            "access_token": create_access_token(
                identity=identity, additional_claims=additional_claims
            ),
            "refresh_token": create_refresh_token(
                identity=identity, additional_claims=additional_claims
            ),
        }

    @classmethod
    def refresh(cls):
        identity = get_jwt_identity()
        user = UserRepository.get_by_id(identity)

        if not user:
            raise ValueError("Usuário não encontrado.")

        return {
            "access_token": create_access_token(
                identity=str(user.id),
                additional_claims={"is_admin": user.is_admin, "email": user.email},
            )
        }

    @classmethod
    def get_current_user(cls):
        identity = get_jwt_identity()
        user = UserRepository.get_by_id(identity)

        if not user:
            raise ValueError("Usuário não encontrado.")

        return user
