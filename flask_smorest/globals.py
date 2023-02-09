from flask import current_app, has_request_context, request
from werkzeug.local import LocalProxy


def _find_current_api():
    if has_request_context():
        apis = current_app.extensions["flask-smorest"]["apis"].values()
        blueprints = set(request.blueprints)
        for api in (x["ext_obj"] for x in apis):
            if api._registered_blueprint_names & blueprints:
                return api
    return None


current_api = LocalProxy(_find_current_api)
"""A proxy for the current Api

Only available within a request context and only
if current blueprint is registered in a smorest api.
"""
