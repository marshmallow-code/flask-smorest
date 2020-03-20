"""Pagination feature

Two pagination modes are supported:

- Pagination inside the resource: the resource function is responsible for
  selecting requested range of items and setting total number of items.

- Post-pagination: the resource returns an iterator (typically a DB cursor) and
  a pager is provided to paginate the data and get the total number of items.
"""

from copy import deepcopy
from collections import OrderedDict
from functools import wraps
import http

from flask import request, current_app

import marshmallow as ma
from webargs.flaskparser import FlaskParser

from .utils import unpack_tuple_response
from .compat import MARSHMALLOW_VERSION_MAJOR


class PaginationParameters:
    """Holds pagination arguments

    :param int page: Page number
    :param int page_size: Page size
    """
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
        def make_paginator(self, data, **kwargs):
            return PaginationParameters(**data)

    return PaginationParametersSchema


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


class PaginationHeaderSchema(ma.Schema):
    """Pagination header schema

    Used to serialize pagination header.
    Its main purpose is to document the pagination header.
    """
    total = ma.fields.Int()
    total_pages = ma.fields.Int()
    first_page = ma.fields.Int()
    last_page = ma.fields.Int()
    page = ma.fields.Int()
    previous_page = ma.fields.Int()
    next_page = ma.fields.Int()

    class Meta:
        ordered = True


class PaginationMixin:
    """Extend Blueprint to add Pagination feature"""

    PAGINATION_ARGUMENTS_PARSER = FlaskParser()

    # Name of field to use for pagination metadata response header
    # Can be overridden. If None, no pagination header is returned.
    PAGINATION_HEADER_FIELD_NAME = 'X-Pagination'

    # Global default pagination parameters
    # Can be overridden to provide custom defaults
    DEFAULT_PAGINATION_PARAMETERS = {
        'page': 1, 'page_size': 10, 'max_page_size': 100}

    PAGINATION_HEADER_DOC = {
        'description': 'Pagination metadata',
        'schema': PaginationHeaderSchema,
    }

    def paginate(self, pager=None, *,
                 page=None, page_size=None, max_page_size=None):
        """Decorator adding pagination to the endpoint

        :param Page pager: Page class used to paginate response data
        :param int page: Default requested page number (default: 1)
        :param int page_size: Default requested page size (default: 10)
        :param int max_page_size: Maximum page size (default: 100)

        If a :class:`Page <Page>` class is provided, it is used to paginate the
        data returned by the view function, typically a lazy database cursor.

        Otherwise, pagination is handled in the view function.

        The decorated function may return a tuple including status and/or
        headers, like a typical flask view function. It may not return a
        ``Response`` object.

        See :doc:`Pagination <pagination>`.
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

        error_status_code = (
            self.PAGINATION_ARGUMENTS_PARSER.DEFAULT_VALIDATION_STATUS
        )

        def decorator(func):

            @wraps(func)
            def wrapper(*args, **kwargs):

                page_params = self.PAGINATION_ARGUMENTS_PARSER.parse(
                    page_params_schema, request, locations=['query'])

                # Pagination in resource code: inject page_params as kwargs
                if pager is None:
                    kwargs['pagination_parameters'] = page_params

                # Execute decorated function
                result, status, headers = unpack_tuple_response(
                    func(*args, **kwargs))

                # Post pagination: use pager class to paginate the result
                if pager is not None:
                    result = pager(result, page_params=page_params).items

                # Add pagination metadata to headers
                if self.PAGINATION_HEADER_FIELD_NAME is not None:
                    if page_params.item_count is None:
                        current_app.logger.warning(
                            'item_count not set in endpoint {}'
                            .format(request.endpoint))
                    else:
                        page_header = self._make_pagination_header(
                            page_params.page, page_params.page_size,
                            page_params.item_count)
                        if headers is None:
                            headers = {}
                        headers[
                            self.PAGINATION_HEADER_FIELD_NAME] = page_header

                return result, status, headers

            # Add pagination params to doc info in wrapper object
            wrapper._apidoc = deepcopy(getattr(wrapper, '_apidoc', {}))
            wrapper._apidoc['pagination'] = {
                'parameters': parameters,
                'response': {
                    error_status_code:
                    http.HTTPStatus(error_status_code).name,
                }
            }
            wrapper._paginated = True

            return wrapper

        return decorator

    @staticmethod
    def _make_pagination_header(page, page_size, item_count):
        """Build pagination header from page, page size and item count

        This method returns a json representation of a default pagination
        metadata structure. It can be overridden to use another structure.
        """
        page_header = OrderedDict()
        page_header['total'] = item_count
        if item_count == 0:
            page_header['total_pages'] = 0
        else:
            # First / last page, page count
            page_count = ((item_count - 1) // page_size) + 1
            first_page = 1
            last_page = page_count
            page_header['total_pages'] = page_count
            page_header['first_page'] = first_page
            page_header['last_page'] = last_page
            # Page, previous / next page
            if page <= last_page:
                page_header['page'] = page
                if page > first_page:
                    page_header['previous_page'] = page - 1
                if page < last_page:
                    page_header['next_page'] = page + 1
        header = PaginationHeaderSchema().dumps(page_header)
        if MARSHMALLOW_VERSION_MAJOR < 3:
            header = header.data
        return header

    @staticmethod
    def _prepare_pagination_doc(doc, doc_info, **kwargs):
        operation = doc_info.get('pagination')
        if operation:
            parameters = operation.get('parameters')
            doc.setdefault('parameters', []).append(parameters)
            response = operation.get('response')
            doc.setdefault('responses', {}).update(response)
        return doc
