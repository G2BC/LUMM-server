from app.repositories.user_repository import UserRepository


class UserService:
    @classmethod
    def list_users(self, page=None, per_page=None):
        if page and per_page:
            pagination = UserRepository.get_users_pagination(page, per_page)
            return {
                "items": pagination.items,
                "total": pagination.total,
                "page": page,
                "per_page": per_page,
                "pages": pagination.pages,
            }

        users = UserRepository.get_users()
        return {
            "items": users,
            "total": len(users),
            "page": None,
            "per_page": None,
            "pages": None,
        }

    @classmethod
    def create_user(cls, data):
        email = data["email"].strip().lower()
        name = data["name"].strip()
        institution = data.get("institution")
        normalized_institution = institution.strip() if institution else None

        if UserRepository.get_by_email(email):
            raise ValueError("Email já cadastrado.")

        return UserRepository.create_user(
            name=name,
            institution=normalized_institution,
            email=email,
            password=data["password"],
        )

    @classmethod
    def get_user_by_id(cls, id: str):
        user = UserRepository.get_by_id(id)

        if not user:
            raise ValueError("Usuário não encontrado.")

        return user
