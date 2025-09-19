def register_blueprints(api) -> None:
    from .user_routes import user_bp

    api.register_blueprint(user_bp, url_prefix="/users")

    from .species_routes import specie_bp

    api.register_blueprint(specie_bp, url_prefix="/species")
