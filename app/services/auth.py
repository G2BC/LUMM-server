from app.repositories.user_repository import UserRepository
from flask_jwt_extended import create_access_token, create_refresh_token, get_jwt_identity


class AuthService:
    @classmethod
    def login(cls, email: str, password: str):
        user = UserRepository.get_by_email(email)

        if not user or not user.check_password(password):
            raise ValueError("Credenciais inválidas.")
        if not user.is_active:
            raise PermissionError("Conta inativa. Aguarde aprovação do administrador.")

        identity = str(user.id)
        additional_claims = {
            "is_admin": user.is_admin,
            "email": user.email,
            "must_change_password": user.must_change_password,
        }

        return {
            "access_token": create_access_token(
                identity=identity, additional_claims=additional_claims
            ),
            "refresh_token": create_refresh_token(
                identity=identity, additional_claims=additional_claims
            ),
            "must_change_password": user.must_change_password,
        }

    @classmethod
    def refresh(cls):
        identity = get_jwt_identity()
        user = UserRepository.get_by_id(identity)

        if not user:
            raise ValueError("Usuário não encontrado.")
        if not user.is_active:
            raise PermissionError("Conta inativa. Aguarde aprovação do administrador.")

        return {
            "access_token": create_access_token(
                identity=str(user.id),
                additional_claims={
                    "is_admin": user.is_admin,
                    "email": user.email,
                    "must_change_password": user.must_change_password,
                },
            )
        }

    @classmethod
    def get_current_user(cls):
        identity = get_jwt_identity()
        user = UserRepository.get_by_id(identity)

        if not user:
            raise ValueError("Usuário não encontrado.")

        return user

    @classmethod
    def change_password(cls, current_password: str, new_password: str):
        identity = get_jwt_identity()
        user = UserRepository.get_by_id(identity)

        if not user:
            raise ValueError("Usuário não encontrado.")
        if not user.is_active:
            raise PermissionError("Conta inativa. Aguarde aprovação do administrador.")
        if not user.check_password(current_password):
            raise ValueError("Senha atual inválida.")

        UserRepository.update_password(
            user=user,
            new_password=new_password,
            must_change_password=False,
        )

        additional_claims = {
            "is_admin": user.is_admin,
            "email": user.email,
            "must_change_password": False,
        }
        return {
            "access_token": create_access_token(
                identity=str(user.id), additional_claims=additional_claims
            ),
            "refresh_token": create_refresh_token(
                identity=str(user.id), additional_claims=additional_claims
            ),
            "must_change_password": False,
        }
