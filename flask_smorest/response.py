"""Response processor"""

from copy import deepcopy
from functools import wraps
import http

from werkzeug import Response
from flask import jsonify

from .utils import (
    deepupdate, remove_none, get_appcontext, prepare_response,
    unpack_tuple_response, set_status_and_headers_in_response
)
from .spec import DEFAULT_RESPONSE_CONTENT_TYPE


class ResponseMixin:
    """Extend Blueprint to add response handling"""

    def response(
            self, status_code, schema=None, *, description=None,
            example=None, examples=None, headers=None
    ):
        """Decorator generating an endpoint response

        :param int|str|HTTPStatus status_code: HTTP status code.
            Used if none is returned from the view function.
        :param schema: :class:`Schema <marshmallow.Schema>` class or instance.
            If not None, will be used to serialize response data.
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

        The `example` and `examples` parameters are mutually exclusive. The
        latter should only be used with OpenAPI 3.

        The `example`, `examples` and `headers` parameters are only used to
        document the resource.

        See :doc:`Response <response>`.
        """
        if isinstance(schema, type):
            schema = schema()

        # Document response (schema, description,...) in the API doc
        doc_schema = self._make_doc_response_schema(schema)
        if description is None:
            description = http.HTTPStatus(int(status_code)).phrase
        resp_doc = remove_none({
            "schema": doc_schema,
            "description": description,
            "example": example,
            "examples": examples,
            "headers": headers,
        })

        def decorator(func):

            @wraps(func)
            def wrapper(*args, **kwargs):

                # Execute decorated function
                result_raw, r_status_code, r_headers = unpack_tuple_response(
                    func(*args, **kwargs))

                # If return value is a werkzeug Response, return it
                if isinstance(result_raw, Response):
                    set_status_and_headers_in_response(
                        result_raw, r_status_code, r_headers)
                    return result_raw

                # Dump result with schema if specified
                if schema is None:
                    result_dump = result_raw
                else:
                    result_dump = schema.dump(result_raw)

                # Store result in appcontext (may be used for ETag computation)
                appcontext = get_appcontext()
                appcontext['result_raw'] = result_raw
                appcontext['result_dump'] = result_dump

                # Build response
                resp = jsonify(self._prepare_response_content(result_dump))
                set_status_and_headers_in_response(
                    resp, r_status_code, r_headers
                )
                if r_status_code is None:
                    resp.status_code = status_code

                return resp

            # Store doc in wrapper function
            # The deepcopy avoids modifying the wrapped function doc
            wrapper._apidoc = deepcopy(getattr(wrapper, '_apidoc', {}))
            wrapper._apidoc.setdefault(
                'response', {}
            ).setdefault('responses', {})[status_code] = resp_doc
            # Indicate which code is the success status code
            # Helps other decorators documenting success response
            wrapper._apidoc['success_status_code'] = status_code

            return wrapper

        return decorator

    def alt_response(
            self, status_code, schema_or_ref, *, description=None,
            example=None, examples=None, headers=None
    ):
        """Decorator documenting an alternative response

        :param int|str|HTTPStatus status_code: HTTP status code.
        :param schema_or_ref: Either a :class:`Schema <marshmallow.Schema>`
            class or instance or a string error reference.
            When passing a reference, arguments below are ignored.
        :param str description: Description of the response (default: None).
        :param dict example: Example of response message.
        :param dict examples: Examples of response message.
        :param dict headers: Headers returned by the response.
        """
        # If a ref is passed
        if isinstance(schema_or_ref, str):
            resp_doc = schema_or_ref
        # If a schema is passed
        else:
            schema = schema_or_ref
            if isinstance(schema, type):
                schema = schema()

            # Document response (schema, description,...) in the API doc
            doc_schema = self._make_doc_response_schema(schema)
            if description is None:
                description = http.HTTPStatus(int(status_code)).phrase
            resp_doc = remove_none({
                "schema": doc_schema,
                "description": description,
                "example": example,
                "examples": examples,
                "headers": headers,
            })

        def decorator(func):

            @wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)

            # Store doc in wrapper function
            # The deepcopy avoids modifying the wrapped function doc
            wrapper._apidoc = deepcopy(getattr(wrapper, '_apidoc', {}))
            wrapper._apidoc.setdefault(
                'response', {}
            ).setdefault('responses', {})[status_code] = resp_doc

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
        operation = doc_info.get('response', {})
        # Document default error response
        if api.DEFAULT_ERROR_RESPONSE_NAME:
            operation.setdefault('responses', {})['default'] = (
                api.DEFAULT_ERROR_RESPONSE_NAME)
        if operation:
            for response in operation['responses'].values():
                prepare_response(response, spec, DEFAULT_RESPONSE_CONTENT_TYPE)
            doc = deepupdate(doc, operation)
        return doc
