import hmac
from functools import wraps

from app import app
from flask import abort, request


def require_api_key(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        supplied = request.headers.get("X-API-Key")
        expected = app.config.get("API_KEY")
        if not supplied or not expected or not hmac.compare_digest(supplied, expected):
            abort(401, description="API key inválida ou ausente.")
        return fn(*args, **kwargs)

    return wrapper
