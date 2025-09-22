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
