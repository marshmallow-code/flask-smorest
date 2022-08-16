"""Response processor"""

from collections import abc
from copy import deepcopy
from functools import wraps
import http

from werkzeug import Response
from flask import jsonify

from .utils import (
    deepupdate,
    remove_none,
    resolve_schema_instance,
    get_appcontext,
    prepare_response,
    unpack_tuple_response,
    set_status_and_headers_in_response,
)


class ResponseMixin:
    """Extend Blueprint to add response handling"""

    def response(
        self,
        status_code,
        schema=None,
        *,
        content_type=None,
        description=None,
        example=None,
        examples=None,
        headers=None,
    ):
        """Decorator generating an endpoint response

        :param int|str|HTTPStatus status_code: HTTP status code.
            Used if none is returned from the view function.
        :param schema schema|str|dict: :class:`Schema <marshmallow.Schema>`
            class or instance or reference or dict.
            If not None, will be used to serialize response data.
        :param str content_type: Content type of the response.
        :param str description: Description of the response (default: None).
        :param dict example: Example of response message.
        :param dict examples: Examples of response message.
        :param dict headers: Headers returned by the response.

        The decorated function is expected to return the same types of value
        than a typical flask view function, except the body part may be an
        object or a list of objects to serialize with the schema, rather than
        a ``string``.

        If the decorated function returns a ``Response`` object, the ``schema``
        and ``status_code`` parameters are only used to document the resource.
        Only in this case, ``schema`` may be a reference as string or a schema
        definition as dict.

        The `example` and `examples` parameters are mutually exclusive. The
        latter should only be used with OpenAPI 3.

        The `example`, `examples` and `headers` parameters are only used to
        document the resource.

        See :doc:`Response <response>`.
        """
        schema = resolve_schema_instance(schema)

        # Document response (schema, description,...) in the API doc
        doc_schema = self._make_doc_response_schema(schema)
        if description is None:
            description = http.HTTPStatus(int(status_code)).phrase
        resp_doc = remove_none(
            {
                "schema": doc_schema,
                "description": description,
                "example": example,
                "examples": examples,
                "headers": headers,
            }
        )
        resp_doc["content_type"] = content_type

        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):

                # Execute decorated function
                result_raw, r_status_code, r_headers = unpack_tuple_response(
                    func(*args, **kwargs)
                )

                # If return value is a werkzeug Response, return it
                if isinstance(result_raw, Response):
                    set_status_and_headers_in_response(
                        result_raw, r_status_code, r_headers
                    )
                    return result_raw

                # Dump result with schema if specified
                if schema is None:
                    result_dump = result_raw
                else:
                    result_dump = schema.dump(result_raw)

                # Store result in appcontext (may be used for ETag computation)
                appcontext = get_appcontext()
                appcontext["result_dump"] = result_dump

                # Build response
                resp = jsonify(self._prepare_response_content(result_dump))
                set_status_and_headers_in_response(resp, r_status_code, r_headers)
                if r_status_code is None:
                    resp.status_code = status_code

                return resp

            # Store doc in wrapper function
            # The deepcopy avoids modifying the wrapped function doc
            wrapper._apidoc = deepcopy(getattr(wrapper, "_apidoc", {}))
            wrapper._apidoc.setdefault("response", {}).setdefault("responses", {})[
                status_code
            ] = resp_doc
            # Indicate this code is a success status code
            # Helps other decorators documenting success responses
            wrapper._apidoc.setdefault("success_status_codes", []).append(status_code)

            return wrapper

        return decorator

    def alt_response(
        self,
        status_code,
        response=None,
        *,
        schema=None,
        content_type=None,
        description=None,
        example=None,
        examples=None,
        headers=None,
        success=False,
    ):
        """Decorator documenting an alternative response

        :param int|str|HTTPStatus status_code: HTTP status code.
        :param str response: Reponse reference.
        :param schema schema|str|dict: :class:`Schema <marshmallow.Schema>`
            class or instance or reference or dict.
        :param str description: Description of the response (default: None).
        :param dict example: Example of response message.
        :param dict examples: Examples of response message.
        :param dict headers: Headers returned by the response.
        :param bool success: ``True`` if this response is part of the normal
            flow of the function. Default: ``False``.

        This decorator allows the user to document an alternative response.
        This can be an error managed with :func:`abort <abort>` or any response
        that is not the primary flow of the function documented by
        :meth:`Blueprint.reponse <Blueprint.response>`.

        When a response reference is passed as ``response``, it is used as
        description and the keyword arguments are ignored. Otherwise, a
        description is built from the keyword arguments.

        See :ref:`document-alternative-responses`.
        """
        # Response ref is passed
        if response is not None:
            resp_doc = response
        # Otherwise, build response description
        else:
            schema = resolve_schema_instance(schema)

            # Document response (schema, description,...) in the API doc
            doc_schema = self._make_doc_response_schema(schema)
            if description is None:
                description = http.HTTPStatus(int(status_code)).phrase
            resp_doc = remove_none(
                {
                    "schema": doc_schema,
                    "description": description,
                    "example": example,
                    "examples": examples,
                    "headers": headers,
                }
            )
            resp_doc["content_type"] = content_type

        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)

            # Store doc in wrapper function
            # The deepcopy avoids modifying the wrapped function doc
            wrapper._apidoc = deepcopy(getattr(wrapper, "_apidoc", {}))
            wrapper._apidoc.setdefault("response", {}).setdefault("responses", {})[
                status_code
            ] = resp_doc
            if success:
                # Indicate this code is a success status code
                # Helps other decorators documenting success responses
                wrapper._apidoc.setdefault("success_status_codes", []).append(
                    status_code
                )
            return wrapper

        return decorator

    @staticmethod
    def _make_doc_response_schema(schema):
        """Override this to modify response schema in docs

        This can be used to document a wrapping structure.

            Example: ::

                @staticmethod
                def _make_doc_response_schema(schema):
                    if schema:
                        return type(
                            'Wrap' + schema.__class__.__name__,
                            (ma.Schema, ),
                            {'data': ma.fields.Nested(schema)},
                        )
                    return None
        """
        return schema

    @staticmethod
    def _prepare_response_content(data):
        """Override this to modify the data structure

        This allows to insert the data in a wrapping structure.

            Example: ::

                @staticmethod
                def _prepare_response_content(data):
                    if data is not None:
                        return {'data': data}
                    return None
        """
        return data

    @staticmethod
    def _prepare_response_doc(doc, doc_info, *, api, spec, **kwargs):
        operation = doc_info.get("response", {})
        # Document default error response
        if api.DEFAULT_ERROR_RESPONSE_NAME:
            operation.setdefault("responses", {})[
                "default"
            ] = api.DEFAULT_ERROR_RESPONSE_NAME
        if operation:
            # OAS 2: set "produces"
            # TODO: The list of content types should contain those used by other
            # decorators (error responses, mainly). In the general case, those
            # responses use DEFAULT_RESPONSE_CONTENT_TYPE which appears in the list
            # if used in response, alt_response or if DEFAULT_ERROR_RESPONSE_NAME
            # is set, so it will only be slightly incomplete in corner cases.
            if spec.openapi_version.major < 3:
                content_types = set()
                for response in operation["responses"].values():
                    if isinstance(response, abc.Mapping):
                        content_type = (
                            response["content_type"]
                            or api.DEFAULT_RESPONSE_CONTENT_TYPE
                        )
                    else:
                        content_type = api.DEFAULT_RESPONSE_CONTENT_TYPE
                    content_types.add(content_type)
                if content_types != {api.DEFAULT_RESPONSE_CONTENT_TYPE}:
                    operation["produces"] = list(content_types)
            # OAS2 / OAS 3: adapt response to OAS version
            for response in operation["responses"].values():
                if isinstance(response, abc.Mapping):
                    content_type = (
                        response.pop("content_type")
                        or api.DEFAULT_RESPONSE_CONTENT_TYPE
                    )
                    prepare_response(response, spec, content_type)
            doc = deepupdate(doc, operation)
        return doc
