from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS
from flask_migrate import Migrate
from flask_smorest import Api

from .extensions import db

migrate = Migrate()
load_dotenv()


def create_app():
    app = Flask(__name__)
    app.config.from_object("app.config.Config")

    CORS(app)

    db.init_app(app)
    migrate.init_app(app, db)

    api = Api(app)

    @app.route("/health", methods=["GET"])
    def health():
        return {"status": "ok"}, 200

    with app.app_context():
        from app import models  # noqa: F401
        from app.routes import register_blueprints

        register_blueprints(api)

    return app
