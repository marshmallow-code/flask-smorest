"""Response processor"""

from collections import abc
from copy import deepcopy
from functools import wraps
import http

from werkzeug.wrappers import BaseResponse
from flask import jsonify

from .utils import (
    deepupdate, get_appcontext, prepare_response,
    unpack_tuple_response, set_status_and_headers_in_response
)
from .compat import MARSHMALLOW_VERSION_MAJOR
from .spec import DEFAULT_RESPONSE_CONTENT_TYPE


class ResponseMixin:
    """Extend Blueprint to add response handling"""

    def response(
            self, schema=None, *, code=200, description=None,
            example=None, examples=None, headers=None
    ):
        """Decorator generating an endpoint response

        :param schema: :class:`Schema <marshmallow.Schema>` class or instance.
            If not None, will be used to serialize response data.
        :param int|str|HTTPStatus code: HTTP status code (default: 200).
            Used if none is returned from the view function.
        :param str description: Description of the response (default: None).
        :param dict example: Example of response message.
        :param list examples: Examples of response message.
        :param dict headers: Headers returned by the response.

        The decorated function is expected to return the same types of value
        than a typical flask view function, except the body part may be an
        object or a list of objects to serialize with the schema, rather than
        a ``string``.

        If the decorated function returns a ``Response`` object, the ``schema``
        and ``code`` parameters are only used to document the resource.

        The `example` and `examples` parameters are mutually exclusive. The
        latter should only be used with OpenAPI 3.

        The `example`, `examples` and `headers` parameters are only used to
        document the resource.

        See :doc:`Response <response>`.
        """
        if isinstance(schema, type):
            schema = schema()

        # Document response (schema, description,...) in the API doc
        resp_doc = {}
        doc_schema = self._make_doc_response_schema(schema)
        if doc_schema is not None:
            resp_doc['schema'] = doc_schema
        if description is not None:
            resp_doc['description'] = description
        else:
            resp_doc['description'] = http.HTTPStatus(int(code)).name
        if example is not None:
            resp_doc['example'] = example
        if examples is not None:
            resp_doc['examples'] = examples
        if headers is not None:
            resp_doc['headers'] = headers
        doc = {'responses': {code: resp_doc}}

        def decorator(func):

            @wraps(func)
            def wrapper(*args, **kwargs):

                # Execute decorated function
                result_raw, status, headers = unpack_tuple_response(
                    func(*args, **kwargs))

                # If return value is a werkzeug BaseResponse, return it
                if isinstance(result_raw, BaseResponse):
                    set_status_and_headers_in_response(
                        result_raw, status, headers)
                    return result_raw

                # Dump result with schema if specified
                if schema is None:
                    result_dump = result_raw
                else:
                    result_dump = schema.dump(result_raw)
                    if MARSHMALLOW_VERSION_MAJOR < 3:
                        result_dump = result_dump.data

                # Store result in appcontext (may be used for ETag computation)
                appcontext = get_appcontext()
                appcontext['result_raw'] = result_raw
                appcontext['result_dump'] = result_dump

                # Build response
                resp = jsonify(self._prepare_response_content(result_dump))
                set_status_and_headers_in_response(resp, status, headers)
                if status is None:
                    resp.status_code = code

                return resp

            # Document pagination header if needed
            if getattr(func, '_paginated', False) is True:
                doc['responses'][code]['headers'] = {
                    self.PAGINATION_HEADER_FIELD_NAME: (
                        self.PAGINATION_HEADER_DOC
                    )
                }

            # Document default error response
            doc['responses']['default'] = 'DEFAULT_ERROR'

            # Store doc in wrapper function
            # The deepcopy avoids modifying the wrapped function doc
            wrapper._apidoc = deepcopy(getattr(wrapper, '_apidoc', {}))
            wrapper._apidoc['response'] = doc

            return wrapper

        return decorator

    @staticmethod
    def _make_doc_response_schema(schema):
        """Override this to modify schema in docs

        This can be used to document a wrapping structure.

            Example: ::

                @staticmethod
                def _doc_schema(schema):
                    if schema:
                        return {'type': 'success', 'data': schema}
                    else:
                        return None
        """
        return schema

    @staticmethod
    def _prepare_response_content(data):
        """Override this to modify the data structure

        This allows to insert the data in a wrapping structure.

            Example: ::

                @staticmethod
                def _prepare_response_content:
                    return {'type': 'success', 'data': schema}
        """
        return data

    @staticmethod
    def _prepare_response_doc(doc, doc_info, spec, **kwargs):
        operation = doc_info.get('response', {})

        responses = {
            c: r for c, r in operation.get('responses', {}).items()
            if isinstance(r, abc.Mapping)
        }

        for resp in responses.values():
            prepare_response(resp, spec, DEFAULT_RESPONSE_CONTENT_TYPE)

        doc = deepupdate(doc, operation)
        return doc
