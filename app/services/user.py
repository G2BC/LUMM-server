from app.repositories.user import get_users, add_user


def get_all_users():
    users = get_users()
    return [u.to_dict() for u in users]


def create_user(data):
    return add_user(data["name"], data["email"])
