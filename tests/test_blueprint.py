"""Test Blueprint extra features"""

import json
import pytest

from flask import jsonify
from flask.views import MethodView

import marshmallow as ma

from flask_rest_api import Api
from flask_rest_api.blueprint import Blueprint, HTTP_METHODS
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
    def test_blueprint_arguments_required(self, app, schemas, required):
        api = Api(app)
        blp = Blueprint('test', __name__, url_prefix='/test')

        if required is None:
            @blp.route('/')
            @blp.arguments(schemas.DocSchema)
            def func():
                pass
        else:
            @blp.route('/')
            @blp.arguments(schemas.DocSchema, required=required)
            def func():
                pass

        api.register_blueprint(blp)
        spec = api.spec.to_dict()
        assert (spec['paths']['/test/']['get']['parameters'][0]['required'] ==
                (required is not False))

    def test_blueprint_arguments_multiple(self, app, schemas):
        api = Api(app)
        blp = Blueprint('test', __name__, url_prefix='/test')
        client = app.test_client()

        class QueryArgsSchema(ma.Schema):
            class Meta:
                strict = True
                ordered = True

            arg1 = ma.fields.String()
            arg2 = ma.fields.Integer()

        @blp.route('/', methods=('POST', ))
        @blp.arguments(schemas.DocSchema)
        @blp.arguments(QueryArgsSchema, location='query')
        def func(document, query_args):
            return jsonify({
                'document': document,
                'query_args': query_args,
            })

        api.register_blueprint(blp)
        spec = api.spec.to_dict()

        # Check parameters are documented
        parameters = spec['paths']['/test/']['post']['parameters']
        assert parameters[0]['name'] == 'arg1'
        assert parameters[0]['in'] == 'query'
        assert parameters[1]['name'] == 'arg2'
        assert parameters[1]['in'] == 'query'
        assert parameters[2]['in'] == 'body'
        assert 'field' in parameters[2]['schema']['properties']

        # Check parameters are passed as arguments to view function
        item_data = {'field': 12}
        response = client.post(
            '/test/',
            data=json.dumps(item_data),
            content_type='application/json',
            query_string={'arg1': 'test'}
        )
        assert response.status_code == 200
        assert response.json == {
            'document': {'db_field': 12},
            'query_args': {'arg1': 'test'},
        }

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

    def test_blueprint_enforce_method_order(self, app):
        api = Api(app)
        blp = Blueprint('test', __name__, url_prefix='/test')

        @blp.route('/')
        class Resource(MethodView):

            def post(self):
                pass

            def put(self):
                pass

            def options(self):
                pass

            def patch(self):
                pass

            def head(self):
                pass

            def delete(self):
                pass

            def get(self):
                pass

        api.register_blueprint(blp)
        methods_spec = api.spec.to_dict()['paths']['/test/']
        assert list(methods_spec.keys()) == [m.lower() for m in HTTP_METHODS]
