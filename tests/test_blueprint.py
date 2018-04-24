"""Test Blueprint extra features"""

import json
import pytest

from flask import jsonify
from flask.views import MethodView

from flask_rest_api import Api
from flask_rest_api.blueprint import Blueprint, HTTP_METHODS
from flask_rest_api.exceptions import InvalidLocation


LOCATIONS_MAPPING = (
    ('querystring', 'query',),
    ('query', 'query',),
    ('json', 'body',),
    ('form', 'formData',),
    ('headers', 'header',),
    ('files', 'formData',),
)


class TestBlueprint():
    """Test Blueprint class"""

    @pytest.mark.parametrize(
        # Also test 'json/body' is default
        'location_map', LOCATIONS_MAPPING + ((None, 'body'),))
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

    @pytest.mark.parametrize('location_map', LOCATIONS_MAPPING)
    @pytest.mark.parametrize('required', (True, False, None))
    def test_blueprint_arguments_required(
            self, app, schemas, required, location_map):
        api = Api(app)
        blp = Blueprint('test', __name__, url_prefix='/test')
        location, _ = location_map

        if required is None:
            @blp.route('/')
            @blp.arguments(schemas.DocSchema, location=location)
            def func():
                pass
        else:
            @blp.route('/')
            @blp.arguments(
                schemas.DocSchema, required=required, location=location)
            def func():
                pass

        api.register_blueprint(blp)
        parameters = api.spec.to_dict()['paths']['/test/']['get']['parameters']
        if location == 'json':
            # One parameter: the schema
            assert len(parameters) == 1
            assert 'schema' in parameters[0]
            # Check required defaults to True
            assert parameters[0]['required'] == (required is not False)
        else:
            # One parameter: the 'field' field in DocSchema
            assert len(parameters) == 1
            assert parameters[0]['name'] == 'field'
            # Check the required parameter has no impact.
            # Only the required attribute of the field matters
            assert parameters[0]['required'] is False

    def test_blueprint_arguments_multiple(self, app, schemas):
        api = Api(app)
        blp = Blueprint('test', __name__, url_prefix='/test')
        client = app.test_client()

        @blp.route('/', methods=('POST', ))
        @blp.arguments(schemas.DocSchema)
        @blp.arguments(schemas.QueryArgsSchema, location='query')
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

        # Check parameters are passed as arguments to view function
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

    def test_blueprint_pagination(self, app, schemas):
        api = Api(app)
        blp = Blueprint('test', __name__, url_prefix='/test')

        @blp.route('/')
        @blp.arguments(schemas.QueryArgsSchema, location='query')
        @blp.response(schemas.DocSchema)
        @blp.paginate()
        def func():
            """Dummy view func"""

        api.register_blueprint(blp)
        spec = api.spec.to_dict()

        # Check parameters are documented
        parameters = spec['paths']['/test/']['get']['parameters']
        # Page
        assert parameters[0]['name'] == 'page'
        assert parameters[0]['in'] == 'query'
        assert parameters[0]['type'] == 'integer'
        assert parameters[0]['required'] is False
        assert parameters[0]['default'] == 1
        assert parameters[0]['minimum'] == 1
        # Page size
        assert parameters[1]['name'] == 'page_size'
        assert parameters[1]['in'] == 'query'
        assert parameters[1]['type'] == 'integer'
        assert parameters[1]['required'] is False
        assert parameters[1]['default'] == 10
        assert parameters[1]['minimum'] == 1
        assert parameters[1]['maximum'] == 100
        # Other query string parameters
        assert parameters[1]['in'] == 'query'
        assert parameters[2]['name'] == 'arg1'
        assert parameters[2]['in'] == 'query'
        assert parameters[3]['name'] == 'arg2'
        assert parameters[3]['in'] == 'query'

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
