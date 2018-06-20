"""Test Api class"""

from collections import OrderedDict

import pytest

from flask import jsonify
from flask.views import MethodView
from werkzeug.routing import BaseConverter
import marshmallow as ma

from flask_rest_api import Api, Blueprint

from .conftest import AppConfig


class TestAPISpec():
    """Test APISpec class"""

    @pytest.mark.parametrize('openapi_version', ['2.0', '3.0.1'])
    def test_apispec_parameters_from_app(self, app, openapi_version):

        class NewAppConfig(AppConfig):
            API_VERSION = 'v42'
            OPENAPI_VERSION = openapi_version

        app.config.from_object(NewAppConfig)
        api = Api(app)
        spec = api.spec.to_dict()

        assert spec['info'] == {'title': 'API Test', 'version': 'v42'}
        if openapi_version == '2.0':
            assert spec['swagger'] == '2.0'
        else:
            assert spec['openapi'] == '3.0.1'

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
    @pytest.mark.parametrize('mapping', [
        ('custom string', 'custom'),
        ('custom string', None),
        (ma.fields.Integer, ),
    ])
    def test_apispec_register_field(self, app, view_type, mapping):
        api = Api(app)
        blp = Blueprint('test', 'test', url_prefix='/test')

        class CustomField(ma.fields.Field):
            pass

        api.spec.register_field(CustomField, *mapping)

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

        if len(mapping) == 2:
            properties = {'field': {'type': 'custom string'}}
            # If mapping format is None, it does not appear in the spec
            if mapping[1] is not None:
                properties['field']['format'] = mapping[1]
        else:
            properties = {'field': {'type': 'integer', 'format': 'int32'}}

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

    @pytest.mark.parametrize(
        'redoc_version',
        (None, 'latest', 'v1.22', 'next', '2.0.0-alpha.17', 'v2.0.0-alpha.17')
    )
    def test_apipec_serve_redoc_using_cdn(self, app, redoc_version):

        class NewAppConfig(AppConfig):
            OPENAPI_URL_PREFIX = 'api-docs'
            OPENAPI_REDOC_PATH = 'redoc'
            if redoc_version:
                OPENAPI_REDOC_VERSION = redoc_version

        app.config.from_object(NewAppConfig)
        Api(app)
        client = app.test_client()
        response_redoc = client.get('/api-docs/redoc')
        assert (response_redoc.headers['Content-Type'] ==
                'text/html; charset=utf-8')

        redoc_version = redoc_version or 'latest'
        if redoc_version == 'latest' or redoc_version.startswith('v1'):
            redoc_url = (
                'https://rebilly.github.io/ReDoc/releases/'
                '{}/redoc.min.js'.format(redoc_version))
        else:
            redoc_url = (
                'https://cdn.jsdelivr.net/npm/redoc@'
                '{}/bundles/redoc.standalone.js'.format(redoc_version))
        script_elem = '<script src="{}"></script>'.format(redoc_url)

        assert script_elem in response_redoc.get_data(as_text=True)

    def test_apipec_serve_spec_preserve_order(self, app):
        app.config['OPENAPI_URL_PREFIX'] = '/api-docs'
        api = Api(app)
        client = app.test_client()

        # Add ordered stuff. This is invalid, but it will do for the test.
        paths = OrderedDict(
            [('/path_{}'.format(i), str(i)) for i in range(20)])
        api.spec._paths = paths

        response_json_docs = client.get('/api-docs/openapi.json')
        assert response_json_docs.status_code == 200
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

        api.register_blueprint(blp)

        paths = api.spec.to_dict()['paths']

        schema_many_false = paths[
            '/test/schema_many_false']['get']['responses'][200]['schema']
        assert schema_many_false['type'] == 'object'
        assert 'items' not in schema_many_false

        schema_many_true = paths[
            '/test/schema_many_true']['get']['responses'][200]['schema']
        assert schema_many_true['type'] == 'array'
        assert schema_many_true['items']['type'] == 'object'
