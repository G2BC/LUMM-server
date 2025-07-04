from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from app.utils.generate_uuid import generate_uuid


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.String, primary_key=True, default=generate_uuid)
    name = db.Column(db.String(100), nullable=False)
    institution = db.Column(db.String(150), nullable=True)
    email = db.Column(db.String(150), nullable=False, unique=True)
    password = db.Column(db.String(150), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now())

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "institution": self.institution,
            "is_admin": self.is_admin,
            "created_at": self.created_at.isoformat(),
        }
