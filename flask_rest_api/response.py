"""Response processor"""

from functools import wraps

from werkzeug import BaseResponse
from flask import jsonify

from .utils import (
    deepupdate, get_appcontext,
    unpack_tuple_response, set_status_and_headers_in_response
)
from .compat import MARSHMALLOW_VERSION_MAJOR


class ResponseMixin:
    """Extend Blueprint to add response handling"""

    def response(self, schema=None, *, code=200, description=''):
        """Decorator generating an endpoint response

        :param schema: :class:`Schema <marshmallow.Schema>` class or instance.
            If not None, will be used to serialize response data.
        :param int code: HTTP status code (default: 200). Used if none is
            returned from the view function.
        :param str descripton: Description of the response.

        The decorated function is expected to return the same types of value
        than a typical flask view function, except the body part may be an
        object or a list of objects to serialize with the schema, rather than
        a ``string``.

        If the decorated function returns a ``Response`` object, the ``schema``
        and ``code`` parameters are only used to document the resource.

        See :doc:`Response <response>`.
        """
        if isinstance(schema, type):
            schema = schema()

        def decorator(func):

            # Add schema as response in the API doc
            doc = {'responses': {str(code): {'description': description}}}
            doc_schema = self._make_doc_response_schema(schema)
            if doc_schema:
                doc['responses'][str(code)]['schema'] = doc_schema
            func._apidoc = deepupdate(getattr(func, '_apidoc', {}), doc)

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
                        result_dump = result_dump[0]

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
