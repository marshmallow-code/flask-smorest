"""Response processor"""

from functools import wraps

from flask import jsonify, request

from .pagination import (
    PaginationData, PaginationParametersSchema, PaginationDataSchema,
    set_pagination_parameters, get_pagination_data)
from .etag import (
    disable_etag_for_request, check_precondition,
    set_etag_in_response, set_etag_schema)
from .args_parser import parser
from .exceptions import MultiplePaginationModes


def marshal_with(schema=None, code=200, paginate=False, paginate_with=None,
                 etag_schema=None, disable_etag=False):
    """Decorator that marshals response with schema."""

    if paginate and paginate_with is not None:
        raise MultiplePaginationModes(
            "paginate_with and paginate are mutually exclusive.")

    # If given Schema class, create instance
    # If resource is paginated, set "many" automatically
    # For a list without pagination, provide a schema instance with many=True:
    #     marshal_with(schema=MySchema(any=True),...)
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

            # Post pagination
            if paginate_with is not None:
                paginator = parser.parse(PaginationParametersSchema, request)
                page = paginate_with(result_raw, page=paginator.page,
                                     items_per_page=paginator.page_size)
                result_raw = page.items

            # Dump with schema if specified
            result_dump = (schema.dump(result_raw)[0] if schema is not None
                           else result_raw)

            # Build response
            response = jsonify(result_dump)

            # Add pagination headers to response
            # TODO: other headers? Total page count, first, last, prev, next?
            extra_data = None
            pagination_data = None
            if paginate:
                pagination_data = get_pagination_data()
            elif paginate_with is not None:
                pagination_data = PaginationData(
                    page.page, page.items_per_page, page.item_count)
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
