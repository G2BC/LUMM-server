from app.models.user import User
from app import db


def get_users():
    return User.query.all()


def add_user(name, email):
    user = User(name=name, email=email)
    db.session.add(user)
    db.session.commit()
    return user
