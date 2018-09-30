"""Arguments parsing"""
import re

from webargs import core
from webargs.flaskparser import FlaskParser
from apispec.ext.marshmallow.openapi import __location_map__

from .exceptions import InvalidLocation


class ArgumentsMixin:
    """Extend Blueprint to add arguments parsing feature"""

    ARGUMENTS_PARSER = FlaskParser()

    def arguments(self, schema, *, location='json', required=True, **kwargs):
        """Decorator specifying the schema used to deserialize parameters

        :param type|Schema schema: Marshmallow ``Schema`` class or instance
            used to deserialize and validate the argument.
        :param str location: Location of the argument.
        :param bool required: Whether argument is required (default: True).
            This only affects `body` arguments as, in this case, the docs
            expose the whole schema as a `required` parameter.
            For other locations, the schema is turned into an array of
            parameters and their required value is inferred from the schema.
        :param dict kwargs: Keyword arguments passed to the webargs
            :meth:`use_args <webargs.core.Parser.use_args>` decorator used
            internally.

        See :doc:`Arguments <arguments>`.
        """
        # TODO: This shouldn't be needed. I think I did this because apispec
        # worked better with instances, but this should have been solved since.
        if isinstance(schema, type):
            schema = schema()

        try:
            openapi_location = __location_map__[location]
        except KeyError:
            raise InvalidLocation(
                "{} is not a valid location".format(location))

        # At this stage, put schema instance in doc dictionary. Il will be
        # replaced later on by $ref or json.
        parameters = {
            'in': openapi_location,
            'required': required,
            'schema': schema,
        }

        def decorator(func):
            # Add parameter to parameters list in doc info in function object
            func._apidoc = getattr(func, '_apidoc', {})
            func._apidoc.setdefault('parameters', []).append(parameters)
            # Call use_args (from webargs) to inject params in function
            return self.ARGUMENTS_PARSER.use_args(
                schema, locations=[location], **kwargs)(func)
        return decorator


# Copied from webargs advanced usage custom parsers
# https://webargs.readthedocs.io/en/latest/advanced.html#custom-parsers
class NestedQueryArgsParser(FlaskParser):
    """Parses nested query args

    This parser handles nested query args. It expects nested levels
    delimited by a period and then deserializes the query args into a
    nested dict.

    For example, the URL query params `?name.first=John&name.last=Boone`
    will yield the following dict:

        {
            'name': {
                'first': 'John',
                'last': 'Boone',
            }
        }
    """
    def parse_querystring(self, req, name, field):
        return core.get_value(_structure_dict(req.args), name, field)


def _structure_dict(dict_):
    def structure_dict_pair(r, key, value):
        match = re.match(r'(\w+)\.(.*)', key)
        if match:
            if r.get(match.group(1)) is None:
                r[match.group(1)] = {}
            structure_dict_pair(r[match.group(1)], match.group(2), value)
        else:
            r[key] = value
    ret = {}
    for key, val in dict_.items():
        structure_dict_pair(ret, key, val)
    return ret
