"""Test Blueprint extra features"""

import pytest

import marshmallow as ma

from flask_rest_api import Api
from flask_rest_api.blueprint import Blueprint
from flask_rest_api.exceptions import InvalidLocation, MultiplePaginationModes
from flask_rest_api.pagination import Page


class TestBlueprint():
    """Test Blueprint class"""

    def test_blueprint_arguments(self, app):
        """Test arguments function"""

        api = Api(app)
        bp = Blueprint('test', __name__, url_prefix='/test')
        api.register_blueprint(bp)

        class SampleQueryArgsSchema(ma.Schema):
            """Sample query parameters to define in documentation"""
            class Meta:
                strict = True
            item_id = ma.fields.Integer(dump_only=True)
            field = ma.fields.String()

        def sample_func():
            """Sample method to define in documentation"""
            return "It's Supercalifragilisticexpialidocious!"

        # Check OpenAPI location mapping
        res = bp.arguments(
            SampleQueryArgsSchema, location='querystring')(sample_func)
        assert res._apidoc['parameters']['location'] == 'query'
        res = bp.arguments(
            SampleQueryArgsSchema, location='query')(sample_func)
        assert res._apidoc['parameters']['location'] == 'query'
        res = bp.arguments(
            SampleQueryArgsSchema, location='json')(sample_func)
        assert res._apidoc['parameters']['location'] == 'body'
        res = bp.arguments(
            SampleQueryArgsSchema, location='form')(sample_func)
        assert res._apidoc['parameters']['location'] == 'formData'
        res = bp.arguments(
            SampleQueryArgsSchema, location='headers')(sample_func)
        assert res._apidoc['parameters']['location'] == 'header'
        res = bp.arguments(
            SampleQueryArgsSchema, location='files')(sample_func)
        assert res._apidoc['parameters']['location'] == 'formData'
        with pytest.raises(InvalidLocation):
            res = bp.arguments(
                SampleQueryArgsSchema, location='bad')(sample_func)

    def test_blueprint_multiple_paginate_modes(self):

        blp = Blueprint('test', __name__, url_prefix='/test')

        with pytest.raises(MultiplePaginationModes):
            @blp.response(paginate=True, paginate_with=Page)
            def get(self):
                pass

    def test_blueprint_keywork_only_args(self):

        blp = Blueprint('test', __name__, url_prefix='/test')

        # All arguments but schema are keyword-only arguments
        with pytest.raises(TypeError):
            # pylint: disable=too-many-function-args
            blp.response(None, 200)
