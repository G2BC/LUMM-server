from .specie_routes import specie_bp
from .user_routes import user_bp


def register_blueprints(api):
    api.register_blueprint(user_bp, url_prefix="/users")
    api.register_blueprint(specie_bp, url_prefix="/species")
