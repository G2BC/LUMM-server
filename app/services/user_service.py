import secrets
import string

from app.models.user import User
from app.repositories.user_repository import UserRepository


class UserService:
    DEFAULT_PER_PAGE = 20
    MAX_PER_PAGE = 100

    @staticmethod
    def _parse_positive_user_id(value) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            raise ValueError("`current_user_id` inválido")
        if parsed < 1:
            raise ValueError("`current_user_id` inválido")
        return parsed

    @staticmethod
    def _generate_temporary_password(length: int = 12) -> str:
        alphabet = string.ascii_letters + string.digits
        while True:
            password = "".join(secrets.choice(alphabet) for _ in range(length))
            if (
                any(char.islower() for char in password)
                and any(char.isupper() for char in password)
                and any(char.isdigit() for char in password)
            ):
                return password

    @classmethod
    def list_users(
        cls,
        current_user_id=None,
        page=None,
        per_page=None,
        search=None,
        is_active=None,
    ):
        exclude_user_id = cls._parse_positive_user_id(current_user_id)

        if page is None and per_page is None:
            users = UserRepository.get_users(search, is_active, exclude_user_id=exclude_user_id)
            return {
                "items": users,
                "total": len(users),
                "page": None,
                "per_page": None,
                "pages": None,
            }

        if page is None:
            page = 1
        if per_page is None:
            per_page = cls.DEFAULT_PER_PAGE

        if not isinstance(page, int) or page < 1:
            raise ValueError("`page` deve ser um inteiro >= 1")
        if not isinstance(per_page, int) or per_page < 1:
            raise ValueError("`per_page` deve ser um inteiro >= 1")
        if per_page > cls.MAX_PER_PAGE:
            raise ValueError(f"`per_page` deve ser <= {cls.MAX_PER_PAGE}")

        pagination = UserRepository.get_users_pagination(
            page,
            per_page,
            search,
            is_active,
            exclude_user_id=exclude_user_id,
        )
        return {
            "items": pagination.items,
            "total": pagination.total,
            "page": page,
            "per_page": per_page,
            "pages": pagination.pages,
        }

    @staticmethod
    def create_user(data):
        email = data["email"].strip().lower()
        name = data["name"].strip()
        institution = data.get("institution")
        normalized_institution = institution.strip() if institution else None

        if UserRepository.get_by_email(email):
            raise ValueError("Email já cadastrado")

        return UserRepository.create_user(
            name=name,
            institution=normalized_institution,
            email=email,
            password=data["password"],
        )

    @staticmethod
    def get_user_by_id(id: str):
        user = UserRepository.get_by_id(id)

        if not user:
            raise ValueError("Usuário não encontrado")

        return user

    @staticmethod
    def approve_user(id: str):
        user = UserRepository.get_by_id(id)

        if not user:
            raise ValueError("Usuário não encontrado")

        if user.is_active:
            return user

        return UserRepository.activate_user(user)

    @staticmethod
    def deactivate_user(id: str):
        user = UserRepository.get_by_id(id)

        if not user:
            raise ValueError("Usuário não encontrado")

        if not user.is_active:
            return user

        return UserRepository.deactivate_user(user)

    @classmethod
    def admin_reset_password(cls, id: str):
        user = UserRepository.get_by_id(id)

        if not user:
            raise ValueError("Usuário não encontrado")

        temporary_password = cls._generate_temporary_password()
        UserRepository.update_password(
            user=user,
            new_password=temporary_password,
            must_change_password=True,
        )

        return {
            "user_id": str(user.id),
            "temporary_password": temporary_password,
            "must_change_password": True,
        }

    @staticmethod
    def update_role(actor_id: str, target_user_id: str, role: str):
        actor = UserRepository.get_by_id(actor_id)
        if not actor:
            raise ValueError("Usuário autenticado não encontrado")

        target_user = UserRepository.get_by_id(target_user_id)
        if not target_user:
            raise ValueError("Usuário não encontrado")

        normalized_role = (role or "").strip().lower()
        if normalized_role not in User.ROLES:
            raise ValueError("Role inválida")

        if actor.id == target_user.id and normalized_role != User.ROLE_ADMIN:
            raise ValueError("Você não pode revogar o próprio perfil de administrador")

        if target_user.role == normalized_role:
            return target_user

        return UserRepository.update_role(target_user, normalized_role)
