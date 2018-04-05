from collections import namedtuple

import pytest

from marshmallow import Schema, fields, post_load, post_dump

from flask import Flask

from .mocks import DatabaseMock
from .utils import JSONResponse


class AppConfig:
    """Base application configuration class

    Overload this to add config parameters
    """


@pytest.fixture(params=[0])
def collection(request):
    _collection = DatabaseMock()
    for idx in range(request.param):
        _collection.post({'db_field': idx})
    return _collection


@pytest.fixture(params=[AppConfig])
def app(request):
    _app = Flask('API Test')
    _app.response_class = JSONResponse
    _app.config.from_object(request.param)
    return _app


class CounterSchema(Schema):
    """Base Schema with load/dump counters"""

    load_count = 0
    dump_count = 0

    @classmethod
    def reset_load_count(cls):
        cls.load_count = 0

    @classmethod
    def reset_dump_count(cls):
        cls.dump_count = 0

    @post_load
    def increment_load_count(self, _):
        self.__class__.load_count += 1

    @post_dump
    def increment_dump_count(self, _):
        self.__class__.dump_count += 1


@pytest.fixture
def schemas():

    class DocSchema(CounterSchema):
        class Meta:
            strict = True
        item_id = fields.Int(dump_only=True)
        field = fields.Int(attribute='db_field')

    class DocEtagSchema(CounterSchema):
        class Meta:
            strict = True
        field = fields.Int(attribute='db_field')

    return namedtuple(
        'Model', ('DocSchema', 'DocEtagSchema'))(DocSchema, DocEtagSchema)
