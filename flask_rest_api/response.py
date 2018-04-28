"""Response processor"""

from functools import wraps

from flask import jsonify

from .etag import (
    disable_etag_for_request, check_precondition, verify_check_etag,
    set_etag_schema, set_etag_in_response)
from .utils import get_appcontext


def response(schema=None, *, code=200, etag_schema=None, disable_etag=False):
    """Decorator that generates response

    - Dump with provided Schema instance
    - Set ETag

    Blueprint.response ensures schema and etag_schema are Schema instances,
    not classes.
    """
    def decorator(func):

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
            result_dump = (schema.dump(result)[0] if schema is not None
                           else result)

            # Build response
            resp = jsonify(result_dump)
            headers = get_appcontext()['headers']
            resp.headers.extend(headers)

            # Add etag value to response
            # Pass result data to use as ETag data if set_etag was not called
            # If etag_schema is provided, pass raw data rather than dump, as
            # the dump needs to be done using etag_schema
            etag_data = result_dump if etag_schema is None else result
            set_etag_in_response(resp, etag_data, etag_schema)

            # Add status code
            return resp, code

        return wrapper

    return decorator
