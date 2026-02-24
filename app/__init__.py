from dotenv import load_dotenv
from flask import Flask, request
from flask_cors import CORS
from flask_migrate import Migrate
from flask_smorest import Api

from .extensions import db, jwt
from .utils.require_api_key import enforce_api_key

migrate = Migrate()
load_dotenv()


def create_app():
    app = Flask(__name__)
    app.config.from_object("app.config.Config")

    CORS(app)

    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)

    api = Api(app)

    @jwt.unauthorized_loader
    def handle_missing_token(_reason):
        return {"code": 401, "status": "Unauthorized", "message": "Token de acesso ausente."}, 401

    @jwt.invalid_token_loader
    def handle_invalid_token(_reason):
        return {"code": 401, "status": "Unauthorized", "message": "Token inválido."}, 401

    @jwt.expired_token_loader
    def handle_expired_token(_jwt_header, _jwt_payload):
        return {"code": 401, "status": "Unauthorized", "message": "Token expirado."}, 401

    @app.before_request
    def require_api_key_for_api_routes():
        if request.method == "OPTIONS":
            return None

        path = request.path
        protected_prefixes = ("/auth", "/users", "/species", "/contact")

        if any(path == prefix or path.startswith(f"{prefix}/") for prefix in protected_prefixes):
            enforce_api_key()

        return None

    @app.route("/", methods=["GET"])
    def index():
        return {"name": "LUMM API"}, 200

    @app.route("/health", methods=["GET"])
    def health():
        return {"status": "ok"}, 200

    with app.app_context():
        from app import models  # noqa: F401
        from app.routes import register_blueprints

        register_blueprints(api)

    return app
