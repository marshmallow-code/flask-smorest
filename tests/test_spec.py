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
    """Test APISpec class doc-serving features"""

    @pytest.mark.parametrize(
        'prefix',
        (
            None,
            'docs_url_prefix',
            '/docs_url_prefix',
            'docs_url_prefix/',
            '/docs_url_prefix/'
        )
    )
    def test_apispec_serve_spec_prefix(self, app, prefix):
        """Test url prefix default value and leading/trailing slashes issues"""
        class NewAppConfig(AppConfig):
            if prefix is not None:
                OPENAPI_URL_PREFIX = prefix

        app.config.from_object(NewAppConfig)
        Api(app)
        client = app.test_client()
        resp_json_docs = client.get('/docs_url_prefix/openapi.json')
        if app.config.get('OPENAPI_URL_PREFIX') is None:
            assert resp_json_docs.status_code == 404
        else:
            assert resp_json_docs.json['info'] == {
                'version': '1', 'title': 'API Test'}

    @pytest.mark.parametrize('prefix', (None, 'docs_url_prefix'))
    @pytest.mark.parametrize('json_path', (None, 'spec.json'))
    def test_apispec_serve_spec_json_path(self, app, prefix, json_path):
        class NewAppConfig(AppConfig):
            if prefix is not None:
                OPENAPI_URL_PREFIX = prefix
            if json_path is not None:
                OPENAPI_JSON_PATH = json_path

        app.config.from_object(NewAppConfig)
        Api(app)
        client = app.test_client()
        resp_json_docs_default = client.get('/docs_url_prefix/openapi.json')
        resp_json_docs_custom = client.get('/docs_url_prefix/spec.json')
        if app.config.get('OPENAPI_URL_PREFIX') is None:
            assert resp_json_docs_default.status_code == 404
            assert resp_json_docs_custom.status_code == 404
        else:
            if json_path is None:
                assert resp_json_docs_default.json['info'] == (
                    {'version': '1', 'title': 'API Test'}
                )
                assert resp_json_docs_custom.status_code == 404
            else:
                assert resp_json_docs_custom.json['info'] == (
                    {'version': '1', 'title': 'API Test'}
                )
                assert resp_json_docs_default.status_code == 404

    @pytest.mark.parametrize('prefix', (None, 'docs_url_prefix'))
    @pytest.mark.parametrize('redoc_path', (None, 'redoc'))
    @pytest.mark.parametrize('redoc_url', (None, 'https://my-redoc/'))
    def test_apispec_serve_spec_redoc(
            self, app, prefix, redoc_path, redoc_url
    ):
        class NewAppConfig(AppConfig):
            if prefix is not None:
                OPENAPI_URL_PREFIX = prefix
            if redoc_path is not None:
                OPENAPI_REDOC_PATH = redoc_path
            if redoc_url is not None:
                OPENAPI_REDOC_URL = redoc_url

        title_tag = '<title>API Test</title>'
        app.config.from_object(NewAppConfig)
        Api(app)
        client = app.test_client()
        response_redoc = client.get('/docs_url_prefix/redoc')
        if app.config.get('OPENAPI_URL_PREFIX') is None:
            assert response_redoc.status_code == 404
        else:
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

    @pytest.mark.parametrize('prefix', (None, 'docs_url_prefix'))
    @pytest.mark.parametrize('swagger_ui_path', (None, 'swagger-ui'))
    @pytest.mark.parametrize('swagger_ui_url', (None, 'https://my-swagger/'))
    def test_apispec_serve_spec_swagger_ui(
            self, app, prefix, swagger_ui_path, swagger_ui_url
    ):
        class NewAppConfig(AppConfig):
            if prefix is not None:
                OPENAPI_URL_PREFIX = prefix
            if swagger_ui_path is not None:
                OPENAPI_SWAGGER_UI_PATH = swagger_ui_path
            if swagger_ui_url is not None:
                OPENAPI_SWAGGER_UI_URL = swagger_ui_url

        title_tag = '<title>API Test</title>'
        app.config.from_object(NewAppConfig)
        Api(app)
        client = app.test_client()
        response_swagger_ui = client.get('/docs_url_prefix/swagger-ui')
        if app.config.get('OPENAPI_URL_PREFIX') is None:
            assert response_swagger_ui.status_code == 404
        else:
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

    def test_apispec_serve_spec_swagger_ui_config(self, app):
        class NewAppConfig(AppConfig):
            OPENAPI_URL_PREFIX = "/"
            OPENAPI_SWAGGER_UI_PATH = "/"
            OPENAPI_SWAGGER_UI_URL = "https://domain.tld/swagger-ui"
            OPENAPI_SWAGGER_UI_CONFIG = {
                "supportedSubmitMethods": ["get", "put", "post", "delete"],
            }

        app.config.from_object(NewAppConfig)
        Api(app)
        client = app.test_client()
        response_swagger_ui = client.get("/")
        assert (
            'var override_config = {'
            '"supportedSubmitMethods": ["get", "put", "post", "delete"]'
            '};'
        ) in response_swagger_ui.get_data(True)

    @pytest.mark.parametrize('prefix', (None, 'docs_url_prefix'))
    @pytest.mark.parametrize('rapidoc_path', (None, 'rapidoc'))
    @pytest.mark.parametrize('rapidoc_url', (None, 'https://my-rapidoc/'))
    def test_apispec_serve_spec_rapidoc(
            self, app, prefix, rapidoc_path, rapidoc_url
    ):
        class NewAppConfig(AppConfig):
            if prefix is not None:
                OPENAPI_URL_PREFIX = prefix
            if rapidoc_path is not None:
                OPENAPI_RAPIDOC_PATH = rapidoc_path
            if rapidoc_url is not None:
                OPENAPI_RAPIDOC_URL = rapidoc_url

        title_tag = '<title>API Test</title>'
        app.config.from_object(NewAppConfig)
        Api(app)
        client = app.test_client()
        response_rapidoc = client.get('/docs_url_prefix/rapidoc')
        if app.config.get('OPENAPI_URL_PREFIX') is None:
            assert response_rapidoc.status_code == 404
        else:
            if (
                    app.config.get('OPENAPI_RAPIDOC_PATH') is None or
                    app.config.get('OPENAPI_RAPIDOC_URL') is None
            ):
                assert response_rapidoc.status_code == 404
            else:
                assert response_rapidoc.status_code == 200
                assert (response_rapidoc.headers['Content-Type'] ==
                        'text/html; charset=utf-8')
                assert title_tag in response_rapidoc.get_data(True)

    def test_apispec_serve_spec_rapidoc_config(self, app):
        class NewAppConfig(AppConfig):
            OPENAPI_URL_PREFIX = "/"
            OPENAPI_RAPIDOC_PATH = "/"
            OPENAPI_RAPIDOC_URL = "https://domain.tld/rapidoc"
            OPENAPI_RAPIDOC_CONFIG = {"theme": "dark"}

        app.config.from_object(NewAppConfig)
        Api(app)
        client = app.test_client()
        response_rapidoc = client.get("/")
        assert 'theme = "dark"' in response_rapidoc.get_data(True)

    @pytest.mark.parametrize('prefix', ('', '/'))
    @pytest.mark.parametrize('path', ('', '/'))
    @pytest.mark.parametrize(
        'tested',
        ('json', 'redoc', 'swagger-ui', 'rapidoc')
    )
    def test_apispec_serve_spec_empty_path(self, app, prefix, path, tested):
        """Test empty string or (equivalently) single slash as paths

        Documentation can be served at root of application.
        """

        class NewAppConfig(AppConfig):
            OPENAPI_URL_PREFIX = prefix
            OPENAPI_REDOC_URL = "https://domain.tld/redoc"
            OPENAPI_SWAGGER_UI_URL = "https://domain.tld/swagger-ui"
            OPENAPI_RAPIDOC_URL = "https://domain.tld/rapidoc"

        mapping = {
            'json': 'OPENAPI_JSON_PATH',
            'redoc': 'OPENAPI_REDOC_PATH',
            'swagger-ui': 'OPENAPI_SWAGGER_UI_PATH',
            'rapidoc': 'OPENAPI_RAPIDOC_PATH',
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
