from collections import namedtuple

import pytest

from marshmallow import Schema, fields, post_load, post_dump

from flask import Flask

from flask_smorest.compat import MARSHMALLOW_VERSION_MAJOR

from .mocks import DatabaseMock


class AppConfig:
    """Base application configuration class

    Overload this to add config parameters
    """
    OPENAPI_VERSION = '3.0.2'


@pytest.fixture(params=[0])
def collection(request):
    _collection = DatabaseMock()
    for idx in range(request.param):
        _collection.post({'db_field': idx})
    return _collection


@pytest.fixture(params=[AppConfig])
def app(request):
    _app = Flask('API Test')
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

    @post_load(pass_many=True)
    def increment_load_count(self, data, many, **kwargs):
        self.__class__.load_count += 1
        return data

    @post_dump(pass_many=True)
    def increment_dump_count(self, data, many, **kwargs):
        self.__class__.dump_count += 1
        return data


@pytest.fixture
def schemas():

    class DocSchema(CounterSchema):
        if MARSHMALLOW_VERSION_MAJOR < 3:
            class Meta:
                strict = True
        item_id = fields.Int(dump_only=True)
        field = fields.Int(attribute='db_field')

    class DocEtagSchema(CounterSchema):
        if MARSHMALLOW_VERSION_MAJOR < 3:
            class Meta:
                strict = True
        field = fields.Int(attribute='db_field')

    class QueryArgsSchema(Schema):
        class Meta:
            ordered = True
            if MARSHMALLOW_VERSION_MAJOR < 3:
                strict = True
        arg1 = fields.String()
        arg2 = fields.Integer()

    return namedtuple(
        'Model', ('DocSchema', 'DocEtagSchema', 'QueryArgsSchema'))(
            DocSchema, DocEtagSchema, QueryArgsSchema)
