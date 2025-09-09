from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS
from flask_migrate import Migrate
from flask_smorest import Api
from flask_sqlalchemy import SQLAlchemy

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

    api = Api(app)

    # routes register
    from app.routes import register_blueprints

    register_blueprints(api)

    return app
