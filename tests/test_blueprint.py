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

    @pytest.mark.parametrize('openapi_version', ('2.0', '3.0.1'))
    @pytest.mark.parametrize(
        # Also test 'json/body' is default
        'location_map', LOCATIONS_MAPPING + ((None, 'body'),))
    def test_blueprint_arguments_location(
            self, app, schemas, location_map, openapi_version):
        app.config['OPENAPI_VERSION'] = openapi_version
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
        get = spec['paths']['/test/']['get']
        if openapi_location != 'body' or openapi_version == '2.0':
            loc = get['parameters'][0]['in']
            assert loc == openapi_location
            assert 'requestBody' not in get
        else:
            # In OpenAPI v3, 'body' parameter is in 'requestBody'
            assert 'parameters' not in get
            assert 'requestBody' in get

    def test_blueprint_arguments_location_invalid(self, app, schemas):
        blp = Blueprint('test', __name__, url_prefix='/test')
        with pytest.raises(InvalidLocation):
            blp.arguments(schemas.DocSchema, location='invalid')

    @pytest.mark.parametrize('openapi_version', ('2.0', '3.0.1'))
    @pytest.mark.parametrize('location_map', LOCATIONS_MAPPING)
    @pytest.mark.parametrize('required', (True, False, None))
    def test_blueprint_arguments_required(
            self, app, schemas, required, location_map, openapi_version):
        app.config['OPENAPI_VERSION'] = openapi_version
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
        get = api.spec.to_dict()['paths']['/test/']['get']
        if location == 'json':
            if openapi_version == '2.0':
                parameters = get['parameters']
                # One parameter: the schema
                assert len(parameters) == 1
                assert 'schema' in parameters[0]
                assert 'requestBody' not in get
                # Check required defaults to True
                assert parameters[0]['required'] == (required is not False)
            else:
                # Body parameter in 'requestBody'
                assert 'requestBody' in get
                # Check required defaults to True
                assert get['requestBody']['required'] == (
                    required is not False)
        else:
            parameters = get['parameters']
            # One parameter: the 'field' field in DocSchema
            assert len(parameters) == 1
            assert parameters[0]['name'] == 'field'
            assert 'requestBody' not in get
            # Check the required parameter has no impact.
            # Only the required attribute of the field matters
            assert parameters[0]['required'] is False

    @pytest.mark.parametrize('openapi_version', ('2.0', '3.0.1'))
    def test_blueprint_arguments_multiple(self, app, schemas, openapi_version):
        app.config['OPENAPI_VERSION'] = openapi_version
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

        if openapi_version == '2.0':
            assert len(parameters) == 3
            assert parameters[2]['in'] == 'body'
            assert 'field' in parameters[2]['schema']['properties']
        else:
            assert len(parameters) == 2
            assert 'field' in spec['paths']['/test/']['post']['requestBody'][
                'content']['application/json']['schema']['properties']

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

    @pytest.mark.parametrize('openapi_version', ['2.0', '3.0.1'])
    def test_blueprint_response_schema(self, app, openapi_version, schemas):
        """Check response schema is correctly documented.

        More specifically, check that:
        - plural response is documented as array in the spec
        - schema is document in the right place w.r.t. OpenAPI version
        """
        app.config['OPENAPI_VERSION'] = openapi_version
        api = Api(app)
        blp = Blueprint('test', 'test', url_prefix='/test')

        api.definition('Doc')(schemas.DocSchema)

        @blp.route('/schema_many_false')
        @blp.response(schemas.DocSchema(many=False))
        def many_false():
            pass

        @blp.route('/schema_many_true')
        @blp.response(schemas.DocSchema(many=True))
        def many_true():
            pass

        api.register_blueprint(blp)

        paths = api.spec.to_dict()['paths']

        response = paths['/test/schema_many_false']['get']['responses'][200]
        if openapi_version == '2.0':
            schema = response['schema']
            assert schema == {'$ref': '#/definitions/Doc'}
        else:
            schema = (
                response['content']['application/json']['schema'])
            assert schema == {'$ref': '#/components/schemas/Doc'}

        response = paths['/test/schema_many_true']['get']['responses'][200]
        if openapi_version == '2.0':
            schema = response['schema']['items']
            assert schema == {'$ref': '#/definitions/Doc'}
        else:
            schema = (
                response['content']['application/json']['schema']['items'])
            assert schema == {'$ref': '#/components/schemas/Doc'}

    def test_blueprint_pagination(self, app, schemas):
        api = Api(app)
        blp = Blueprint('test', __name__, url_prefix='/test')

        @blp.route('/')
        @blp.arguments(schemas.QueryArgsSchema, location='query')
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

    def test_blueprint_doc_function(self, app):
        api = Api(app)
        blp = Blueprint('test', __name__, url_prefix='/test')

        @blp.route('/', methods=('PUT', 'PATCH', ))
        @blp.doc(summary='Dummy func', description='Do dummy stuff')
        def view_func():
            pass

        api.register_blueprint(blp)
        spec = api.spec.to_dict()
        path = spec['paths']['/test/']
        for method in ('put', 'patch', ):
            assert path[method]['summary'] == 'Dummy func'
            assert path[method]['description'] == 'Do dummy stuff'

    def test_blueprint_doc_method_view(self, app):
        api = Api(app)
        blp = Blueprint('test', __name__, url_prefix='/test')

        @blp.route('/')
        class Resource(MethodView):

            @blp.doc(summary='Dummy put', description='Do dummy put')
            def put(self):
                pass

            @blp.doc(summary='Dummy patch', description='Do dummy patch')
            def patch(self):
                pass

        api.register_blueprint(blp)
        spec = api.spec.to_dict()
        path = spec['paths']['/test/']
        for method in ('put', 'patch', ):
            assert path[method]['summary'] == 'Dummy {}'.format(method)
            assert path[method]['description'] == 'Do dummy {}'.format(method)

    def test_blueprint_doc_info_from_docstring(self, app):
        api = Api(app)
        blp = Blueprint('test', __name__, url_prefix='/test')

        @blp.route('/')
        class Resource(MethodView):

            def get(self):
                """Docstring get summary"""

            def put(self):
                """Docstring put summary

                Docstring put description
                """

            @blp.doc(
                summary='Decorator patch summary',
                description='Decorator patch description'
            )
            def patch(self):
                """Docstring patch summary

                Docstring patch description
                """

        api.register_blueprint(blp)
        spec = api.spec.to_dict()
        path = spec['paths']['/test/']

        assert path['get']['summary'] == 'Docstring get summary'
        assert 'description' not in path['get']
        assert path['put']['summary'] == 'Docstring put summary'
        assert path['put']['description'] == 'Docstring put description'
        # @doc decorator overrides docstring
        assert path['patch']['summary'] == 'Decorator patch summary'
        assert path['patch']['description'] == 'Decorator patch description'

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
