from .user import user_bp


def register_blueprints(api):
    api.register_blueprint(user_bp, url_prefix="/users")

