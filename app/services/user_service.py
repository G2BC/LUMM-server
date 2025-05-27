from app.repositories.user_repository import get_users, get_users_pagination


def list_users(page=None, per_page=None):
    if page and per_page:
        pagination = get_users_pagination(page, per_page)
        return {
            "items": pagination.items,
            "total": pagination.total,
            "page": page,
            "per_page": per_page,
            "pages": pagination.pages,
        }

    users = get_users()
    return {
        "items": users,
        "total": len(users),
        "page": None,
        "per_page": None,
        "pages": None,
    }
