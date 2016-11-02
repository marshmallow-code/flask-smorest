# -*- coding: utf-8 -*-
"""Flask plugin

Heavily copied from apispec
"""

from urllib.parse import urljoin

import werkzeug.routing

from apispec import Path
from apispec.ext.flask import flaskpath2swagger
from apispec.ext.marshmallow import resolve_schema_dict

from ..exceptions import EndpointRuleMissing

# From flask-apispec
CONVERTER_MAPPING = {
    werkzeug.routing.UnicodeConverter: ('string', None),
    werkzeug.routing.IntegerConverter: ('integer', 'int32'),
    werkzeug.routing.FloatConverter: ('number', 'float'),
}

DEFAULT_TYPE = ('string', None)


# Greatly inspired by flask-apispec
def rule_to_params(rule):

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
        if rule.defaults and argument in rule.defaults:
            param['default'] = rule.defaults[argument]
        params.append(param)
    return params


# Greatly inspired by apispec
def flask_path_helper(spec, app, endpoint, operations={}, **kwargs):

    # Resolve Flask path
    try:
        # WARNING: Assume 1 rule per view function for now
        rule = app.url_map._rules_by_endpoint[endpoint][0]
    except KeyError:
        raise EndpointRuleMissing(
            "Could not find rule for endpoint '{}'".format(endpoint))
    path = flaskpath2swagger(rule.rule)
    app_root = app.config['APPLICATION_ROOT'] or '/'
    path = urljoin(app_root.rstrip('/') + '/', path.lstrip('/'))

    if operations:
        operations = operations.copy()
        # Get path parameters
        path_parameters = rule_to_params(rule)
        if path_parameters:
            for operation in operations.values():
                operation['parameters'] = operation.get('parameters', list())
                operation['parameters'].extend(path_parameters)
        # Translate Marshmallow Schema
        for operation in operations.values():
            for response in operation.get('responses', {}).values():
                if 'schema' in response:
                    # If the API returns a list,
                    # the schema is specfied as [schema]
                    if isinstance(response['schema'], list):
                        response['schema'] = [
                            resolve_schema_dict(spec, response['schema'][0])
                            ]
                    else:
                        response['schema'] = resolve_schema_dict(
                            spec, response['schema'])

            for parameter in operation.get('parameters', []):
                if 'schema' in parameter:
                    parameter['schema'] = resolve_schema_dict(
                        spec, parameter['schema'])

    path = Path(path=path, operations=operations)

    return path


def schema_definition_x_property(spec, name, schema, **kwargs):
    """Pass provided extensions properties as is to the spec

       Extensions properties begin with 'x-'
       http://swagger.io/specification/#vendorExtensions
    """
    return {k: v for k, v in kwargs.items() if k.startswith('x-')}


def setup(spec):
    """Setup for the plugin."""
    spec.register_path_helper(flask_path_helper)
    spec.register_definition_helper(schema_definition_x_property)
