"""Response processor"""

from functools import wraps

from flask import jsonify

from .etag import (
    disable_etag_for_request, check_precondition, verify_check_etag,
    set_etag_schema, set_etag_in_response)
from .utils import deepupdate, get_appcontext
from .compat import MARSHMALLOW_VERSION_MAJOR


class ResponseMixin:
    """Extend Blueprint to add response handling"""

    def response(self, schema=None, *, code=200, description='',
                 etag_schema=None, disable_etag=False):
        """Decorator generating an endpoint response

        :param schema: :class:`Schema <marshmallow.Schema>` class or instance.
            If not None, will be used to serialize response data.
        :param int code: HTTP status code (default: 200).
        :param str descripton: Description of the response.
        :param etag_schema: :class:`Schema <marshmallow.Schema>` class
            or instance. If not None, will be used to serialize etag data.
        :param bool disable_etag: Disable ETag feature locally even if enabled
            globally.

        See :doc:`Response <response>`.
        """
        if isinstance(schema, type):
            schema = schema()
        if isinstance(etag_schema, type):
            etag_schema = etag_schema()

        def decorator(func):

            # Add schema as response in the API doc
            doc = {'responses': {code: {'description': description}}}
            doc_schema = self._make_doc_response_schema(schema)
            if doc_schema:
                doc['responses'][code]['schema'] = doc_schema
            func._apidoc = deepupdate(getattr(func, '_apidoc', {}), doc)

            @wraps(func)
            def wrapper(*args, **kwargs):

                if disable_etag:
                    disable_etag_for_request()

                # Check etag precondition
                check_precondition()

                # Store etag_schema in AppContext
                set_etag_schema(etag_schema)

                # Execute decorated function
                result = func(*args, **kwargs)

                # Verify that check_etag was called in resource code if needed
                verify_check_etag()

                # Dump result with schema if specified
                if schema is None:
                    result_dump = result
                else:
                    result_dump = schema.dump(result)
                    if MARSHMALLOW_VERSION_MAJOR < 3:
                        result_dump = result_dump[0]

                # Build response
                resp = jsonify(self._prepare_response_content(result_dump))
                resp.headers.extend(get_appcontext()['headers'])

                # Add etag value to response
                # Pass data to use as ETag data if set_etag was not called
                # If etag_schema is provided, pass raw data rather than dump,
                # as the dump needs to be done using etag_schema
                etag_data = result_dump if etag_schema is None else result
                set_etag_in_response(resp, etag_data, etag_schema)

                # Add status code
                return resp, code

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
