from contextlib import contextmanager

from flask import request
from flask.app import Rule

from apispec.utils import build_reference

# Getter functions are copied from apispec tests


def get_schemas(spec):
    if spec.openapi_version.major < 3:
        return spec.to_dict()["definitions"]
    return spec.to_dict()["components"]["schemas"]


def get_responses(spec):
    if spec.openapi_version.major < 3:
        return spec.to_dict()["responses"]
    return spec.to_dict()["components"]["responses"]


def get_parameters(spec):
    if spec.openapi_version.major < 3:
        return spec.to_dict()["parameters"]
    return spec.to_dict()["components"]["parameters"]


def get_headers(spec):
    return spec.to_dict()["components"]["headers"]


def build_ref(spec, component_type, obj):
    return build_reference(component_type, spec.openapi_version.major, obj)


@contextmanager
def request_ctx_with_current_api(app, blp, *args, **kwargs):
    """Create request context within an api

    It tricks globals.py::_find_current_api into thinking that
    request comes from this particular blueprint.
    """
    with app.test_request_context(*args, **kwargs):
        backup = request.url_rule
        request.url_rule = Rule("/", endpoint=f"{blp.name}.view")
        yield
        request.url_rule = backup
