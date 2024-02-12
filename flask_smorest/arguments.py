"""Arguments parsing"""

from collections import abc
from copy import deepcopy
from functools import wraps
import http

from webargs.flaskparser import FlaskParser

from .utils import deepupdate


class ArgumentsMixin:
    """Extend Blueprint to add arguments parsing feature"""

    ARGUMENTS_PARSER = FlaskParser()

    def arguments(
        self,
        schema,
        *,
        location="json",
        content_type=None,
        required=True,
        description=None,
        example=None,
        examples=None,
        **kwargs
    ):
        """Decorator specifying the schema used to deserialize parameters

        :param type|Schema schema: Marshmallow ``Schema`` class or instance
            used to deserialize and validate the argument.
        :param str location: Location of the argument.
        :param str content_type: Content type of the argument.
            Should only be used in conjunction with ``json``, ``form`` or
            ``files`` location.
            The default value depends on the location and is set in
            ``Blueprint.DEFAULT_LOCATION_CONTENT_TYPE_MAPPING``.
            This is only used for documentation purpose.
        :param bool required: Whether argument is required (default: True).
        :param str description: Argument description.
        :param dict example: Parameter example.
        :param dict examples: Parameter examples.
        :param kwargs: Keyword arguments passed to the webargs
            :meth:`use_args <webargs.core.Parser.use_args>` decorator used
            internally.

        The `required` and `description` only affect `body` arguments
        (OpenAPI 2) or `requestBody` (OpenAPI 3), because the docs expose the
        whole schema. For other locations, the schema is turned into an array
        of parameters and the required/description value of each parameter item
        is taken from the corresponding field in the schema.

        The `example` and `examples` parameters are mutually exclusive and
        should only be used with OpenAPI 3 and when location is ``json``.

        See :doc:`Arguments <arguments>`.
        """
        # At this stage, put schema instance in doc dictionary. Il will be
        # replaced later on by $ref or json.
        parameters = {
            "in": location,
            "required": required,
            "schema": schema,
        }
        if content_type is not None:
            parameters["content_type"] = content_type
        if example is not None:
            parameters["example"] = example
        if examples is not None:
            parameters["examples"] = examples
        if description is not None:
            parameters["description"] = description

        error_status_code = kwargs.get(
            "error_status_code", self.ARGUMENTS_PARSER.DEFAULT_VALIDATION_STATUS
        )

        def decorator(func):
            @wraps(func)
            def wrapper(*f_args, **f_kwargs):
                return func(*f_args, **f_kwargs)

            # Add parameter to parameters list in doc info in function object
            # The deepcopy avoids modifying the wrapped function doc
            wrapper._apidoc = deepcopy(getattr(wrapper, "_apidoc", {}))
            docs = wrapper._apidoc.setdefault("arguments", {})
            docs.setdefault("parameters", []).append(parameters)
            docs.setdefault("responses", {})[error_status_code] = http.HTTPStatus(
                error_status_code
            ).name

            # Call use_args (from webargs) to inject params in function
            return self.ARGUMENTS_PARSER.use_args(schema, location=location, **kwargs)(
                wrapper
            )

        return decorator

    def _prepare_arguments_doc(self, doc, doc_info, *, api, spec, **kwargs):
        # This callback should run first as it overrides existing parameters
        # in doc. Following callbacks should append to parameters list.
        operation = doc_info.get("arguments")
        if operation:
            parameters = [
                p for p in operation["parameters"] if isinstance(p, abc.Mapping)
            ]
            # OAS 2
            if spec.openapi_version.major < 3:
                for param in parameters:
                    if param["in"] in (self.DEFAULT_LOCATION_CONTENT_TYPE_MAPPING):
                        content_type = (
                            param.pop("content_type", None)
                            or self.DEFAULT_LOCATION_CONTENT_TYPE_MAPPING[param["in"]]
                        )
                        if content_type != api.DEFAULT_REQUEST_BODY_CONTENT_TYPE:
                            operation["consumes"] = [
                                content_type,
                            ]
                        # body and formData are mutually exclusive
                        break
            # OAS 3
            else:
                for param in parameters:
                    if param["in"] in (self.DEFAULT_LOCATION_CONTENT_TYPE_MAPPING):
                        request_body = {
                            x: param[x]
                            for x in ("description", "required")
                            if x in param
                        }
                        fields = {
                            x: param.pop(x)
                            for x in ("schema", "example", "examples")
                            if x in param
                        }
                        content_type = (
                            param.pop("content_type", None)
                            or self.DEFAULT_LOCATION_CONTENT_TYPE_MAPPING[param["in"]]
                        )
                        request_body["content"] = {content_type: fields}
                        operation["requestBody"] = request_body
                        # There can be only one requestBody
                        operation["parameters"].remove(param)
                        if not operation["parameters"]:
                            del operation["parameters"]
                        break
            doc = deepupdate(doc, operation)
        return doc
