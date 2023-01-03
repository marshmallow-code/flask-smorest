from flask import has_request_context
from werkzeug.local import LocalProxy
from .utils import get_appcontext


def _find_api():
    ctx = get_appcontext()
    if has_request_context() and "_current_api" in ctx:
        return ctx["_current_api"]
    return None


current_api = LocalProxy(_find_api)
"""A proxy for the current Api

Only available within a request context and only
if current blueprint is registered in a smorest api.
"""


def update_current_api(api):
    """Update context-local `current_api`

    This is an internal function.

    :param flask_smorest.Api api
    """
    get_appcontext()["_current_api"] = api


def teardown_current_api():
    """Clean up context-local `current_api`

    This is an internal function.
    """
    ctx = get_appcontext()
    if "_current_api" in ctx:
        del ctx["_current_api"]
