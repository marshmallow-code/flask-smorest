"""Test Api class"""

from collections import OrderedDict
import json

import pytest

from flask_smorest import Api

from .conftest import AppConfig


class TestAPISpec:
    """Test APISpec class"""

    @pytest.mark.parametrize('openapi_version', ['2.0', '3.0.2'])
    def test_apispec_sets_produces_consumes(self, app, openapi_version):
        app.config['OPENAPI_VERSION'] = openapi_version
        api = Api(app)
        spec = api.spec.to_dict()

        if openapi_version == '2.0':
            assert spec['produces'] == ['application/json', ]
            assert spec['consumes'] == ['application/json', ]
        else:
            assert 'produces' not in spec
            assert 'consumes' not in spec

    def test_apispec_print_openapi_doc(self, app):
        api = Api(app)
        result = app.test_cli_runner().invoke(args=('openapi', 'print'))
        assert result.exit_code == 0
        assert json.loads(result.output) == api.spec.to_dict()

    def test_apispec_write_openapi_doc(self, app, tmp_path):
        output_file = tmp_path / 'openapi.json'
        api = Api(app)
        result = app.test_cli_runner().invoke(
            args=('openapi', 'write', str(output_file))
        )
        assert result.exit_code == 0
        with open(output_file) as output:
            assert json.loads(output.read()) == api.spec.to_dict()


class TestAPISpecServeDocs:
    """Test APISpec class docs serving features"""

    @pytest.mark.parametrize(
        'prefix', (None, 'docs_url_prefix', '/docs_url_prefix',
                   'docs_url_prefix/', '/docs_url_prefix/'))
    @pytest.mark.parametrize('json_path', (None, 'openapi.json'))
    @pytest.mark.parametrize('redoc_path', (None, 'redoc'))
    @pytest.mark.parametrize('redoc_url', (None, 'https://my-redoc/'))
    @pytest.mark.parametrize('swagger_ui_path', (None, 'swagger-ui'))
    @pytest.mark.parametrize('swagger_ui_url', (None, 'https://my-swagger/'))
    def test_apispec_serve_spec(
            self, app, prefix, json_path, redoc_path, redoc_url,
            swagger_ui_path, swagger_ui_url):
        """Test default values and leading/trailing slashes issues"""

        class NewAppConfig(AppConfig):
            if prefix is not None:
                OPENAPI_URL_PREFIX = prefix
            if json_path is not None:
                OPENAPI_JSON_PATH = json_path
            if redoc_path is not None:
                OPENAPI_REDOC_PATH = redoc_path
            if redoc_url is not None:
                OPENAPI_REDOC_URL = redoc_url
            if swagger_ui_path is not None:
                OPENAPI_SWAGGER_UI_PATH = swagger_ui_path
            if swagger_ui_url is not None:
                OPENAPI_SWAGGER_UI_URL = swagger_ui_url

        title_tag = '<title>API Test</title>'
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
            if (
                    app.config.get('OPENAPI_REDOC_PATH') is None or
                    app.config.get('OPENAPI_REDOC_URL') is None
            ):
                assert response_redoc.status_code == 404
            else:
                assert response_redoc.status_code == 200
                assert (response_redoc.headers['Content-Type'] ==
                        'text/html; charset=utf-8')
                assert title_tag in response_redoc.get_data(True)
            if (
                    app.config.get('OPENAPI_SWAGGER_UI_PATH') is None or
                    app.config.get('OPENAPI_SWAGGER_UI_URL') is None
            ):
                assert response_swagger_ui.status_code == 404
            else:
                assert response_swagger_ui.status_code == 200
                assert (response_swagger_ui.headers['Content-Type'] ==
                        'text/html; charset=utf-8')
                assert title_tag in response_swagger_ui.get_data(True)

    @pytest.mark.parametrize('prefix', ('', '/'))
    @pytest.mark.parametrize('path', ('', '/'))
    @pytest.mark.parametrize('tested', ('json', 'redoc', 'swagger-ui'))
    def test_apispec_serve_spec_empty_path(self, app, prefix, path, tested):
        """Test empty string or (equivalently) single slash as paths

        Documentation can be served at root of application.
        """

        class NewAppConfig(AppConfig):
            OPENAPI_URL_PREFIX = prefix
            OPENAPI_REDOC_URL = "https://domain.tld/redoc"
            OPENAPI_SWAGGER_UI_URL = "https://domain.tld/swagger-ui"

        mapping = {
            'json': 'OPENAPI_JSON_PATH',
            'redoc': 'OPENAPI_REDOC_PATH',
            'swagger-ui': 'OPENAPI_SWAGGER_UI_PATH',
        }
        setattr(NewAppConfig, mapping[tested], path)

        app.config.from_object(NewAppConfig)
        Api(app)
        client = app.test_client()
        if tested == 'json':
            response_json_docs = client.get('/')
        else:
            response_json_docs = client.get('openapi.json')
            response_doc_page = client.get('/')
            assert response_doc_page.status_code == 200
            assert (response_doc_page.headers['Content-Type'] ==
                    'text/html; charset=utf-8')
        assert response_json_docs.json['info'] == {
            'version': '1', 'title': 'API Test'}

    def test_apispec_serve_spec_preserve_order(self, app):
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
