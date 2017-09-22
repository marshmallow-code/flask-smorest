"""Pagination feature"""

import marshmallow as ma

from .utils import get_appcontext


class PaginationParameters:
    """Pagination utilities"""

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


class PaginationParametersSchema(ma.Schema):
    # pylint: disable=too-few-public-methods
    """Deserialize pagination parameters: page number and page size"""

    class Meta:
        strict = True

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


class PaginationData:

    def __init__(self, page, page_size, total_count):
        self.page = page
        self.page_size = page_size
        self.total_count = total_count


# TODO: add other pagination data: first, last, prev, next
class PaginationDataSchema(ma.Schema):

    class Meta:
        strict = True

    total = ma.fields.Integer(
        attribute='total_count'
    )


def _get_pagination_ctx():
    """Get pagination section of AppContext"""
    return get_appcontext().setdefault('pagination', {})


def set_pagination_parameters(page, page_size):
    """Store pagination parameters in AppContext

    Called automatically
    """
    _get_pagination_ctx()['parameters'] = (page, page_size)


def set_item_count(item_count):
    """Set total number of items when paginating

    Should be called from resource code to provide pagination metadata
    """
    page, page_size = _get_pagination_ctx()['parameters']
    pagination_data = PaginationData(page, page_size, item_count)
    _get_pagination_ctx()['data'] = pagination_data


def get_pagination_data():
    """Get pagination metadata from AppContext"""
    return _get_pagination_ctx().get('data')
