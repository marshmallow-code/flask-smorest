"""apispec plugins"""
from collections.abc import Mapping
import re

import werkzeug.routing
from apispec import BasePlugin


# from flask-restplus
RE_URL = re.compile(r"<(?:[^:<>]+:)?([^<>]+)>")


def baseconverter2paramschema(converter):
    schema = {"type": "string"}
    return schema


def unicodeconverter2paramschema(converter):
    schema = {"type": "string"}
    bounds = re.compile(r"{([^}]*)}").findall(converter.regex)[0].split(",")
    schema["minLength"] = int(bounds[0])
    if len(bounds) == 1:
        schema["maxLength"] = int(bounds[0])
    elif bounds[1] != "":
        schema["maxLength"] = int(bounds[1])
    return schema


def integerconverter2paramschema(converter):
    schema = {"type": "integer"}
    if converter.max is not None:
        schema["maximum"] = converter.max
    if converter.min is not None:
        schema["minimum"] = converter.min
    if not converter.signed:
        schema["minimum"] = max(schema.get("minimum", 0), 0)
    return schema


def floatconverter2paramschema(converter):
    schema = {"type": "number"}
    if converter.max is not None:
        schema["maximum"] = converter.max
    if converter.min is not None:
        schema["minimum"] = converter.min
    if not converter.signed:
        schema["minimum"] = max(schema.get("minimum", 0), 0)
    return schema


def anyconverter2paramschema(converter):
    schema = {"type": "string"}
    schema["enum"] = [
        # https://stackoverflow.com/questions/43662474/
        re.sub(r"\\(.)", r"\1", s)
        for s in converter.regex[3:-1].split("|")
    ]
    return schema


def uuidconverter2paramschema(converter):
    schema = {"type": "string", "format": "uuid"}
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
        return RE_URL.sub(r"{\1}", path)

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
                "in": "path",
                "name": argument,
                "required": True,
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
                param["schema"] = schema
            params.append(param)
        return params

    def path_helper(self, rule, operations, parameters, **kwargs):
        """Get path from flask Rule and set path parameters in operations"""

        for path_p in self.rule_to_params(rule):
            # If a parameter with same name and location is already
            # documented, update. Otherwise, append as new parameter.
            p_doc = next(
                (
                    p
                    for p in parameters
                    if (
                        isinstance(p, Mapping)
                        and p["in"] == "path"
                        and p["name"] == path_p["name"]
                    )
                ),
                None,
            )
            if p_doc is not None:
                # If parameter already documented, mutate to update doc
                # Ensure manual doc overwrites auto doc
                p_doc.update({**path_p, **p_doc})
            else:
                parameters.append(path_p)

        return self.flaskpath2openapi(rule.rule)
