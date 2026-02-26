import os
from datetime import timedelta


class Config:
    API_TITLE = "LUMM"
    API_VERSION = "v1"
    OPENAPI_VERSION = "3.0.3"
    OPENAPI_URL_PREFIX = ""
    OPENAPI_SWAGGER_UI_PATH = "/docs"
    OPENAPI_SWAGGER_UI_URL = "https://cdn.jsdelivr.net/npm/swagger-ui-dist/"
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", "postgresql://postgres:postgres@db:5432/app"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv("SECRET_KEY", "changeme")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(seconds=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES", "900")))
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(
        seconds=int(os.getenv("JWT_REFRESH_TOKEN_EXPIRES", "2592000"))
    )
    API_KEY = os.getenv("API_KEY", "")
    APP_ENV = os.getenv("APP_ENV", "development").strip().lower()
    _default_cors_origins = (
        "http://localhost:3000,http://localhost:5173,http://localhost:3333,http://127.0.0.1:3000,http://127.0.0.1:5173,http://127.0.0.1:3333"
        if APP_ENV == "development"
        else "https://lumm.uneb.br"
    )
    CORS_ALLOWED_ORIGINS = [
        origin.strip()
        for origin in os.getenv("CORS_ALLOWED_ORIGINS", _default_cors_origins).split(",")
        if origin.strip()
    ]
    CORS_ALLOW_HEADERS = [
        header.strip()
        for header in "Content-Type,Authorization,X-API-Key".split(",")
        if header.strip()
    ]
    CORS_METHODS = [
        method.strip().upper()
        for method in "GET,POST,PUT,PATCH,DELETE,OPTIONS".split(",")
        if method.strip()
    ]
