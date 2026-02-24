from typing import Optional

from app.extensions import db
from app.models.user import User
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError


class UserRepository:
    @classmethod
    def get_users(cls):
        return User.query.all()

    @classmethod
    def get_users_pagination(cls, page, per_page):
        return User.query.paginate(page=page, per_page=per_page, error_out=False)

    @classmethod
    def get_by_email(cls, email: str):
        return User.query.filter(func.lower(User.email) == email.strip().lower()).first()

    @classmethod
    def get_by_id(cls, id: str):
        try:
            parsed_id = int(id)
        except (TypeError, ValueError):
            return None

        return User.query.filter_by(id=parsed_id).first()

    @classmethod
    def create_user(cls, name: str, institution: Optional[str], email: str, password: str) -> User:
        user = User(name=name, institution=institution, email=email.strip().lower())
        user.set_password(password)
        db.session.add(user)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            raise ValueError("Email já cadastrado.")
        return user
