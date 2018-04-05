"""Pagination feature

Two pagination modes are supported:

- Pagination inside the resource: the resource function is responsible for
  selecting requested range of items and setting total number of items.

- Post-pagination: the resource returns an iterator (typically a DB cursor) and
  a pager is provided to paginate the data and get the total number of items.
"""

from flask import request

import marshmallow as ma

from .args_parser import abort, parser
from .utils import get_appcontext
from .exceptions import PageOutOfRangeError


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


class PaginationParametersSchema(ma.Schema):
    """Deserializes pagination parameters into a PaginationParameters object"""

    class Meta:
        strict = True
        ordered = True

    page = ma.fields.Integer(
        missing=1,
        validate=ma.validate.Range(min=1)
    )
    page_size = ma.fields.Integer(
        # TODO: don't hardcode default and max page_size values?
        missing=10,
        validate=ma.validate.Range(min=1, max=100)
    )

    @ma.post_load
    def make_paginator(self, data):
        return PaginationParameters(**data)


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
    first_page = ma.fields.Integer()
    last_page = ma.fields.Integer()
    previous_page = ma.fields.Integer()
    next_page = ma.fields.Integer()


# Inspired from Pylons/paginate: https://github.com/Pylons/paginate
class Page:
    """Pager for simple types such as lists.

    Can be subclassed to provide a pager for a specific data object.

    Example pager for Pymongo cursor:

    class PymongoCursorWrapper():
        def __init__(self, obj):
            self.obj = obj
        def __getitem__(self, range):
            return self.obj[range]
        def __len__(self):
            return self.obj.count()

    class PymongoCursorPage(Page):
        _wrapper_class = PymongoCursorWrapper
    """

    _wrapper_class = None

    def __init__(self, collection, page_params):
        """Create a Page instance

        :param sequence collection: Collection of items to page through
        :page PaginationParameters page_params: Pagination parameters
        """
        if self._wrapper_class is not None:
            # Custom wrapper class used to access collection elements
            collection = self._wrapper_class(collection)
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
    return get_appcontext().setdefault('pagination', {})


def get_pagination_parameters_from_request():
    """Parse pagination parameters in request object

    Store pagination data in AppContext and return it

    Called automatically
    """
    page_params = parser.parse(PaginationParametersSchema, request)
    _get_pagination_ctx()['parameters'] = page_params
    return page_params


def set_item_count(item_count):
    """Set total number of items when paginating

    When paginating in resource, this should be called from resource code
    """
    _get_pagination_ctx()['item_count'] = item_count


def get_pagination_metadata():
    """Get pagination metadata from AppContext

    Called automatically

    Abort with 404 status if requested page number is out of range
    """
    pagination_ctx = _get_pagination_ctx()
    item_count = pagination_ctx['item_count']
    if item_count is None:
        return None
    page_params = pagination_ctx['parameters']
    try:
        pagination_metadata = PaginationMetadata(
            page_params.page, page_params.page_size, item_count)
    except PageOutOfRangeError as exc:
        abort(404, messages=str(exc), exc=exc)
    return PaginationMetadataSchema().dumps(pagination_metadata)[0]


def set_pagination_metadata_in_response(response, pagination_metadata):
    """Set pagination metadata in response object

    Called automatically
    """
    response.headers['X-Pagination'] = pagination_metadata
