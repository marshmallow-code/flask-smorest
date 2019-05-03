from collections import OrderedDict
import json

from werkzeug.utils import cached_property
from flask import Response
from apispec.utils import build_reference


class JSONResponse(Response):
    """
    A Response class with extra useful helpers, i.e. ``.json`` property.

    Taken from https://github.com/frol/flask-restplus-server-example/
    Thanks Vlad Frolov
    """
    # pylint: disable=too-many-ancestors

    @cached_property
    def json(self):
        return json.loads(
            self.get_data(as_text=True),
            object_pairs_hook=OrderedDict
        )


class NoLoggingContext:
    """Context manager to disable logging temporarily

    Some tests purposely trigger errors. We don't want to log them.
    """

    def __init__(self, app):
        self.app = app

    def __enter__(self):
        self.logger_was_disabled = self.app.logger.disabled
        self.app.logger.disabled = True

    def __exit__(self, et, ev, tb):
        self.app.logger.disabled = self.logger_was_disabled


def get_schemas(spec):
    if spec.openapi_version.major < 3:
        return spec.to_dict()["definitions"]
    return spec.to_dict()["components"]["schemas"]


def build_ref(spec, component_type, obj):
    return build_reference(component_type, spec.openapi_version.major, obj)
