from flask.views import MethodView
from flask_smorest import Blueprint
from app.services.user import get_all_users
from app.schemas.user import UserSchema


user_bp = Blueprint(
    "users", "users", url_prefix="/users",
    description="Operações relacionadas aos usuários"
)


@user_bp.route("")
class UsersList(MethodView):
    @user_bp.response(200, UserSchema(many=True))
    def get(self):
        return get_all_users()