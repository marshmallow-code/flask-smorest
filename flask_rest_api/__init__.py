# -*- coding: utf-8 -*-
"""Api extension initialization"""

from werkzeug.exceptions import default_exceptions
from flask_cors import CORS
from webargs.flaskparser import abort  # noqa

from .error_handlers import _handle_http_exception
from .etag import is_etag_enabled, conditional  # noqa
from .spec import docs
from .blueprint import Blueprint  # noqa


def init_app(app):
    """Initialize api"""

    docs.init_app(app)

    # CORS is setup the most permissive way, to avoid cross-origin
    # issues when serving the spec or trying it using swagger-ui.
    CORS(app)

    # Can't register a handler for HTTPException, so let's register
    # default handler for each code explicitly.
    # https://github.com/pallets/flask/issues/941#issuecomment-118975275
    for code in default_exceptions:
        app.register_error_handler(code, _handle_http_exception)
