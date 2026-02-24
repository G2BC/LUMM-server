import hmac
from functools import wraps
from typing import Optional

from flask import current_app, request
from flask_smorest import abort


def _is_valid_api_key(supplied: Optional[str], expected: Optional[str]) -> bool:
    return bool(supplied and expected and hmac.compare_digest(supplied, expected))


def enforce_api_key() -> None:
    supplied = request.headers.get("X-API-Key")
    expected = current_app.config.get("API_KEY")
    if not _is_valid_api_key(supplied, expected):
        abort(401, message="API key inválida ou ausente.")


def require_api_key(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        enforce_api_key()
        return fn(*args, **kwargs)

    return wrapper
