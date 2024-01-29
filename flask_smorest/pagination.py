"""Pagination feature

Two pagination modes are supported:

- Pagination inside the resource: the resource function is responsible for
  selecting requested range of items and setting total number of items.

- Post-pagination: the resource returns an iterator (typically a DB cursor) and
  a pager is provided to paginate the data and get the total number of items.
"""

from copy import deepcopy
from functools import wraps
import http
import json
import warnings

from flask import request

import marshmallow as ma
from webargs.flaskparser import FlaskParser

from .utils import unpack_tuple_response


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
        return (
            f"{self.__class__.__name__}"
            f"(page={self.page!r},page_size={self.page_size!r})"
        )


def _pagination_parameters_schema_factory(def_page, def_page_size, def_max_page_size):
    """Generate a PaginationParametersSchema"""

    class PaginationParametersSchema(ma.Schema):
        """Deserializes pagination params into PaginationParameters"""

        class Meta:
            ordered = True
            unknown = ma.EXCLUDE

        page = ma.fields.Integer(
            load_default=def_page, validate=ma.validate.Range(min=1)
        )
        page_size = ma.fields.Integer(
            load_default=def_page_size,
            validate=ma.validate.Range(min=1, max=def_max_page_size),
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
        return list(
            self.collection[
                self.page_params.first_item : self.page_params.last_item + 1
            ]
        )

    @property
    def item_count(self):
        return len(self.collection)

    def __repr__(self):
        return (
            f"{self.__class__.__name__}"
            f"(collection={self.collection!r},page_params={self.page_params!r})"
        )


class PaginationMetadataSchema(ma.Schema):
    """Pagination metadata schema

    Used to serialize pagination metadata.
    Its main purpose is to document the pagination metadata.
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


PAGINATION_HEADER = {
    "description": "Pagination metadata",
    "schema": PaginationMetadataSchema,
}


class PaginationMixin:
    """Extend Blueprint to add Pagination feature"""

    PAGINATION_ARGUMENTS_PARSER = FlaskParser()

    # Name of field to use for pagination metadata response header
    # Can be overridden. If None, no pagination header is returned.
    PAGINATION_HEADER_NAME = "X-Pagination"

    # Global default pagination parameters
    # Can be overridden to provide custom defaults
    DEFAULT_PAGINATION_PARAMETERS = {"page": 1, "page_size": 10, "max_page_size": 100}

    def paginate(self, pager=None, *, page=None, page_size=None, max_page_size=None):
        """Decorator adding pagination to the endpoint

        :param type[Page] pager: Page class used to paginate response data
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
            page = self.DEFAULT_PAGINATION_PARAMETERS["page"]
        if page_size is None:
            page_size = self.DEFAULT_PAGINATION_PARAMETERS["page_size"]
        if max_page_size is None:
            max_page_size = self.DEFAULT_PAGINATION_PARAMETERS["max_page_size"]
        page_params_schema = _pagination_parameters_schema_factory(
            page, page_size, max_page_size
        )

        parameters = {
            "in": "query",
            "schema": page_params_schema,
        }

        error_status_code = self.PAGINATION_ARGUMENTS_PARSER.DEFAULT_VALIDATION_STATUS

        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                page_params = self.PAGINATION_ARGUMENTS_PARSER.parse(
                    page_params_schema, request, location="query"
                )

                # Pagination in resource code: inject page_params as kwargs
                if pager is None:
                    kwargs["pagination_parameters"] = page_params

                # Execute decorated function
                result, status, headers = unpack_tuple_response(func(*args, **kwargs))

                # Post pagination: use pager class to paginate the result
                if pager is not None:
                    result = pager(result, page_params=page_params).items

                # Set pagination metadata in response
                if self.PAGINATION_HEADER_NAME is not None:
                    if page_params.item_count is None:
                        warnings.warn(
                            f"item_count not set in endpoint {request.endpoint}.",
                            stacklevel=2,
                        )
                    else:
                        result, headers = self._set_pagination_metadata(
                            page_params, result, headers
                        )

                return result, status, headers

            # Add pagination params to doc info in wrapper object
            wrapper._apidoc = deepcopy(getattr(wrapper, "_apidoc", {}))
            wrapper._apidoc["pagination"] = {
                "parameters": parameters,
                "response": {
                    error_status_code: http.HTTPStatus(error_status_code).name,
                },
            }

            return wrapper

        return decorator

    @staticmethod
    def _make_pagination_metadata(page, page_size, item_count):
        """Build pagination metadata from page, page size and item count

        Override this to use another pagination metadata structure
        """
        page_metadata = {}
        page_metadata["total"] = item_count
        if item_count == 0:
            page_metadata["total_pages"] = 0
        else:
            # First / last page, page count
            page_count = ((item_count - 1) // page_size) + 1
            first_page = 1
            last_page = page_count
            page_metadata["total_pages"] = page_count
            page_metadata["first_page"] = first_page
            page_metadata["last_page"] = last_page
            # Page, previous / next page
            if page <= last_page:
                page_metadata["page"] = page
                if page > first_page:
                    page_metadata["previous_page"] = page - 1
                if page < last_page:
                    page_metadata["next_page"] = page + 1
        return PaginationMetadataSchema().dump(page_metadata)

    def _set_pagination_metadata(self, page_params, result, headers):
        """Add pagination metadata to headers

        Override this to set pagination data another way
        """
        if headers is None:
            headers = {}
        headers[self.PAGINATION_HEADER_NAME] = json.dumps(
            self._make_pagination_metadata(
                page_params.page, page_params.page_size, page_params.item_count
            )
        )
        return result, headers

    def _document_pagination_metadata(self, spec, resp_doc):
        """Document pagination metadata header

        Override this to document custom pagination metadata
        """
        resp_doc.setdefault("headers", {}).update(
            {
                self.PAGINATION_HEADER_NAME: (
                    "PAGINATION"
                    if spec.openapi_version.major >= 3
                    else PAGINATION_HEADER
                )
            }
        )

    def _prepare_pagination_doc(self, doc, doc_info, *, spec, **kwargs):
        operation = doc_info.get("pagination")
        if operation:
            doc.setdefault("parameters", []).append(operation["parameters"])
            doc.setdefault("responses", {}).update(operation["response"])
            success_status_codes = doc_info.get("success_status_codes", [])
            for success_status_code in success_status_codes:
                self._document_pagination_metadata(
                    spec, doc["responses"][success_status_code]
                )
        return doc
