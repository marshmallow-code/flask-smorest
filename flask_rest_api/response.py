"""Response processor"""

from functools import wraps

from flask import jsonify

from .utils import deepupdate, get_appcontext
from .compat import MARSHMALLOW_VERSION_MAJOR


class ResponseMixin:
    """Extend Blueprint to add response handling"""

    def response(self, schema=None, *, code=200, description=''):
        """Decorator generating an endpoint response

        :param schema: :class:`Schema <marshmallow.Schema>` class or instance.
            If not None, will be used to serialize response data.
        :param int code: HTTP status code (default: 200).
        :param str descripton: Description of the response.

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
                result_raw = func(*args, **kwargs)

                # Dump result with schema if specified
                if schema is None:
                    result_dump = result_raw
                else:
                    result_dump = schema.dump(result_raw)
                    if MARSHMALLOW_VERSION_MAJOR < 3:
                        result_dump = result_dump[0]

                # Store result in appcontext (may be used for ETag computation)
                get_appcontext()['result_raw'] = result_raw
                get_appcontext()['result_dump'] = result_dump

                # Build response
                resp = jsonify(self._prepare_response_content(result_dump))
                resp.headers.extend(get_appcontext()['headers'])
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
