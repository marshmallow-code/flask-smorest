from collections import namedtuple

import pytest

from marshmallow import Schema, fields

from flask import Flask

from .mocks import DatabaseMock
from .utils import JSONResponse


HTTP_METHODS = [
    'GET', 'PATCH', 'POST', 'HEAD', 'PUT', 'DELETE', 'OPTIONS', 'TRACE']


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


@pytest.fixture
def schemas():

    class DocSchema(Schema):
        class Meta:
            strict = True
        item_id = fields.Int(dump_only=True)
        field = fields.Int(attribute='db_field')

    class DocEtagSchema(Schema):
        class Meta:
            strict = True
        field = fields.Int(attribute='db_field')

    return namedtuple(
        'Model', ('DocSchema', 'DocEtagSchema'))(DocSchema, DocEtagSchema)
