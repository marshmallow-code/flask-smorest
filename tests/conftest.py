from collections import namedtuple

import pytest

import marshmallow as ma

from flask import Flask

from .mocks import DatabaseMock


class AppConfig:
    """Base application configuration class

    Overload this to add config parameters
    """

    API_TITLE = "API Test"
    API_VERSION = "1"
    OPENAPI_VERSION = "3.0.2"
    TESTING = True


@pytest.fixture(params=[0])
def collection(request):
    _collection = DatabaseMock()
    for idx in range(request.param):
        _collection.post({"db_field": idx})
    return _collection


@pytest.fixture(params=[AppConfig])
def app(request):
    _app = Flask(__name__)
    _app.config.from_object(request.param)
    return _app


class CounterSchema(ma.Schema):
    """Base Schema with load/dump counters"""

    load_count = 0
    dump_count = 0

    @classmethod
    def reset_load_count(cls):
        cls.load_count = 0

    @classmethod
    def reset_dump_count(cls):
        cls.dump_count = 0

    @ma.post_load(pass_many=True)
    def increment_load_count(self, data, **kwargs):
        self.__class__.load_count += 1
        return data

    @ma.post_dump(pass_many=True)
    def increment_dump_count(self, data, **kwargs):
        self.__class__.dump_count += 1
        return data


@pytest.fixture
def schemas():
    class DocSchema(CounterSchema):
        item_id = ma.fields.Int(dump_only=True)
        field = ma.fields.Int(attribute="db_field")

    class QueryArgsSchema(ma.Schema):
        class Meta:
            ordered = True
            unknown = ma.EXCLUDE

        arg1 = ma.fields.String()
        arg2 = ma.fields.Integer()

    class ClientErrorSchema(ma.Schema):
        error_id = ma.fields.Str()
        text = ma.fields.Str()

    return namedtuple("Model", ("DocSchema", "QueryArgsSchema", "ClientErrorSchema"))(
        DocSchema, QueryArgsSchema, ClientErrorSchema
    )
