from functools import wraps

from flask_jwt_extended import get_jwt, verify_jwt_in_request
from flask_smorest import abort


def require_admin(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        if get_jwt().get("role") != "admin":
            abort(403, message="Acesso permitido apenas para administradores")
        return fn(*args, **kwargs)

    return wrapper


def require_curator_or_admin(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        if get_jwt().get("role") not in {"curator", "admin"}:
            abort(403, message="Acesso permitido apenas para curadores ou administradores")
        return fn(*args, **kwargs)

    return wrapper
