"""Test Api class"""

from collections import OrderedDict

import pytest

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

    @pytest.mark.parametrize('openapi_version', ['2.0', '3.0.1'])
    def test_apipec_path_response_schema(self, app, openapi_version, schemas):
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


class TestAPISpecServeDocs():
    """Test APISpec class docs serving features"""

    @pytest.mark.parametrize(
        'prefix', (None, 'docs_url_prefix', '/docs_url_prefix',
                   'docs_url_prefix/', '/docs_url_prefix/'))
    @pytest.mark.parametrize('json_path', (None, 'openapi.json'))
    @pytest.mark.parametrize('redoc_path', (None, 'redoc'))
    @pytest.mark.parametrize('swagger_ui_path', (None, 'swagger-ui'))
    @pytest.mark.parametrize('swagger_ui_version', (None, '3.0.0'))
    def test_apipec_serve_spec(self, app, prefix, json_path, redoc_path,
                               swagger_ui_path, swagger_ui_version):

        class NewAppConfig(AppConfig):
            if prefix:
                OPENAPI_URL_PREFIX = prefix
            if json_path:
                OPENAPI_JSON_PATH = json_path
            if redoc_path:
                OPENAPI_REDOC_PATH = redoc_path
            if swagger_ui_path:
                OPENAPI_SWAGGER_UI_PATH = swagger_ui_path
            if swagger_ui_version:
                OPENAPI_SWAGGER_UI_VERSION = swagger_ui_version

        app.config.from_object(NewAppConfig)
        Api(app)
        client = app.test_client()
        response_json_docs = client.get('/docs_url_prefix/openapi.json')
        response_redoc = client.get('/docs_url_prefix/redoc')
        response_swagger_ui = client.get('/docs_url_prefix/swagger-ui')
        if app.config.get('OPENAPI_URL_PREFIX') is None:
            assert response_json_docs.status_code == 404
            assert response_redoc.status_code == 404
            assert response_swagger_ui.status_code == 404
        else:
            assert response_json_docs.json['info'] == {
                'version': '1', 'title': 'API Test'}
            if app.config.get('OPENAPI_REDOC_PATH') is None:
                assert response_redoc.status_code == 404
            else:
                assert response_redoc.status_code == 200
                assert (response_redoc.headers['Content-Type'] ==
                        'text/html; charset=utf-8')
            if (app.config.get('OPENAPI_SWAGGER_UI_PATH') is None or
                    app.config.get('OPENAPI_SWAGGER_UI_VERSION') is None):
                assert response_swagger_ui.status_code == 404
            else:
                assert response_swagger_ui.status_code == 200
                assert (response_swagger_ui.headers['Content-Type'] ==
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
