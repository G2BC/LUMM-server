from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from dotenv import load_dotenv

db = SQLAlchemy()
migrate = Migrate()


def create_app():
    load_dotenv()

    app = Flask(__name__)
    app.config.from_object("app.config.Config")

    CORS(app)

    db.init_app(app)
    migrate.init_app(app, db)

    # models imports
    from app import models  # noqa: F401

    # routes register
    from app.routes import api_bp
    app.register_blueprint(api_bp, url_prefix="/api")

    return app
