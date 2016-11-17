# -*- coding: utf-8 -*-

from functools import wraps

from flask import jsonify, request, Response, current_app
from marshmallow import Schema, fields, validate
from webargs.flaskparser import parser, abort

from .etag import generate_etag, is_etag_enabled


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


def marshal_with(schema=None, code=200, payload='data', paginate_with=None):
    """Decorator that marshals response with schema."""

    # TODO: provide Page class registration rather than letting
    # the user specify a Page class for each call to marshall_with?

    # If given Schema class, create instance
    # TODO: test/check if given Schema instance with many=True / False
    if isinstance(schema, Schema.__class__):
        schema = schema(many=(paginate_with is not None))

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

            # Execute decorated function
            result = func(*args, **kwargs)

            # Do we paginate result ?
            if paginate_with is not None:
                page_args = parser.parse(PaginationParameters, request)
                page = paginate_with(result, **page_args)
                # Dump with schema if specified
                data = _dump_data(schema, page.items)
            else:
                # Dump with schema if specified
                data = _dump_data(schema, result)

            response = {
                (payload or 'data'): data
            }

            # Get page meta data
            if paginate_with is not None:
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
