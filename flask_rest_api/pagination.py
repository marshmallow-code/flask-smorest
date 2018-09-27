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

from .args_parser import parser
from .utils import get_appcontext
from .compat import MARSHMALLOW_VERSION_MAJOR


class PaginationParameters:
    """Holds pagination arguments"""

    def __init__(self, page, page_size):
        self.page = page
        self.page_size = page_size
        self.item_count = None

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


def _pagination_parameters_schema_factory(
        def_page, def_page_size, def_max_page_size):
    """Generate a PaginationParametersSchema"""

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
    """Holds pagination metadata"""

    def __init__(self, page, page_size, item_count):
        self.page_size = page_size
        self.item_count = item_count

        if self.item_count == 0:
            self.page_count = 0
        else:
            # First / last page, page count
            self.first_page = 1
            self.page_count = ((self.item_count - 1) // self.page_size) + 1
            self.last_page = self.first_page + self.page_count - 1
            # Page, previous / next page
            if page <= self.last_page:
                self.page = page
                if page > self.first_page:
                    self.previous_page = page - 1
                if page < self.last_page:
                    self.next_page = page + 1

    def __repr__(self):
        return ("{}(page={!r},page_size={!r},item_count={!r})"
                .format(self.__class__.__name__,
                        self.page, self.page_size, self.item_count))


class PaginationMetadataSchema(ma.Schema):
    """Serializes pagination metadata"""

    class Meta:
        ordered = True

    total = ma.fields.Integer(attribute='item_count')
    total_pages = ma.fields.Integer(attribute='page_count')
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
        self.page_params.item_count = self.item_count

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


class PaginationMixin:
    """Extend Blueprint to add Pagination feature"""

    PAGINATION_HEADER_FIELD_NAME = 'X-Pagination'

    # Global default pagination parameters
    # Can be overridden to provide custom defaults
    DEFAULT_PAGINATION_PARAMETERS = {
        'page': 1, 'page_size': 10, 'max_page_size': 100}

    def paginate(self, pager=None, *,
                 page=None, page_size=None, max_page_size=None):
        """Decorator adding pagination to the endpoint

        :param Page pager: Page class used to paginate response data
        :param int page: Default requested page number (default: 1)
        :param int page_size: Default requested page size (default: 10)
        :param int max_page_size: Maximum page size (default: 100)

        If a pager class is provided, it is used to paginate the data returned
        by the view function, typically a lazy database cursor.

        If no pager class is provided, pagination is handled in the view
        function. The view function is passed a
        :class:`pagination.PaginationParameters` <PaginationParameters>
        instance as `pagination_parameters` keyword parameter.
        This object provides pagination parameters as both `page`/`page_size`
        and `first_item`/`last_item`. The view function is responsible for
        storing the total number of items as `item_count` attribute of passed
        `PaginationParameters` instance.
        """
        if page is None:
            page = self.DEFAULT_PAGINATION_PARAMETERS['page']
        if page_size is None:
            page_size = self.DEFAULT_PAGINATION_PARAMETERS['page_size']
        if max_page_size is None:
            max_page_size = self.DEFAULT_PAGINATION_PARAMETERS['max_page_size']
        page_params_schema = _pagination_parameters_schema_factory(
            page, page_size, max_page_size)

        parameters = {
            'in': 'query',
            'schema': page_params_schema,
        }

        def decorator(func):
            # Add pagination params to doc info in function object
            func._apidoc = getattr(func, '_apidoc', {})
            func._apidoc.setdefault('parameters', []).append(parameters)

            @wraps(func)
            def wrapper(*args, **kwargs):

                page_params = parser.parse(page_params_schema, request)

                # Pagination in resource code: inject page_params as kwargs
                if pager is None:
                    kwargs['pagination_parameters'] = page_params

                # Execute decorated function
                result = func(*args, **kwargs)

                # Post pagination: use pager class to paginate the result
                if pager is not None:
                    result = pager(result, page_params=page_params).items

                # Get item_count
                item_count = page_params.item_count
                if item_count is None:
                    current_app.logger.warning(
                        'item_count not set in endpoint {}'
                        .format(request.endpoint))
                else:
                    # Add pagination metadata to headers
                    pagination_metadata = PaginationMetadata(
                        page_params.page, page_params.page_size, item_count)
                    page_header = self._make_pagination_header(
                        pagination_metadata)
                    get_appcontext()['headers'][
                        self.PAGINATION_HEADER_FIELD_NAME] = (page_header)

                return result

            return wrapper

        return decorator

    @staticmethod
    def _make_pagination_header(pagination_metadata):
        """Build pagination header from page, page size and item count"""
        page_header = PaginationMetadataSchema().dumps(pagination_metadata)
        if MARSHMALLOW_VERSION_MAJOR < 3:
            page_header = page_header[0]
        return page_header
