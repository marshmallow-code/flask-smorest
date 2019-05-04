"""Test Blueprint extra features"""

import json
import http
import pytest

import marshmallow as ma

from flask import jsonify
from flask.views import MethodView

from flask_rest_api import Api, Blueprint, Page
from flask_rest_api.exceptions import InvalidLocationError

from .utils import build_ref


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

    @pytest.mark.parametrize('openapi_version', ('2.0', '3.0.2'))
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
        with pytest.raises(InvalidLocationError):
            blp.arguments(schemas.DocSchema, location='invalid')

    @pytest.mark.parametrize('openapi_version', ('2.0', '3.0.2'))
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

    @pytest.mark.parametrize('openapi_version', ('2.0', '3.0.2'))
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
            assert 'schema' in parameters[2]
        else:
            assert len(parameters) == 2
            assert 'schema' in spec['paths']['/test/']['post']['requestBody'][
                'content']['application/json']

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

    # This is only relevant to OAS3.
    @pytest.mark.parametrize('openapi_version', ('3.0.2', ))
    def test_blueprint_arguments_examples(self, app, schemas, openapi_version):
        app.config['OPENAPI_VERSION'] = openapi_version
        api = Api(app)
        blp = Blueprint('test', __name__, url_prefix='/test')

        example = {'field': 12}
        examples = {'example 1': {'field': 12}, 'example 2': {'field': 42}}

        @blp.route('/example')
        @blp.arguments(schemas.DocSchema, example=example)
        def func_example():
            """Dummy view func"""

        @blp.route('/examples')
        @blp.arguments(schemas.DocSchema, examples=examples)
        def func_examples():
            """Dummy view func"""

        api.register_blueprint(blp)
        spec = api.spec.to_dict()
        get = spec['paths']['/test/example']['get']
        assert (
            get['requestBody']['content']['application/json']['example'] ==
            example
        )
        get = spec['paths']['/test/examples']['get']
        assert (
            get['requestBody']['content']['application/json']['examples'] ==
            examples
        )

    @pytest.mark.parametrize('openapi_version', ('2.0', '3.0.2'))
    def test_blueprint_path_parameters(self, app, openapi_version):
        """Check auto and manual param docs are merged"""
        app.config['OPENAPI_VERSION'] = openapi_version
        api = Api(app)
        blp = Blueprint('test', __name__, url_prefix='/test')

        @blp.route('/<int:item_id>')
        @blp.doc(parameters=[
            {'name': 'item_id', 'in': 'path', 'description': 'Item ID'}
        ])
        def get(item_id):
            pass

        api.register_blueprint(blp)
        spec = api.spec.to_dict()
        params = spec['paths']['/test/{item_id}']['get']['parameters']
        assert len(params) == 1
        if openapi_version == '2.0':
            assert params == [{
                'name': 'item_id', 'in': 'path', 'required': True,
                'description': 'Item ID',
                'format': 'int32', 'type': 'integer'}]
        else:
            assert params == [{
                'name': 'item_id', 'in': 'path', 'required': True,
                'description': 'Item ID',
                'schema': {'format': 'int32', 'type': 'integer'}
            }]

    @pytest.mark.parametrize('openapi_version', ['2.0', '3.0.2'])
    def test_blueprint_response_schema(self, app, openapi_version, schemas):
        """Check response schema is correctly documented.

        More specifically, check that:
        - plural response is documented as array in the spec
        - schema is document in the right place w.r.t. OpenAPI version
        """
        app.config['OPENAPI_VERSION'] = openapi_version
        api = Api(app)
        blp = Blueprint('test', 'test', url_prefix='/test')

        api.schema('Doc')(schemas.DocSchema)

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

        schema_ref = build_ref(api.spec, 'schema', 'Doc')

        response = paths['/test/schema_many_false']['get']['responses']['200']
        if openapi_version == '2.0':
            assert response['schema'] == schema_ref
        else:
            assert (
                response['content']['application/json']['schema'] ==
                schema_ref
            )

        response = paths['/test/schema_many_true']['get']['responses']['200']
        if openapi_version == '2.0':
            assert response['schema']['items'] == schema_ref
        else:
            assert (
                response['content']['application/json']['schema']['items'] ==
                schema_ref
            )

    def test_blueprint_response_description(self, app):
        api = Api(app)
        blp = Blueprint('test', 'test', url_prefix='/test')

        @blp.route('/route_1')
        @blp.response()
        def func_1():
            pass

        @blp.route('/route_2')
        @blp.response(description='Test')
        def func_2():
            pass

        api.register_blueprint(blp)

        get_1 = api.spec.to_dict()['paths']['/test/route_1']['get']
        assert 'description' not in get_1['responses']['200']
        get_2 = api.spec.to_dict()['paths']['/test/route_2']['get']
        assert get_2['responses']['200']['description'] == 'Test'

    @pytest.mark.parametrize('openapi_version', ('2.0', '3.0.2'))
    def test_blueprint_response_example(self, app, openapi_version):
        app.config['OPENAPI_VERSION'] = openapi_version
        api = Api(app)
        blp = Blueprint('test', 'test', url_prefix='/test')

        example = {'name': 'One'}

        @blp.route('/')
        @blp.response(example=example)
        def func():
            pass

        api.register_blueprint(blp)

        get = api.spec.to_dict()['paths']['/test/']['get']
        if openapi_version == '2.0':
            assert get['responses']['200']['examples'][
                'application/json'] == example
        else:
            assert get['responses']['200']['content'][
                'application/json']['example'] == example

    # This is only relevant to OAS3.
    @pytest.mark.parametrize('openapi_version', ('3.0.2', ))
    def test_blueprint_response_examples(self, app, openapi_version):
        app.config['OPENAPI_VERSION'] = openapi_version
        api = Api(app)
        blp = Blueprint('test', 'test', url_prefix='/test')

        examples = {
            'example 1': {'summary': 'Example 1', 'value': {'name': 'One'}},
            'example 2': {'summary': 'Example 2', 'value': {'name': 'Two'}},
        }

        @blp.route('/')
        @blp.response(examples=examples)
        def func():
            pass

        api.register_blueprint(blp)

        get = api.spec.to_dict()['paths']['/test/']['get']
        assert get['responses']['200']['content']['application/json'][
            'examples'] == examples

    def test_blueprint_response_headers(self, app):
        api = Api(app)
        blp = Blueprint('test', 'test', url_prefix='/test')

        headers = {'X-Header': {'description': 'Custom header'}}

        @blp.route('/')
        @blp.response(headers=headers)
        def func():
            pass

        api.register_blueprint(blp)

        get = api.spec.to_dict()['paths']['/test/']['get']
        assert get['responses']['200']['headers'] == headers

    @pytest.mark.parametrize('openapi_version', ('2.0', '3.0.2'))
    def test_blueprint_pagination(self, app, schemas, openapi_version):
        app.config['OPENAPI_VERSION'] = openapi_version
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
        assert parameters[0]['required'] is False
        if openapi_version == '2.0':
            assert parameters[0]['type'] == 'integer'
            assert parameters[0]['default'] == 1
            assert parameters[0]['minimum'] == 1
        else:
            assert parameters[0]['schema']['type'] == 'integer'
            assert parameters[0]['schema']['default'] == 1
            assert parameters[0]['schema']['minimum'] == 1
        # Page size
        assert parameters[1]['name'] == 'page_size'
        assert parameters[1]['in'] == 'query'
        assert parameters[1]['required'] is False
        if openapi_version == '2.0':
            assert parameters[1]['type'] == 'integer'
            assert parameters[1]['default'] == 10
            assert parameters[1]['minimum'] == 1
            assert parameters[1]['maximum'] == 100
        else:
            assert parameters[1]['schema']['type'] == 'integer'
            assert parameters[1]['schema']['default'] == 10
            assert parameters[1]['schema']['minimum'] == 1
            assert parameters[1]['schema']['maximum'] == 100
        # Other query string parameters
        assert parameters[1]['in'] == 'query'
        assert parameters[2]['name'] == 'arg1'
        assert parameters[2]['in'] == 'query'
        assert parameters[3]['name'] == 'arg2'
        assert parameters[3]['in'] == 'query'

    def test_blueprint_doc_function(self, app):
        api = Api(app)
        blp = Blueprint('test', __name__, url_prefix='/test')
        client = app.test_client()

        @blp.route('/', methods=('PUT', 'PATCH', ))
        @blp.doc(summary='Dummy func', description='Do dummy stuff')
        def view_func():
            return jsonify({'Value': 'OK'})

        api.register_blueprint(blp)
        spec = api.spec.to_dict()
        path = spec['paths']['/test/']
        for method in ('put', 'patch', ):
            assert path[method]['summary'] == 'Dummy func'
            assert path[method]['description'] == 'Do dummy stuff'

        response = client.put('/test/')
        assert response.status_code == 200
        assert response.json == {'Value': 'OK'}

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

    def test_blueprint_doc_called_twice(self, app):
        api = Api(app)
        blp = Blueprint('test', __name__, url_prefix='/test')

        @blp.route('/')
        @blp.doc(summary='Dummy func')
        @blp.doc(description='Do dummy stuff')
        def view_func():
            pass

        api.register_blueprint(blp)
        spec = api.spec.to_dict()
        path = spec['paths']['/test/']
        assert path['get']['summary'] == 'Dummy func'
        assert path['get']['description'] == 'Do dummy stuff'

    # Regression test for https://github.com/Nobatek/flask-rest-api/issues/19
    def test_blueprint_doc_merged_after_prepare_doc(self, app):
        app.config['OPENAPI_VERSION'] = '3.0.2'
        api = Api(app)
        blp = Blueprint('test', __name__, url_prefix='/test')

        # This is a dummy example. In real-life, use 'example' parameter.
        doc_example = {
            'content': {'application/json': {'example': {'test': 123}}}}

        class ItemSchema(ma.Schema):
            test = ma.fields.Int()

        @blp.route('/')
        class Resource(MethodView):

            @blp.doc(**{'requestBody': doc_example})
            @blp.doc(**{'responses': {200: doc_example}})
            @blp.arguments(ItemSchema)
            @blp.response(ItemSchema)
            def get(self):
                pass

        api.register_blueprint(blp)
        spec = api.spec.to_dict()
        get = spec['paths']['/test/']['get']
        assert get['requestBody']['content']['application/json'][
            'example'] == {'test': 123}
        resp = get['responses']['200']
        assert resp['content']['application/json']['example'] == {'test': 123}
        assert 'schema' in resp['content']['application/json']

    @pytest.mark.parametrize('status_code', (200, '200', http.HTTPStatus.OK))
    def test_blueprint_response_status_code_cast_to_string(
            self, app, status_code):
        api = Api(app)
        blp = Blueprint('test', __name__, url_prefix='/test')

        # This is a dummy example. In real-life, use 'description' parameter.
        doc_desc = {'description': 'Description'}

        class ItemSchema(ma.Schema):
            test = ma.fields.Int()

        @blp.route('/')
        class Resource(MethodView):

            # When documenting a response, @blp.doc MUST use the same type
            # to express the status code as the one used in @blp.response.
            # (Default is 200 expressed as int.)
            @blp.doc(**{'responses': {status_code: doc_desc}})
            @blp.arguments(ItemSchema)
            @blp.response(ItemSchema, code=status_code)
            def get(self):
                pass

        api.register_blueprint(blp)
        spec = api.spec.to_dict()
        resp = spec['paths']['/test/']['get']['responses']['200']
        assert resp['description'] == 'Description'
        assert 'schema' in resp['content']['application/json']

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

    @pytest.mark.parametrize('http_methods', (
        ['OPTIONS', 'HEAD', 'GET', 'POST', 'PUT', 'PATCH', 'DELETE'],
        ['PUT', 'PATCH', 'DELETE', 'OPTIONS', 'HEAD', 'GET', 'POST'],
    ))
    def test_blueprint_enforce_method_order(self, app, http_methods):
        api = Api(app)

        class MyBlueprint(Blueprint):
            HTTP_METHODS = http_methods

        blp = MyBlueprint('test', __name__, url_prefix='/test')

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
        methods = list(api.spec.to_dict()['paths']['/test/'].keys())
        assert methods == [m.lower() for m in http_methods]

    @pytest.mark.parametrize('as_method_view', (True, False))
    def test_blueprint_multiple_routes_per_view(self, app, as_method_view):
        api = Api(app)
        blp = Blueprint('test', __name__, url_prefix='/test')

        if as_method_view:
            # Blueprint.route ensures a different endpoint is used for each
            # route. Otherwise, this would break in Blueprint.route when
            # calling as_view for the second time with the same endpoint.
            @blp.route('/route_1')
            @blp.route('/route_2')
            class Resource(MethodView):

                def get(self):
                    pass

        else:
            @blp.route('/route_1')
            @blp.route('/route_2')
            def func():
                pass

        api.register_blueprint(blp)
        paths = api.spec.to_dict()['paths']

        assert 'get' in paths['/test/route_1']
        assert 'get' in paths['/test/route_2']

    @pytest.mark.parametrize('as_method_view', (True, False))
    def test_blueprint_route_path_parameter_default(self, app, as_method_view):
        api = Api(app)
        blp = Blueprint('test', __name__, url_prefix='/test')

        if as_method_view:
            @blp.route('/<int:user_id>')
            @blp.route('/', defaults={'user_id': 1})
            class Resource(MethodView):

                def get(self, user_id):
                    pass

        else:
            @blp.route('/<int:user_id>')
            @blp.route('/', defaults={'user_id': 1})
            def func(user_id):
                pass

        api.register_blueprint(blp)
        paths = api.spec.to_dict()['paths']

        assert 'parameters' not in paths['/test/']['get']
        assert paths['/test/{user_id}']['get']['parameters'][0][
            'name'] == 'user_id'

    def test_blueprint_response_tuple(self, app):
        api = Api(app)
        blp = Blueprint('test', __name__, url_prefix='/test')
        client = app.test_client()

        @blp.route('/response')
        @blp.response()
        def func_response():
            return {}

        @blp.route('/response_code_int')
        @blp.response()
        def func_response_code_int():
            return {}, 201

        @blp.route('/response_code_str')
        @blp.response()
        def func_response_code_str():
            return {}, '201 CREATED'

        @blp.route('/response_headers')
        @blp.response()
        def func_response_headers():
            return {}, {'X-header': 'test'}

        @blp.route('/response_code_int_headers')
        @blp.response()
        def func_response_code_int_headers():
            return {}, 201, {'X-header': 'test'}

        @blp.route('/response_code_str_headers')
        @blp.response()
        def func_response_code_str_headers():
            return {}, '201 CREATED', {'X-header': 'test'}

        @blp.route('/response_wrong_tuple')
        @blp.response()
        def func_response_wrong_tuple():
            return {}, 201, {'X-header': 'test'}, 'extra'

        @blp.route('/response_tuple_subclass')
        @blp.response()
        def func_response_tuple_subclass():
            class MyTuple(tuple):
                pass
            return MyTuple((1, 2))

        api.register_blueprint(blp)

        response = client.get('/test/response')
        assert response.status_code == 200
        assert response.json == {}
        response = client.get('/test/response_code_int')
        assert response.status_code == 201
        assert response.status == '201 CREATED'
        assert response.json == {}
        response = client.get('/test/response_code_str')
        assert response.status_code == 201
        assert response.status == '201 CREATED'
        assert response.json == {}
        response = client.get('/test/response_headers')
        assert response.status_code == 200
        assert response.json == {}
        assert response.headers['X-header'] == 'test'
        response = client.get('/test/response_code_int_headers')
        assert response.status_code == 201
        assert response.status == '201 CREATED'
        assert response.json == {}
        assert response.headers['X-header'] == 'test'
        response = client.get('/test/response_code_str_headers')
        assert response.status_code == 201
        assert response.status == '201 CREATED'
        assert response.json == {}
        assert response.headers['X-header'] == 'test'
        response = client.get('/test/response_wrong_tuple')
        assert response.status_code == 500
        response = client.get('/test/response_tuple_subclass')
        assert response.status_code == 200
        assert response.json == [1, 2]

    def test_blueprint_pagination_response_tuple(self, app):
        api = Api(app)
        blp = Blueprint('test', __name__, url_prefix='/test')
        client = app.test_client()

        @blp.route('/response')
        @blp.response()
        @blp.paginate(Page)
        def func_response():
            return [1, 2]

        @blp.route('/response_code')
        @blp.response()
        @blp.paginate(Page)
        def func_response_code():
            return [1, 2], 201

        @blp.route('/response_headers')
        @blp.response()
        @blp.paginate(Page)
        def func_response_headers():
            return [1, 2], {'X-header': 'test'}

        @blp.route('/response_code_headers')
        @blp.response()
        @blp.paginate(Page)
        def func_response_code_headers():
            return [1, 2], 201, {'X-header': 'test'}

        @blp.route('/response_wrong_tuple')
        @blp.response()
        @blp.paginate(Page)
        def func_response_wrong_tuple():
            return [1, 2], 201, {'X-header': 'test'}, 'extra'

        @blp.route('/response_tuple_subclass')
        @blp.response()
        @blp.paginate(Page)
        def func_response_tuple_subclass():
            class MyTuple(tuple):
                pass
            return MyTuple((1, 2))

        api.register_blueprint(blp)

        response = client.get('/test/response')
        assert response.status_code == 200
        assert response.json == [1, 2]
        response = client.get('/test/response_code')
        assert response.status_code == 201
        assert response.json == [1, 2]
        response = client.get('/test/response_headers')
        assert response.status_code == 200
        assert response.json == [1, 2]
        assert response.headers['X-header'] == 'test'
        response = client.get('/test/response_code_headers')
        assert response.status_code == 201
        assert response.json == [1, 2]
        assert response.headers['X-header'] == 'test'
        response = client.get('/test/response_wrong_tuple')
        assert response.status_code == 500
        response = client.get('/test/response_tuple_subclass')
        assert response.status_code == 200
        assert response.json == [1, 2]

    def test_blueprint_response_response_object(self, app, schemas):
        api = Api(app)
        blp = Blueprint('test', __name__, url_prefix='/test')
        client = app.test_client()

        @blp.route('/response')
        # Schema is ignored when response object is returned
        @blp.response(schemas.DocSchema, code=200)
        def func_response():
            return jsonify({}), 201, {'X-header': 'test'}

        api.register_blueprint(blp)

        response = client.get('/test/response')
        assert response.status_code == 201
        assert response.status == '201 CREATED'
        assert response.json == {}
        assert response.headers['X-header'] == 'test'
