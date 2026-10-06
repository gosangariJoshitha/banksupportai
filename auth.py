"""
JWT Authentication middleware for Flask routes.
"""

from functools import wraps
from flask import request, redirect, url_for, flash
from database import verify_token


class UserProxy:
    """Wraps the JWT payload dict so templates can use dot-notation access."""
    def __init__(self, payload: dict):
        self._data = payload

    def __getattr__(self, item):
        try:
            return self._data[item]
        except KeyError:
            return None

    def get(self, key, default=None):
        return self._data.get(key, default)


def login_required(f):
    """Decorator: redirects to /login if JWT cookie is missing or invalid."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.cookies.get("jwt_token")
        if not token:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        payload = verify_token(token)
        if not payload:
            flash("Your session has expired. Please log in again.", "warning")
            return redirect(url_for("login"))
        request.current_user = UserProxy(payload)
        return f(*args, **kwargs)
    return decorated


def get_current_user():
    """Returns a UserProxy (dot-accessible) or None."""
    token = request.cookies.get("jwt_token")
    if not token:
        return None
    payload = verify_token(token)
    if not payload:
        return None
    return UserProxy(payload)
