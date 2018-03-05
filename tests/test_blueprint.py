"""Test Blueprint extra features"""

import pytest

from flask_rest_api import Api
from flask_rest_api.blueprint import Blueprint
from flask_rest_api.exceptions import MultiplePaginationModes, InvalidLocation
from flask_rest_api.pagination import Page


LOCATIONS_MAPPING = (
    ('querystring', 'query',),
    ('query', 'query',),
    ('json', 'body',),
    ('form', 'formData',),
    ('headers', 'header',),
    ('files', 'formData',),
    # Test 'body' is default
    (None, 'body',),
)


class TestBlueprint():
    """Test Blueprint class"""

    @pytest.mark.parametrize('location_map', LOCATIONS_MAPPING)
    def test_blueprint_arguments_location(self, app, schemas, location_map):
        api = Api(app)
        blp = Blueprint('test', __name__, url_prefix='/test')
        location, openapi_location = location_map

        if location is not None:
            @blp.route('/')
            @blp.arguments(schemas.DocSchema, location=location)
            def func():
                """Dummy view func"""
        else:
            @blp.route('/')
            @blp.arguments(schemas.DocSchema)
            def func():
                """Dummy view func"""

        api.register_blueprint(blp)
        spec = api.spec.to_dict()
        loc = spec['paths']['/test/']['get']['parameters'][0]['in']
        assert loc == openapi_location

    def test_blueprint_arguments_location_invalid(self, app, schemas):
        blp = Blueprint('test', __name__, url_prefix='/test')
        with pytest.raises(InvalidLocation):
            blp.arguments(schemas.DocSchema, location='invalid')

    @pytest.mark.parametrize('required', (None, True, False))
    def test_blueprint_arguments_required(self, schemas, required):
        bp = Blueprint('test', __name__, url_prefix='/test')

        def view_func():
            pass

        if required is None:
            res = bp.arguments(schemas.DocSchema)(view_func)
        else:
            res = bp.arguments(schemas.DocSchema, required=required)(view_func)
        assert res._apidoc['parameters']['required'] == (required is not False)

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

    def test_blueprint_doc(self):
        blp = Blueprint('test', __name__, url_prefix='/test')

        def view_func():
            pass

        res = blp.doc(summary='Dummy func', description='Do dummy stuff')(
            view_func)
        assert res._apidoc['summary'] == 'Dummy func'
        assert res._apidoc['description'] == 'Do dummy stuff'
