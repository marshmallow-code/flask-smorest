"""Pagination feature

Two pagination modes are supported:

- Pagination inside the resource: the resource function is responsible for
  selecting requested range of items and setting total number of items.

- Post-pagination: the resource returns an iterator (typically a DB cursor) and
  a pager is provided to paginate the data and get the total number of items.
"""

from functools import wraps

from flask import request, current_app

import marshmallow as ma

from .args_parser import abort, parser
from .utils import get_appcontext
from .exceptions import PageOutOfRangeError
from .compat import MARSHMALLOW_VERSION_MAJOR


# Global default pagination parameters
# Can be mutated to provide custom defaults
DEFAULT_PAGINATION_PARAMETERS = {
    'page': 1, 'page_size': 10, 'max_page_size': 100}


class PaginationParameters:
    """Holds pagination arguments"""

    def __init__(self, page, page_size):
        self.page = page
        self.page_size = page_size

    @property
    def first_item(self):
        """Return first item number"""
        return (self.page - 1) * self.page_size

    @property
    def last_item(self):
        """Return last item number"""
        return self.first_item + self.page_size - 1

    def __repr__(self):
        return ("{}(page={!r},page_size={!r})"
                .format(self.__class__.__name__, self.page, self.page_size))


def pagination_parameters_schema_factory(
        def_page=None, def_page_size=None, def_max_page_size=None):
    """Generate a PaginationParametersSchema"""
    if def_page is None:
        def_page = DEFAULT_PAGINATION_PARAMETERS['page']
    if def_page_size is None:
        def_page_size = DEFAULT_PAGINATION_PARAMETERS['page_size']
    if def_max_page_size is None:
        def_max_page_size = DEFAULT_PAGINATION_PARAMETERS['max_page_size']

    class PaginationParametersSchema(ma.Schema):
        """Deserializes pagination params into PaginationParameters"""

        class Meta:
            ordered = True
            if MARSHMALLOW_VERSION_MAJOR < 3:
                strict = True

        page = ma.fields.Integer(
            missing=def_page,
            validate=ma.validate.Range(min=1)
        )
        page_size = ma.fields.Integer(
            missing=def_page_size,
            validate=ma.validate.Range(min=1, max=def_max_page_size)
        )

        @ma.post_load
        def make_paginator(self, data):
            return PaginationParameters(**data)

    return PaginationParametersSchema


class PaginationMetadata:

    def __init__(self, page, page_size, item_count):
        self.page = page
        self.page_size = page_size
        self.item_count = item_count

        if self.item_count == 0:
            self.page_count = 0
        else:
            # First / last page, page count
            self.first_page = 1
            self.page_count = ((self.item_count - 1) // self.page_size) + 1
            self.last_page = self.first_page + self.page_count - 1
            # Check if requested page number is out of range
            if (self.page < self.first_page) or (self.page > self.last_page):
                raise PageOutOfRangeError(
                    "Page {} out of [{}-{}] range.".format(
                        self.page, self.first_page, self.last_page)
                )
            # Previous / next page
            if self.page > self.first_page:
                self.previous_page = self.page-1
            if self.page < self.last_page:
                self.next_page = self.page+1

    def __repr__(self):
        return ("{}(page={!r},page_size={!r},item_count={!r})"
                .format(self.__class__.__name__,
                        self.page, self.page_size, self.item_count))


class PaginationMetadataSchema(ma.Schema):
    """Serializes pagination metadata"""

    class Meta:
        ordered = True

    total = ma.fields.Integer(
        attribute='item_count'
    )
    total_pages = ma.fields.Integer(
        attribute='page_count'
    )
    page = ma.fields.Integer()
    first_page = ma.fields.Integer()
    last_page = ma.fields.Integer()
    previous_page = ma.fields.Integer()
    next_page = ma.fields.Integer()


class Page:
    """Pager for simple types such as lists.

    Can be subclassed to provide a pager for a specific data object.
    """
    def __init__(self, collection, page_params):
        """Create a Page instance

        :param sequence collection: Collection of items to page through
        :page PaginationParameters page_params: Pagination parameters
        """
        self.collection = collection
        self.page_params = page_params

    @property
    def items(self):
        return list(self.collection[
            self.page_params.first_item: self.page_params.last_item + 1])

    @property
    def item_count(self):
        return len(self.collection)

    def __repr__(self):
        return ("{}(collection={!r},page_params={!r})"
                .format(self.__class__.__name__,
                        self.collection, self.page_params))


def _get_pagination_ctx():
    """Get pagination section of AppContext"""
    return get_appcontext()['pagination']


def set_item_count(item_count):
    """Set total number of items when paginating

    When paginating in resource, this must be called from resource code
    """
    _get_pagination_ctx()['item_count'] = item_count


def _set_pagination_header(page_params):
    """Get pagination metadata from AppContext and add it to headers

    Abort with 404 status if requested page number is out of range
    """
    try:
        item_count = _get_pagination_ctx()['item_count']
    except KeyError:
        # item_count is not set, this is an issue in the app. Pass and warn.
        current_app.logger.warning(
            'item_count not set in endpoint {}'.format(request.endpoint))
        return
    try:
        pagination_metadata = PaginationMetadata(
            page_params.page, page_params.page_size, item_count)
    except PageOutOfRangeError as exc:
        abort(404, messages=str(exc), exc=exc)
    page_header = PaginationMetadataSchema().dumps(pagination_metadata)
    if MARSHMALLOW_VERSION_MAJOR < 3:
        page_header = page_header[0]
    get_appcontext()['headers']['X-Pagination'] = page_header


def paginate(pager, page_params_schema):
    """Decorator that handles pagination"""

    def decorator(func):

        @wraps(func)
        def wrapper(*args, **kwargs):

            page_params = parser.parse(page_params_schema, request)

            # Pagination in resource code: inject first/last as kwargs
            if pager is None:
                kwargs.update({
                    'first_item': page_params.first_item,
                    'last_item': page_params.last_item,
                })

            # Execute decorated function
            result = func(*args, **kwargs)

            # Post pagination: use pager class to paginate the result
            if pager is not None:
                page = pager(result, page_params=page_params)
                result = page.items
                set_item_count(page.item_count)

            # Add pagination metadata to headers
            _set_pagination_header(page_params)

            return result

        return wrapper

    return decorator
