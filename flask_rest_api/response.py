"""Response processor"""

from functools import wraps

from flask import jsonify

from .pagination import (
    get_pagination_parameters_from_request, set_item_count,
    get_pagination_metadata, set_pagination_metadata_in_response)
from .etag import (
    disable_etag_for_request, check_precondition, verify_check_etag,
    set_etag_schema, set_etag_in_response)
from .exceptions import MultiplePaginationModes


def response(schema=None, *, code=200, paginate=False, paginate_with=None,
             etag_schema=None, disable_etag=False):
    """Decorator that generates response

    - Dump with provided Schema
    - Set ETag
    - Set pagination
    """

    if paginate and paginate_with is not None:
        raise MultiplePaginationModes(
            "paginate_with and paginate are mutually exclusive.")

    # If given Schema class, create instance
    # If resource is paginated, set "many" automatically
    # For a list without pagination, provide a schema instance with many=True:
    #     response(schema=MySchema(any=True),...)
    if isinstance(schema, type):
        schema = schema(many=(paginate or paginate_with is not None))
    if isinstance(etag_schema, type):
        etag_schema = etag_schema(many=(paginate or paginate_with is not None))

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

            # Dump result with schema if specified
            result_dump = (schema.dump(result)[0] if schema is not None
                           else result)

            # Build response
            response = jsonify(result_dump)

            # Add pagination metadata to response
            if paginate or (paginate_with is not None):
                pagination_metadata = get_pagination_metadata()
                set_pagination_metadata_in_response(
                    response, pagination_metadata)
            else:
                pagination_metadata = None

            # Add etag value to response
            # Pass result data to use as ETag data if set_etag was not called
            # If etag_schema is provided, pass raw data rather than dump, as
            # the dump needs to be done using etag_schema
            if etag_schema is not None:
                set_etag_in_response(response, result, etag_schema,
                                     extra_data=pagination_metadata)
            else:
                set_etag_in_response(response, result_dump,
                                     extra_data=pagination_metadata)

            # Add status code
            return response, code

        return wrapper

    return decorator
