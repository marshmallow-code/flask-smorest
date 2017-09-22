"""Test Blueprint extra features"""

import marshmallow as ma

from flask_rest_api import Api
from flask_rest_api.blueprint import Blueprint


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

        # check __apidoc__ (location mapping...)
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
            SampleQueryArgsSchema, location='files')(sample_func)
        assert res.__apidoc__['parameters']['location'] == 'formData'
        res = bp.use_args(
            SampleQueryArgsSchema, location='headers')(sample_func)
        assert res.__apidoc__['parameters']['location'] == 'header'

        # default apispec location
        res = bp.use_args(SampleQueryArgsSchema, location='bad')(sample_func)
        assert res.__apidoc__['parameters']['location'] == 'body'
