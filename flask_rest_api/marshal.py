"""Response processor"""

from functools import wraps

from flask import jsonify, request
import marshmallow as ma

from .etag import validate_etag, process_etag
from .exceptions import MultiplePaginationModes
from .args_parser import parser


class PaginationParameters(ma.Schema):
    # pylint: disable=too-few-public-methods
    """Handle pagination parameters: page number and page size."""

    class Meta:
        """Pagination parameters schema Meta properties"""
        strict = True

    page = ma.fields.Integer(
        missing=1,
        validate=ma.validate.Range(min=1)
    )
    page_size = ma.fields.Integer(
        attribute='items_per_page',
        missing=10,
        validate=ma.validate.Range(min=1, max=100)
    )



class Paginator():
    """Paginator class"""

    def __init__(self, page, items_per_page):
        self.page = page
        self.items_per_page = items_per_page
        self.item_count = 0
        self.items = []

    @property
    def first(self):
        """Return first page number"""
        return (self.page - 1) * self.items_per_page

    @property
    def last(self):    # More like last + 1, actually
        """Return last page number"""
        return self.first + self.items_per_page

    @property
    def page_count(self):
        """Return total page count"""
        if self.item_count > 0:
            return (self.item_count - 1) // self.items_per_page + 1
        else:
            return 0

    def __repr__(self):
        return ("Paginator:\n"
                "Current page:           {0.page}\n"
                "Items per page:         {0.items_per_page}\n"
                "Total number of items:  {0.item_count}\n"
                "Number of pages:        {0.page_count}"
               ).format(self)


def marshal_with(schema=None, code=200, payload_key='data',
                 paginate_with=None, paginate=False,
                 etag_schema=None, etag_validate=True, etag_item_func=None):
    """Decorator that marshals response with schema."""

    if paginate and paginate_with:
        raise MultiplePaginationModes(
            "paginate_with and paginate are mutually exclusive.")

    # TODO: provide Page class registration rather than letting
    # the user specify a Page class for each call to marshall_with?

    # If given Schema class, create instance
    # TODO: test/check if given Schema instance with many=True / False
    if isinstance(schema, ma.Schema.__class__):
        schema = schema(many=(paginate_with is not None or paginate))

    if isinstance(etag_schema, ma.Schema.__class__):
        etag_schema = etag_schema(many=(paginate_with is not None or paginate))
    else:
        # when not defined, default etag_schema must be schema
        etag_schema = schema

    def decorator(func):

        # XXX: why @wraps?
        @wraps(func)
        def wrapper(*args, **kwargs):

            # Check etag conditions
            if etag_validate:
                # try to take in account both MethodView or functions endpoints
                endpoint = args[0] if len(args) > 0 else func
                validate_etag(
                    endpoint=endpoint, schema=etag_schema,
                    get_item_func=etag_item_func, **kwargs)

            # Create Paginator if needed
            if paginate:
                page_args = parser.parse(PaginationParameters, request)
                kwargs['paginator'] = Paginator(**page_args)

            # Execute decorated function
            result = func(*args, **kwargs)

            # Post pagination
            if paginate_with is not None:
                page_args = parser.parse(PaginationParameters, request)
                page = paginate_with(result, **page_args)
                result = list(page.items)
            # Pagination inside resource function
            elif paginate:
                page = result
                result = list(page.items)

            # Dump with schema if specified
            data = schema.dump(result)[0] if schema is not None else None

            response_content = {
                (payload_key or 'data'): data
            }

            # Get page meta data
            if paginate_with is not None or paginate:
                response_content['meta'] = _get_pagination_meta(page)

            # Build response
            if request.method == 'DELETE':
                response_content = None
            resp = jsonify(response_content)
            # add etag value to response
            process_etag(resp, etag_schema, result, validate=etag_validate)

            # Add status code
            return resp, code

        return wrapper

    return decorator


def _get_pagination_meta(page):
    """Get pagination metadata from "paginate"-ish Paginator

    `page` should behave like paginate's Page object
    """
    return {
        'page': page.page,
        'page_size': page.items_per_page,
        'page_count': page.page_count,
        'item_count': page.item_count,
    }
