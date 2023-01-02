from flask import has_request_context
from flask.globals import request_ctx
from werkzeug.local import LocalProxy


def _find_api():
    if has_request_context():
        if hasattr(request_ctx, "api"):
            return request_ctx.api
    return None


current_api = LocalProxy(_find_api)
