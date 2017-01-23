"""API args parser

Inpired by webargs advanced usage custom parsers
https://webargs.readthedocs.io/en/latest/advanced.html#custom-parsers
"""
import re

from webargs import core
from webargs.flaskparser import FlaskParser, abort  # noqa


class NestedQueryFlaskParser(FlaskParser):
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
        m = re.match(r'(\w+)\.(.*)', key)
        if m:
            if r.get(m.group(1)) is None:
                r[m.group(1)] = {}
            structure_dict_pair(r[m.group(1)], m.group(2), value)
        else:
            r[key] = value
    r = {}
    for k, v in dict_.items():
        structure_dict_pair(r, k, v)
    return r


parser = NestedQueryFlaskParser()
