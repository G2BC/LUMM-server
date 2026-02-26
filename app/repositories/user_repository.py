import re
from typing import Optional

from app.extensions import db
from app.models.user import User
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError

EXACT_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class UserRepository:
    @classmethod
    def _build_users_query(cls, search: Optional[str] = None, is_active: Optional[bool] = None):
        query = User.query.order_by(User.id.asc())

        if search := (search or "").strip():
            if EXACT_EMAIL_RE.match(search):
                query = query.filter(User.email == search.lower())
            else:
                query = query.filter(
                    or_(
                        User.name.ilike(f"%{search}%"),
                        User.email.ilike(f"%{search}%"),
                    )
                )

        if is_active is not None:
            query = query.filter(User.is_active == is_active)

        return query

    @classmethod
    def get_users(cls, search: Optional[str] = None, is_active: Optional[bool] = None):
        return cls._build_users_query(search, is_active).all()

    @classmethod
    def get_users_pagination(
        cls,
        page,
        per_page,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
    ):
        return cls._build_users_query(search, is_active).paginate(
            page=page, per_page=per_page, error_out=False
        )

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

    @classmethod
    def activate_user(cls, user: User) -> User:
        user.is_active = True
        db.session.add(user)
        db.session.commit()
        return user

    @classmethod
    def deactivate_user(cls, user: User) -> User:
        user.is_active = False
        db.session.add(user)
        db.session.commit()
        return user

    @classmethod
    def update_password(cls, user: User, new_password: str, must_change_password: bool) -> User:
        user.set_password(new_password)
        user.must_change_password = must_change_password
        db.session.add(user)
        db.session.commit()
        return user

    @classmethod
    def update_admin_status(cls, user: User, is_admin: bool) -> User:
        user.is_admin = is_admin
        db.session.add(user)
        db.session.commit()
        return user
