"""Response processor"""

from functools import wraps

from flask import jsonify, request

from .pagination import (
    PaginationParametersSchema, PaginationDataSchema,
    set_pagination_parameters, get_pagination_data)
from .etag import (
    disable_etag_for_request, check_precondition,
    set_etag_in_response, set_etag_schema)
from .args_parser import parser


def marshal_with(schema=None, code=200, paginate=False,
                 etag_schema=None, disable_etag=False):
    """Decorator that marshals response with schema."""

    # If given Schema class, create instance
    # If paginate, set "many" automatically
    # To return a list without pagination, provide a schema instance
    if isinstance(schema, type):
        schema = schema(many=paginate)
    if isinstance(etag_schema, type):
        etag_schema = etag_schema(many=paginate)

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
            # - Inject parameter first/last in resource function
            # - Store page/page_size in AppContext
            if paginate:
                paginator = parser.parse(PaginationParametersSchema, request)
                kwargs.update({
                    'first_item': paginator.first_item,
                    'last_item': paginator.last_item,
                })
                set_pagination_parameters(paginator.page, paginator.page_size)

            # Execute decorated function
            result_raw = func(*args, **kwargs)

            # Dump with schema if specified
            result_dump = (schema.dump(result_raw)[0] if schema is not None
                           else result_raw)

            # Build response
            response = jsonify(result_dump)

            # Add pagination headers to response
            # TODO: other headers? Total page count, first, last, prev, next?
            extra_data = None
            if paginate:
                pagination_data = get_pagination_data()
                if pagination_data:
                    pagination_data_dump = PaginationDataSchema().dump(
                        pagination_data)[0]
                    response.headers['X-Pagination'] = pagination_data_dump
                    extra_data = pagination_data_dump

            # Add etag value to response
            set_etag_in_response(response, result_raw, etag_schema or schema,
                                 extra_data=extra_data)

            # Add status code
            return response, code

        return wrapper

    return decorator
