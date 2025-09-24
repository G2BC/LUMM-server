def register_blueprints(api) -> None:
    from .contact_routes import contact_bp
    from .species_routes import specie_bp
    from .user_routes import user_bp

    api.register_blueprint(user_bp, url_prefix="/users")
    api.register_blueprint(specie_bp, url_prefix="/species")
    api.register_blueprint(contact_bp, url_prefix="/contact")
