from flask import Blueprint, jsonify
from app.services.user import get_all_users

user_bp = Blueprint("users", __name__)


@user_bp.route("/", methods=["GET"])
def list_users():
    users = get_all_users()
    return jsonify(users)
