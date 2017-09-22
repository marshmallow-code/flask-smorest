"""Test Blueprint extra features"""

import pytest

import marshmallow as ma

from paginate import Page

from flask_rest_api import Api
from flask_rest_api.blueprint import Blueprint
from flask_rest_api.exceptions import InvalidLocation, MultiplePaginationModes


class TestBlueprint():
    """Test Blueprint class"""

    def test_blueprint_use_args(self, app):
        """Test use_args function"""

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
        res = bp.use_args(
            SampleQueryArgsSchema, location='querystring')(sample_func)
        assert res.__apidoc__['parameters']['location'] == 'query'
        res = bp.use_args(
            SampleQueryArgsSchema, location='query')(sample_func)
        assert res.__apidoc__['parameters']['location'] == 'query'
        res = bp.use_args(
            SampleQueryArgsSchema, location='json')(sample_func)
        assert res.__apidoc__['parameters']['location'] == 'body'
        res = bp.use_args(
            SampleQueryArgsSchema, location='form')(sample_func)
        assert res.__apidoc__['parameters']['location'] == 'formData'
        res = bp.use_args(
            SampleQueryArgsSchema, location='headers')(sample_func)
        assert res.__apidoc__['parameters']['location'] == 'header'
        res = bp.use_args(
            SampleQueryArgsSchema, location='files')(sample_func)
        assert res.__apidoc__['parameters']['location'] == 'formData'
        with pytest.raises(InvalidLocation):
            res = bp.use_args(
                SampleQueryArgsSchema, location='bad')(sample_func)

    def test_blueprint_multiple_paginate_modes(self):

        blp = Blueprint('test', __name__, url_prefix='/test')

        with pytest.raises(MultiplePaginationModes):
            @blp.marshal_with(paginate=True, paginate_with=Page)
            def get(self):
                pass
