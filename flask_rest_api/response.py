"""Response processor"""

from functools import wraps

from flask import jsonify

from .pagination import (
    get_pagination_parameters_from_request, set_item_count,
    set_pagination_header)
from .etag import (
    disable_etag_for_request, check_precondition, verify_check_etag,
    set_etag_schema, set_etag_in_response)
from .utils import get_appcontext


def response(schema=None, *, code=200, paginate=False, paginate_with=None,
             etag_schema=None, disable_etag=False):
    """Decorator that generates response

    - Dump with provided Schema instance
    - Set ETag
    - Set pagination

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

            # Pagination parameters:
            # - Store page/page_size in AppContext
            # - If paginating in resource code, inject first/last as kwargs
            if paginate or (paginate_with is not None):
                page_params = get_pagination_parameters_from_request()
                if paginate:
                    kwargs.update({
                        'first_item': page_params.first_item,
                        'last_item': page_params.last_item,
                    })

            # Execute decorated function
            result = func(*args, **kwargs)

            # Verify that check_etag was called in resource code if needed
            verify_check_etag()

            # Post pagination
            if paginate_with is not None:
                page = paginate_with(result, page_params=page_params)
                result = page.items
                set_item_count(page.item_count)

            # Add pagination metadata to headers
            if paginate or (paginate_with is not None):
                set_pagination_header()

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
            pagination_header = headers.get('X-Pagination', {})
            if etag_schema is not None:
                set_etag_in_response(resp, result, etag_schema,
                                     extra_data=pagination_header)
            else:
                set_etag_in_response(resp, result_dump,
                                     extra_data=pagination_header)

            # Add status code
            return resp, code

        return wrapper

    return decorator
