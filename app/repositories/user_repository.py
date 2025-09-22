from app.models.user import User


class UserRepository:
    @classmethod
    def get_users():
        return User.query.all()

    @classmethod
    def get_users_pagination(page, per_page):
        return User.query.paginate(page=page, per_page=per_page, error_out=False)
