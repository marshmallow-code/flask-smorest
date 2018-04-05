"""Test Api class"""

from collections import OrderedDict

import pytest

from flask import jsonify
from flask.views import MethodView
from werkzeug.routing import BaseConverter
import marshmallow as ma

from flask_rest_api import Api, Blueprint, Page

from .conftest import AppConfig


class TestAPISpec():
    """Test APISpec class"""

    @pytest.mark.parametrize('view_type', ['function', 'method'])
    @pytest.mark.parametrize('custom_format', ['custom', None])
    def test_apispec_register_converter(self, app, view_type, custom_format):
        api = Api(app)
        blp = Blueprint('test', 'test', url_prefix='/test')

        class CustomConverter(BaseConverter):
            pass

        app.url_map.converters['custom_str'] = CustomConverter
        api.spec.register_converter(
            CustomConverter, 'custom string', custom_format)

        if view_type == 'function':
            @blp.route('/<custom_str:val>')
            def test_func(val):
                return jsonify(val)
        else:
            @blp.route('/<custom_str:val>')
            class TestMethod(MethodView):
                def get(self, val):
                    return jsonify(val)

        api.register_blueprint(blp)
        spec = api.spec.to_dict()

        # If custom_format is None (default), it does not appear in the spec
        if custom_format is not None:
            parameters = [{'in': 'path', 'name': 'val', 'required': True,
                           'type': 'custom string', 'format': 'custom'}]
        else:
            parameters = [{'in': 'path', 'name': 'val', 'required': True,
                           'type': 'custom string'}]
        assert spec['paths']['/test/{val}']['get']['parameters'] == parameters

    @pytest.mark.parametrize('view_type', ['function', 'method'])
    @pytest.mark.parametrize('custom_format', ['custom', None])
    def test_apispec_register_field(self, app, view_type, custom_format):
        api = Api(app)
        blp = Blueprint('test', 'test', url_prefix='/test')

        class CustomField(ma.fields.Field):
            pass

        api.spec.register_field(CustomField, 'custom string', custom_format)

        class Document(ma.Schema):
            field = CustomField()

        if view_type == 'function':
            @blp.route('/')
            @blp.arguments(Document)
            def test_func(args):
                return jsonify(None)
        else:
            @blp.route('/')
            class TestMethod(MethodView):
                @blp.arguments(Document)
                def get(self, args):
                    return jsonify(None)

        api.register_blueprint(blp)
        spec = api.spec.to_dict()

        # If custom_format is None (default), it does not appear in the spec
        properties = {'field': {'type': 'custom string'}}
        if custom_format is not None:
            properties['field']['format'] = 'custom'

        assert (spec['paths']['/test/']['get']['parameters'] ==
                [{'in': 'body', 'required': True, 'name': 'body',
                  'schema': {'properties': properties, 'type': 'object'}, }])


class TestAPISpecServeDocs():
    """Test APISpec class docs serving features"""

    @pytest.mark.parametrize(
        'prefix', (None, 'docs_url_prefix', '/docs_url_prefix',
                   'docs_url_prefix/', '/docs_url_prefix/'))
    @pytest.mark.parametrize('json_path', (None, 'openapi.json'))
    @pytest.mark.parametrize('redoc_path', (None, 'redoc'))
    def test_apipec_serve_spec(self, app, prefix, json_path, redoc_path):

        class NewAppConfig(AppConfig):
            if prefix:
                OPENAPI_URL_PREFIX = prefix
            if json_path:
                OPENAPI_JSON_PATH = json_path
            if redoc_path:
                OPENAPI_REDOC_PATH = redoc_path

        app.config.from_object(NewAppConfig)
        Api(app)
        client = app.test_client()
        response_json_docs = client.get('/docs_url_prefix/openapi.json')
        response_redoc = client.get('/docs_url_prefix/redoc')
        if app.config.get('OPENAPI_URL_PREFIX') is None:
            assert response_json_docs.status_code == 404
            assert response_redoc.status_code == 404
        else:
            assert response_json_docs.json['info'] == {
                'version': '1', 'title': 'API Test'}
            if app.config.get('OPENAPI_REDOC_PATH') is None:
                assert response_redoc.status_code == 404
            else:
                assert response_redoc.status_code == 200
                assert (response_redoc.headers['Content-Type'] ==
                        'text/html; charset=utf-8')

    def test_apipec_serve_spec_preserve_order(self, app):
        app.config['OPENAPI_URL_PREFIX'] = '/api-docs/'
        api = Api(app)
        client = app.test_client()

        # Add ordered stuff. This is invalid, but it will do for the test.
        paths = OrderedDict(
            [('/path_{}'.format(i), str(i)) for i in range(20)])
        api.spec._paths = paths

        response_json_docs = client.get('/api-docs/openapi.json')
        assert response_json_docs.json['paths'] == paths


class TestAPISpecPlugin():
    """Test apispec plugin"""

    def test_apipec_path_response_schema_many(self, app, schemas):
        """Check that plural response is documented as array in the spec"""
        api = Api(app)
        blp = Blueprint('test', 'test', url_prefix='/test')

        @blp.route('/schema_many_false')
        @blp.response(schemas.DocSchema(many=False))
        def many_false():
            pass

        @blp.route('/schema_many_true')
        @blp.response(schemas.DocSchema(many=True))
        def many_true():
            pass

        @blp.route('/paginate')
        @blp.response(schemas.DocSchema, paginate=True)
        def paginate():
            pass

        @blp.route('/paginate_with')
        @blp.response(schemas.DocSchema, paginate_with=Page)
        def paginate_with():
            pass

        api.register_blueprint(blp)

        paths = api.spec.to_dict()['paths']

        schema_many_false = paths[
            '/test/schema_many_false']['get']['responses'][200]['schema']
        assert schema_many_false['type'] == 'object'
        assert 'items' not in schema_many_false

        for path in ('schema_many_true', 'paginate', 'paginate_with'):
            schema = paths[
                '/test/{}'.format(path)]['get']['responses'][200]['schema']
            assert schema['type'] == 'array'
            assert schema['items']['type'] == 'object'
