"""apispec plugins"""
from collections.abc import Mapping
import http
import re

import werkzeug.routing
from apispec import BasePlugin

from flask_smorest.utils import prepare_response
from flask_smorest.error_handler import ErrorSchema
from .constants import DEFAULT_RESPONSE_CONTENT_TYPE


# from flask-restplus
RE_URL = re.compile(r'<(?:[^:<>]+:)?([^<>]+)>')


def baseconverter2paramschema(converter):
    schema = {'type': 'string'}
    return schema


def unicodeconverter2paramschema(converter):
    schema = {'type': 'string'}
    bounds = re.compile(r"{([^}]*)}").findall(converter.regex)[0].split(",")
    schema["minLength"] = int(bounds[0])
    if len(bounds) == 1:
        schema["maxLength"] = int(bounds[0])
    elif bounds[1] != "":
        schema["maxLength"] = int(bounds[1])
    return schema


def integerconverter2paramschema(converter):
    schema = {'type': 'integer'}
    if converter.max is not None:
        schema['maximum'] = converter.max
    if converter.min is not None:
        schema['minimum'] = converter.min
    if not converter.signed:
        schema['minimum'] = max(schema.get('minimum', 0), 0)
    return schema


def floatconverter2paramschema(converter):
    schema = {'type': 'number'}
    if converter.max is not None:
        schema['maximum'] = converter.max
    if converter.min is not None:
        schema['minimum'] = converter.min
    if not converter.signed:
        schema['minimum'] = max(schema.get('minimum', 0), 0)
    return schema


def anyconverter2paramschema(converter):
    schema = {'type': 'string'}
    schema['enum'] = [
        # https://stackoverflow.com/questions/43662474/
        re.sub(r'\\(.)', r'\1', s) for s in converter.regex[3:-1].split('|')
    ]
    return schema


def uuidconverter2paramschema(converter):
    schema = {'type': 'string', 'format': 'uuid'}
    return schema


DEFAULT_CONVERTER_MAPPING = {
    werkzeug.routing.BaseConverter: baseconverter2paramschema,
    werkzeug.routing.AnyConverter: anyconverter2paramschema,
    werkzeug.routing.UnicodeConverter: unicodeconverter2paramschema,
    werkzeug.routing.IntegerConverter: integerconverter2paramschema,
    werkzeug.routing.FloatConverter: floatconverter2paramschema,
    werkzeug.routing.UUIDConverter: uuidconverter2paramschema,
}


class FlaskPlugin(BasePlugin):
    """Plugin to create OpenAPI paths from Flask rules

    Heavily copied from apispec.
    """
    def __init__(self):
        super().__init__()
        self.converter_mapping = dict(DEFAULT_CONVERTER_MAPPING)
        self.openapi_version = None

    def init_spec(self, spec):
        super().init_spec(spec)
        self.openapi_version = spec.openapi_version

    # From apispec
    @staticmethod
    def flaskpath2openapi(path):
        """Convert a Flask URL rule to an OpenAPI-compliant path.

        :param str path: Flask path template.
        """
        return RE_URL.sub(r'{\1}', path)

    def register_converter(self, converter, func):
        """Register custom path parameter converter

        :param BaseConverter converter: Converter.
            Subclass of werkzeug's BaseConverter
        :param callable func: Function returning a parameter schema from
            a converter intance
        """
        self.converter_mapping[converter] = func

    def rule_to_params(self, rule):
        """Get parameters from flask Rule"""
        params = []
        for argument in [a for a in rule.arguments if a not in rule.defaults]:
            param = {
                'in': 'path',
                'name': argument,
                'required': True,
            }
            converter = rule._converters[argument]
            # Inspired from apispec
            for converter_class in type(converter).__mro__:
                if converter_class in self.converter_mapping:
                    func = self.converter_mapping[converter_class]
                    break
            schema = func(converter)
            if self.openapi_version.major < 3:
                param.update(schema)
            else:
                param['schema'] = schema
            params.append(param)
        return params

    def path_helper(self, rule, operations, parameters, **kwargs):
        """Get path from flask Rule and set path parameters in operations"""

        for path_p in self.rule_to_params(rule):
            # If a parameter with same name and location is already
            # documented, update. Otherwise, append as new parameter.
            p_doc = next(
                (
                    p for p in parameters
                    if (
                        isinstance(p, Mapping) and
                        p['in'] == 'path' and
                        p['name'] == path_p['name']
                    )
                ),
                None
            )
            if p_doc is not None:
                # If parameter already documented, mutate to update doc
                # Ensure manual doc overwrites auto doc
                p_doc.update({**path_p, **p_doc})
            else:
                parameters.append(path_p)

        return self.flaskpath2openapi(rule.rule)


class ResponseReferencesPlugin(BasePlugin):
    """Plugin to add responses to spec

    This plugin automatically adds a response component for default responses
    on-the-fly when it is referenced in an operation.

    It applies to all HTTP status responses and to the default error response,
    allowing the user to pass responses as string like
    "UNPROCESSABLE_ENTITY" or "DEFAULT_ERROR".

    :param error_schema: :class:`Schema <marshmallow.Schema>` defining the
        error response structure.
    :param str content_type: Content type used in default responses.
    """
    def __init__(
            self,
            error_schema=ErrorSchema,
            response_content_type=DEFAULT_RESPONSE_CONTENT_TYPE
    ):
        self.error_schema = error_schema
        self.content_type = response_content_type
        self._available = self._available_responses()
        self._registered = set()

    def init_spec(self, spec):
        super().init_spec(spec)
        self.spec = spec

    def operation_helper(self, operations=None, **kwargs):
        """Inspired by MarshmallowPlugin.operation_helper

        Looking for `str` responses, adding the corresponding spec responses.
        `APISpec.clean_operations` will add a $ref for any response that is not
        a `dict`, it's this plugin's role to ensure that $ref exists.
        """
        for operation in (operations or {}).values():
            if not isinstance(operation, dict):
                continue
            for response in operation.get("responses", {}).values():
                if (
                        isinstance(response, str)
                        and response not in self._registered
                        and response in self._available
                ):
                    resp = self._available[response]
                    prepare_response(resp, self.spec, self.content_type)
                    self.spec.components.response(response, resp)
                    self._registered.add(response)

    def _available_responses(self):
        """Build responses for all status codes."""
        responses = {
            status.name: {
                'description': status.phrase,
                'schema': self.error_schema,
            }
            for status in http.HTTPStatus
        }
        # Also add a default error response
        responses['DEFAULT_ERROR'] = {
            'description': 'Default error response',
            'schema': self.error_schema,
        }
        return responses
