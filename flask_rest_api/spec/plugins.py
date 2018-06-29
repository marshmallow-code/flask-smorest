"""Flask plugin

Heavily copied from apispec
"""

from urllib.parse import urljoin

import werkzeug.routing

from apispec import Path
from apispec.exceptions import PluginMethodNotImplementedError
from apispec.ext import flask as aef
from apispec.ext import marshmallow as aem


# From flask-apispec
DEFAULT_CONVERTER_MAPPING = {
    werkzeug.routing.UnicodeConverter: ('string', None),
    werkzeug.routing.IntegerConverter: ('integer', 'int32'),
    werkzeug.routing.FloatConverter: ('number', 'float'),
}
DEFAULT_TYPE = ('string', None)


class FlaskPlugin(aef.FlaskPlugin):
    """Plugin to create OpenAPI paths from Flask rules"""

    def __init__(self):
        super().__init__()
        self.converter_mapping = dict(DEFAULT_CONVERTER_MAPPING)

    def register_converter(self, converter, conv_type, conv_format=None):
        """Register custom path parameter converter

        :param BaseConverter converter: Converter.
            Subclass of werkzeug's BaseConverter
        :param str conv_type: Parameter type
        :param str conv_format: Parameter format (optional)
        """
        self.converter_mapping[converter] = (conv_type, conv_format)

    # Greatly inspired by flask-apispec
    def rule_to_params(self, rule):
        """Get parameters from flask Rule"""
        params = []
        for argument in rule.arguments:
            param = {
                'in': 'path',
                'name': argument,
                'required': True,
            }
            type_, format_ = self.converter_mapping.get(
                type(rule._converters[argument]), DEFAULT_TYPE)
            param['type'] = type_
            if format_ is not None:
                param['format'] = format_
            params.append(param)
        return params

    # Greatly inspired by apispec
    def path_helper(self, app, rule, operations=None, **kwargs):
        """Make Path from flask Rule"""
        path = self.flaskpath2openapi(rule.rule)
        app_root = app.config['APPLICATION_ROOT'] or '/'
        path = urljoin(app_root.rstrip('/') + '/', path.lstrip('/'))

        if operations:
            # Get path parameters
            path_parameters = self.rule_to_params(rule)
            if path_parameters:
                for operation in operations.values():
                    parameters = operation.setdefault('parameters', [])
                    # Add path parameters to documentation
                    for path_p in path_parameters:
                        parameters.append(path_p)

        return Path(path=path, operations=operations)


class MarshmallowPlugin(aem.MarshmallowPlugin):
    """Plugin introspecting marshmallow schemas"""

    def path_helper(self, *args, **kwargs):
        """No-op path helper

        apispec's path helper parses YAML docstring. We don't need this.
        """
        raise PluginMethodNotImplementedError
