from flask import current_app, has_request_context, request
from werkzeug.local import LocalProxy


def _find_current_api():
    if has_request_context():
        blp_name_to_api = current_app.extensions["flask-smorest"]["blp_name_to_api"]
        for blp_name in request.blueprints:
            api = blp_name_to_api.get(blp_name)
            if api:
                return api

    return None


current_api = LocalProxy(_find_current_api)
"""A proxy for the current Api

Only available within a request context and only
if current blueprint is registered in a smorest api.
"""
