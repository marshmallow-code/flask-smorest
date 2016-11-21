# -*- coding: utf-8 -*-

from functools import wraps

from flask import jsonify, request, Response, current_app
from marshmallow import Schema, fields, validate
from webargs.flaskparser import parser, abort

from .etag import generate_etag, is_etag_enabled
from .exceptions import MultiplePaginationModes


class PaginationParameters(Schema):
    """
    Handle pagination parameters: page number and page size.
    """

    page = fields.Int(
        missing=1,
        validate=validate.Range(min=1)
    )
    page_size = fields.Int(
        attribute='items_per_page',
        missing=10,
        validate=validate.Range(min=1, max=100)
    )

    class Meta:
        strict = True


class Paginator():

    def __init__(self, page, items_per_page):
        self.page = page
        self.items_per_page = items_per_page
        self.item_count = 0
        self.items = []

    @property
    def first(self):
        return (self.page - 1) * self.items_per_page

    @property
    def last(self):    # More like last + 1, actually
        return self.first + self.items_per_page

    @property
    def page_count(self):
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


def marshal_with(schema=None, code=200, payload='data',
                 paginate_with=None, paginate=False):
    """Decorator that marshals response with schema."""

    if paginate and paginate_with:
        raise MultiplePaginationModes(
            "paginate_with and paginate are mutually exclusive.")

    # TODO: provide Page class registration rather than letting
    # the user specify a Page class for each call to marshall_with?

    # If given Schema class, create instance
    # TODO: test/check if given Schema instance with many=True / False
    if isinstance(schema, Schema.__class__):
        schema = schema(many=(paginate_with is not None or paginate))

    def decorator(func):

        # XXX: why @wraps?
        @wraps(func)
        def wrapper(*args, **kwargs):

            # Check @conditional PUT, DELETE and PATCH requests
            if (is_etag_enabled(current_app)
                    and request.method in ['PUT', 'DELETE', 'PATCH']):
                func_getter = getattr(args[0], '_getter', None)
                if func_getter is not None:
                    item = func_getter(**kwargs)
                    # Dump with schema if specified
                    data_item = _dump_data(schema, item)
                    resp = Response(status=202)
                    resp.set_etag(generate_etag(data_item))
                else:
                    # TODO: translate error message
                    msg = 'No _getter in [{}] MethodView !'.format(args[0])
                    abort(501, messages=msg)

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
                result = page.items
            # Pagination inside resource function
            elif paginate:
                page = result
                result = page.items

            # Dump with schema if specified
            data = _dump_data(schema, result)

            response = {
                (payload or 'data'): data
            }

            # Get page meta data
            if paginate_with is not None or paginate:
                response['meta'] = _get_pagination_meta(page)

            # Build response
            if request.method == 'DELETE':
                response = None
            resp = jsonify(response)
            if is_etag_enabled(current_app) and request.method != 'DELETE':
                resp.set_etag(generate_etag(data))

            # Add status code
            return resp, code

        return wrapper

    return decorator


def _dump_data(schema=None, data=None):
    if schema is not None:
        return schema.dump(data)[0]
    return None


def _get_pagination_meta(page):
    """Get pagination metadata from "flask-mongoengine"-ish Paginator"""

    meta = {
        'page': page.page,
        'page_size': page.items_per_page,
        'page_count': page.page_count,
        'item_count': page.item_count,
    }

    return meta
