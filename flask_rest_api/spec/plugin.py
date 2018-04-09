"""Flask plugin

Heavily copied from apispec
"""

from urllib.parse import urljoin

import werkzeug.routing

from apispec import Path
from apispec.ext.flask import flaskpath2swagger

# From flask-apispec
CONVERTER_MAPPING = {
    werkzeug.routing.UnicodeConverter: ('string', None),
    werkzeug.routing.IntegerConverter: ('integer', 'int32'),
    werkzeug.routing.FloatConverter: ('number', 'float'),
}

DEFAULT_TYPE = ('string', None)


# Greatly inspired by flask-apispec
def rule_to_params(rule):
    """Get parameters from flask Rule"""
    params = []
    for argument in rule.arguments:
        param = {
            'in': 'path',
            'name': argument,
            'required': True,
        }
        type_, format_ = CONVERTER_MAPPING.get(
            type(rule._converters[argument]), DEFAULT_TYPE)
        param['type'] = type_
        if format_ is not None:
            param['format'] = format_
        params.append(param)
    return params


# Greatly inspired by apispec
def flask_path_helper(spec, app, rule, operations=None, **kwargs):
    """Make Path from flask Rule"""
    path = flaskpath2swagger(rule.rule)
    app_root = app.config['APPLICATION_ROOT'] or '/'
    path = urljoin(app_root.rstrip('/') + '/', path.lstrip('/'))

    if operations:
        # Get path parameters
        path_parameters = rule_to_params(rule)
        if path_parameters:
            for operation in operations.values():
                parameters = operation.setdefault('parameters', [])
                # Add path parameters to documentation
                for path_p in path_parameters:
                    parameters.append(path_p)

    return Path(path=path, operations=operations)


def setup(spec):
    """Setup for the plugin."""
    spec.register_path_helper(flask_path_helper)
