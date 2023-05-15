"""Globals"""
from flask import current_app, request
from werkzeug.local import LocalProxy

from .exceptions import CurrentApiNotAvailableError


def _find_current_api():
    blp_name_to_api = current_app.extensions["flask-smorest"]["blp_name_to_api"]
    for blp_name in request.blueprints:
        api = blp_name_to_api.get(blp_name)
        if api:
            return api
    raise CurrentApiNotAvailableError("Current Blueprint not registered in any Api.")


# Proxy for the current Api. Only available within a request context and only
# if current Blueprint is registered in a flask-smorest Api.
current_api = LocalProxy(_find_current_api)
