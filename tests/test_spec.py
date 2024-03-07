"""Test Api class"""

import http
import json
from unittest import mock

import pytest

import marshmallow as ma
from webargs.fields import DelimitedList

import yaml

from flask_smorest import Api, Blueprint
from flask_smorest import etag as fs_etag

from .conftest import AppConfig
from .utils import build_ref, get_headers, get_parameters, get_responses


class TestAPISpec:
    """Test APISpec class"""

    @pytest.mark.parametrize("openapi_version", ["2.0", "3.0.2"])
    def test_apispec_sets_produces_consumes(self, app, openapi_version):
        app.config["OPENAPI_VERSION"] = openapi_version
        api = Api(app)
        spec = api.spec.to_dict()

        if openapi_version == "2.0":
            assert spec["produces"] == [
                "application/json",
            ]
            assert spec["consumes"] == [
                "application/json",
            ]
        else:
            assert "produces" not in spec
            assert "consumes" not in spec

    @pytest.mark.parametrize("openapi_version", ["2.0", "3.0.2"])
    def test_apispec_correct_path_parameters_ordering(self, app, openapi_version):
        """Test path parameters are sorted from left to right.

        If this test is flaky it's considered a failure.
        """
        app.config["OPENAPI_VERSION"] = openapi_version
        api = Api(app)

        blp = Blueprint("pets", "pets", url_prefix="/pets")

        @blp.route("/project/<project_id>/upload/<part_id>/complete")
        def do_nothing():
            return

        api.register_blueprint(blp)

        sorted_params = list(api.spec.to_dict()["paths"].values())[0]["parameters"]
        assert sorted_params[0]["name"] == "project_id"
        assert sorted_params[1]["name"] == "part_id"

    @pytest.mark.parametrize("openapi_version", ["2.0", "3.0.2"])
    def test_apispec_lazy_registers_error_responses(self, app, openapi_version):
        """Test error responses are registered"""
        app.config["OPENAPI_VERSION"] = openapi_version
        api = Api(app)

        # Declare a dummy response to ensure get_response doesn't fail
        response_1 = {"description": "Response 1"}
        api.spec.components.response("Response_1", response_1)

        # No route registered -> default errors not registered
        responses = get_responses(api.spec)
        for status in http.HTTPStatus:
            assert status.name not in responses

        # Register routes with all error responses
        blp = Blueprint("test", "test", url_prefix="/test")

        for status in http.HTTPStatus:

            @blp.route(f"/{status.name}")
            @blp.alt_response(400, status.name)
            def test(val):
                pass

        api.register_blueprint(blp)

        # Errors are now registered
        for status in http.HTTPStatus:
            response = responses[status.name]
            assert response["description"] == status.phrase
            empty_body = (100 <= status < 200) or status in (204, 304)
            if openapi_version == "2.0":
                if empty_body:
                    assert "schema" not in response
                else:
                    assert response["schema"] == build_ref(api.spec, "schema", "Error")
            else:
                if empty_body:
                    assert "content" not in response
                else:
                    assert response["content"] == {
                        "application/json": {
                            "schema": build_ref(api.spec, "schema", "Error")
                        }
                    }

    @pytest.mark.parametrize("openapi_version", ["2.0", "3.0.2"])
    def test_apispec_lazy_registers_etag_headers(self, app, openapi_version):
        """Test etag headers are registered"""
        app.config["OPENAPI_VERSION"] = openapi_version
        api = Api(app)

        # Declare dummy components to ensure get_* don't fail
        if openapi_version == "3.0.2":
            header_1 = {"description": "Header 1"}
            api.spec.components.header("Header_1", header_1)
        parameter_1 = {"description": "Parameter 1"}
        api.spec.components.parameter("Parameter_1", "header", parameter_1)

        # No route registered -> etag headers not registered
        if openapi_version == "3.0.2":
            headers = get_headers(api.spec)
            assert headers == {"Header_1": header_1}
        parameters = get_parameters(api.spec)
        assert parameters == {
            "Parameter_1": {**parameter_1, "in": "header", "name": "Parameter_1"}
        }

        # Register routes with etag
        blp = Blueprint("test", "test", url_prefix="/test")

        @blp.route("/etag_get", methods=["GET"])
        @blp.etag
        @blp.response(200)
        def test_get(val):
            pass

        @blp.route("/etag_pet", methods=["PUT"])
        @blp.etag
        @blp.response(200)
        def test_put(val):
            pass

        api.register_blueprint(blp)

        if openapi_version == "3.0.2":
            headers = get_headers(api.spec)
            assert headers["ETAG"] == fs_etag.ETAG_HEADER
        parameters = get_parameters(api.spec)
        assert parameters["IF_NONE_MATCH"] == fs_etag.IF_NONE_MATCH_HEADER
        assert parameters["IF_MATCH"] == fs_etag.IF_MATCH_HEADER

    def test_apispec_lazy_registers_pagination_header(self, app):
        """Test pagination header is registered"""
        api = Api(app)

        # Declare dummy header to ensure get_headers doesn't fail
        header_1 = {"description": "Header 1"}
        api.spec.components.header("Header_1", header_1)

        # No route registered -> parameter header not registered
        headers = get_headers(api.spec)
        assert headers == {"Header_1": header_1}

        # Register routes with pagination
        blp = Blueprint("test", "test", url_prefix="/test")

        @blp.route("/")
        @blp.response(200)
        @blp.paginate()
        def test_get(val):
            pass

        api.register_blueprint(blp)

        headers = get_headers(api.spec)
        assert headers["PAGINATION"] == {
            "description": "Pagination metadata",
            "schema": {"$ref": "#/components/schemas/PaginationMetadata"},
        }

    @pytest.mark.parametrize("openapi_version", ("2.0", "3.0.2"))
    def test_apispec_delimited_list_documentation(self, app, openapi_version):
        """Test DelimitedList if correctly documented"""
        app.config["OPENAPI_VERSION"] = openapi_version
        api = Api(app)

        blp = Blueprint("test", "test", url_prefix="/test")

        class ListInputsSchema(ma.Schema):
            inputs = DelimitedList(ma.fields.Integer)

        @blp.route("/")
        @blp.arguments(ListInputsSchema, location="query")
        def test(args):
            # Also test DelimitedList behaves as expected
            assert args == {"inputs": [1, 2, 3]}
            return "OK"

        api.register_blueprint(blp)
        spec = api.spec.to_dict()
        parameters = spec["paths"]["/test/"]["get"]["parameters"]
        param = next(p for p in parameters if p["name"] == "inputs")
        if openapi_version == "2.0":
            assert param["type"] == "array"
            assert param["items"] == {"type": "integer"}
            assert param["collectionFormat"] == "csv"
        else:
            assert param["schema"] == {"type": "array", "items": {"type": "integer"}}
            assert param["explode"] is False
            assert param["style"] == "form"

        client = app.test_client()
        client.get("/test/", query_string={"inputs": "1,2,3"})


class TestAPISpecServeDocs:
    """Test APISpec class doc-serving features"""

    @pytest.mark.parametrize(
        "prefix",
        (
            None,
            "docs_url_prefix",
            "/docs_url_prefix",
            "docs_url_prefix/",
            "/docs_url_prefix/",
        ),
    )
    def test_apispec_serve_spec_prefix(self, app, prefix):
        """Test url prefix default value and leading/trailing slashes issues"""

        class NewAppConfig(AppConfig):
            if prefix is not None:
                OPENAPI_URL_PREFIX = prefix

        app.config.from_object(NewAppConfig)
        Api(app)
        client = app.test_client()
        resp_json_docs = client.get("/docs_url_prefix/openapi.json")
        if app.config.get("OPENAPI_URL_PREFIX") is None:
            assert resp_json_docs.status_code == 404
        else:
            assert resp_json_docs.json["info"] == {"version": "1", "title": "API Test"}

    @pytest.mark.parametrize("prefix", (None, "docs_url_prefix"))
    @pytest.mark.parametrize("json_path", (None, "spec.json"))
    def test_apispec_serve_spec_json_path(self, app, prefix, json_path):
        class NewAppConfig(AppConfig):
            if prefix is not None:
                OPENAPI_URL_PREFIX = prefix
            if json_path is not None:
                OPENAPI_JSON_PATH = json_path

        app.config.from_object(NewAppConfig)
        Api(app)
        client = app.test_client()
        resp_json_docs_default = client.get("/docs_url_prefix/openapi.json")
        resp_json_docs_custom = client.get("/docs_url_prefix/spec.json")
        if app.config.get("OPENAPI_URL_PREFIX") is None:
            assert resp_json_docs_default.status_code == 404
            assert resp_json_docs_custom.status_code == 404
        else:
            if json_path is None:
                assert resp_json_docs_default.json["info"] == (
                    {"version": "1", "title": "API Test"}
                )
                assert resp_json_docs_custom.status_code == 404
            else:
                assert resp_json_docs_custom.json["info"] == (
                    {"version": "1", "title": "API Test"}
                )
                assert resp_json_docs_default.status_code == 404

    @pytest.mark.parametrize("prefix", (None, "docs_url_prefix"))
    @pytest.mark.parametrize("redoc_path", (None, "redoc"))
    @pytest.mark.parametrize("redoc_url", (None, "https://my-redoc/"))
    def test_apispec_serve_spec_redoc(self, app, prefix, redoc_path, redoc_url):
        class NewAppConfig(AppConfig):
            if prefix is not None:
                OPENAPI_URL_PREFIX = prefix
            if redoc_path is not None:
                OPENAPI_REDOC_PATH = redoc_path
            if redoc_url is not None:
                OPENAPI_REDOC_URL = redoc_url

        title_tag = "<title>API Test</title>"
        app.config.from_object(NewAppConfig)
        Api(app)
        client = app.test_client()
        response_redoc = client.get("/docs_url_prefix/redoc")
        if app.config.get("OPENAPI_URL_PREFIX") is None:
            assert response_redoc.status_code == 404
        else:
            if (
                app.config.get("OPENAPI_REDOC_PATH") is None
                or app.config.get("OPENAPI_REDOC_URL") is None
            ):
                assert response_redoc.status_code == 404
            else:
                assert response_redoc.status_code == 200
                assert (
                    response_redoc.headers["Content-Type"] == "text/html; charset=utf-8"
                )
                assert title_tag in response_redoc.get_data(True)

    @pytest.mark.parametrize("prefix", (None, "docs_url_prefix"))
    @pytest.mark.parametrize("swagger_ui_path", (None, "swagger-ui"))
    @pytest.mark.parametrize("swagger_ui_url", (None, "https://my-swagger/"))
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

        title_tag = "<title>API Test</title>"
        app.config.from_object(NewAppConfig)
        Api(app)
        client = app.test_client()
        response_swagger_ui = client.get("/docs_url_prefix/swagger-ui")
        if app.config.get("OPENAPI_URL_PREFIX") is None:
            assert response_swagger_ui.status_code == 404
        else:
            if (
                app.config.get("OPENAPI_SWAGGER_UI_PATH") is None
                or app.config.get("OPENAPI_SWAGGER_UI_URL") is None
            ):
                assert response_swagger_ui.status_code == 404
            else:
                assert response_swagger_ui.status_code == 200
                assert (
                    response_swagger_ui.headers["Content-Type"]
                    == "text/html; charset=utf-8"
                )
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
            "var override_config = {"
            '"supportedSubmitMethods": ["get", "put", "post", "delete"]'
            "};"
        ) in response_swagger_ui.get_data(True)

    @pytest.mark.parametrize("prefix", (None, "docs_url_prefix"))
    @pytest.mark.parametrize("rapidoc_path", (None, "rapidoc"))
    @pytest.mark.parametrize("rapidoc_url", (None, "https://my-rapidoc/"))
    def test_apispec_serve_spec_rapidoc(self, app, prefix, rapidoc_path, rapidoc_url):
        class NewAppConfig(AppConfig):
            if prefix is not None:
                OPENAPI_URL_PREFIX = prefix
            if rapidoc_path is not None:
                OPENAPI_RAPIDOC_PATH = rapidoc_path
            if rapidoc_url is not None:
                OPENAPI_RAPIDOC_URL = rapidoc_url

        title_tag = "<title>API Test</title>"
        app.config.from_object(NewAppConfig)
        Api(app)
        client = app.test_client()
        response_rapidoc = client.get("/docs_url_prefix/rapidoc")
        if app.config.get("OPENAPI_URL_PREFIX") is None:
            assert response_rapidoc.status_code == 404
        else:
            if (
                app.config.get("OPENAPI_RAPIDOC_PATH") is None
                or app.config.get("OPENAPI_RAPIDOC_URL") is None
            ):
                assert response_rapidoc.status_code == 404
            else:
                assert response_rapidoc.status_code == 200
                assert (
                    response_rapidoc.headers["Content-Type"]
                    == "text/html; charset=utf-8"
                )
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

    @pytest.mark.parametrize("prefix", ("", "/"))
    @pytest.mark.parametrize("path", ("", "/"))
    @pytest.mark.parametrize("tested", ("json", "redoc", "swagger-ui", "rapidoc"))
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
            "json": "OPENAPI_JSON_PATH",
            "redoc": "OPENAPI_REDOC_PATH",
            "swagger-ui": "OPENAPI_SWAGGER_UI_PATH",
            "rapidoc": "OPENAPI_RAPIDOC_PATH",
        }
        setattr(NewAppConfig, mapping[tested], path)

        app.config.from_object(NewAppConfig)
        Api(app)
        client = app.test_client()
        if tested == "json":
            response_json_docs = client.get("/")
        else:
            response_json_docs = client.get("openapi.json")
            response_doc_page = client.get("/")
            assert response_doc_page.status_code == 200
            assert (
                response_doc_page.headers["Content-Type"] == "text/html; charset=utf-8"
            )
        assert response_json_docs.json["info"] == {"version": "1", "title": "API Test"}

    def test_apispec_serve_spec_preserve_order(self, app):
        app.config["OPENAPI_URL_PREFIX"] = "/api-docs"
        api = Api(app)
        client = app.test_client()

        # Add ordered stuff. This is invalid, but it will do for the test.
        paths = {f"/path_{i}": str(i) for i in range(20)}
        api.spec._paths = paths

        response_json_docs = client.get("/api-docs/openapi.json")
        assert response_json_docs.status_code == 200
        assert response_json_docs.json["paths"] == paths

    def test_multiple_apis_serve_separate_specs(self, app):
        client = app.test_client()

        for i in [1, 2]:
            app.config[f"V{i}_OPENAPI_URL_PREFIX"] = f"/v{i}-docs"
            app.config[f"V{i}_OPENAPI_RAPIDOC_PATH"] = "rapidoc/"
            app.config[f"V{i}_OPENAPI_RAPIDOC_URL"] = "/statid/rapidoc.js"
            app.config[f"V{i}_OPENAPI_REDOC_PATH"] = "/redoc/"
            app.config[f"V{i}_OPENAPI_SWAGGER_UI_URL"] = "/static/swagger-ui/"
            app.config[f"V{i}_OPENAPI_SWAGGER_UI_PATH"] = "/swagger/"
            app.config[f"V{i}_OPENAPI_REDOC_URL"] = "/static/redoc.js"
            app.config[f"V{i}_OPENAPI_REDOC_PATH"] = "/redoc/"
            api = Api(
                app,
                config_prefix=f"V{i}_",
                spec_kwargs={
                    "title": f"V{i}",
                    "version": f"{i}",
                    "openapi_version": "3.0.2",
                },
            )
            blp = Blueprint(f"test{i}", f"test{i}", url_prefix=f"/test-{i}")
            blp.route("/")(lambda: None)
            api.register_blueprint(blp)

        # Checking openapi.json

        json1 = client.get("/v1-docs/openapi.json").json
        json2 = client.get("/v2-docs/openapi.json").json

        # Should have a different info
        assert json1["info"]["title"] == "V1"
        assert json2["info"]["title"] == "V2"

        # One api's routes should not leak into other's
        assert "/test-1/" in json1["paths"]
        assert "/test-2/" not in json1["paths"]
        assert "/test-1/" not in json2["paths"]
        assert "/test-2/" in json2["paths"]

        # Checking RapiDoc

        assert "/v1-docs/openapi.json" in client.get("/v1-docs/rapidoc/").text
        assert "/v2-docs/openapi.json" in client.get("/v2-docs/rapidoc/").text

        # Checking Swagger

        assert "/v1-docs/openapi.json" in client.get("/v1-docs/swagger/").text
        assert "/v2-docs/openapi.json" in client.get("/v2-docs/swagger/").text

        # Checking ReDoc

        assert "/v1-docs/openapi.json" in client.get("/v1-docs/redoc/").text
        assert "/v2-docs/openapi.json" in client.get("/v2-docs/redoc/").text


class TestAPISpecCLICommands:
    """Test OpenAPI CLI commands"""

    @pytest.mark.parametrize(
        ("cmd", "deserialize_fn"),
        [
            pytest.param(
                "openapi print", json.loads, id="'openapi print' serializes to JSON"
            ),
            pytest.param(
                "openapi print -f json",
                json.loads,
                id="'openapi print  -f json' serializes to JSON",
            ),
            pytest.param(
                "openapi print --format=json",
                json.loads,
                id="'openapi print  --format=json' serializes to JSON",
            ),
            pytest.param(
                "openapi print -f yaml",
                lambda data: yaml.load(data, yaml.Loader),
                id="'openapi print -f yaml' serializes to YAML",
            ),
            pytest.param(
                "openapi print --format=yaml",
                lambda data: yaml.load(data, yaml.Loader),
                id="'openapi print --format=yaml' serializes to YAML",
            ),
        ],
    )
    def test_apispec_command_print(self, cmd, deserialize_fn, app):
        api = Api(app)
        result = app.test_cli_runner().invoke(args=cmd.split())
        assert result.exit_code == 0
        assert deserialize_fn(result.output) == api.spec.to_dict()

    @mock.patch("flask_smorest.spec.HAS_PYYAML", False)
    def test_apispec_command_print_output_yaml_no_yaml_module(self, app):
        Api(app)
        result = app.test_cli_runner().invoke(
            args=["openapi", "print", "--format=yaml"]
        )
        assert result.exit_code == 0
        assert result.output.startswith(
            "To use yaml output format, please install PyYAML module"
        )

    @pytest.mark.parametrize(
        ("cmd", "deserialize_fn"),
        [
            pytest.param(
                "openapi write", json.load, id="'openapi write' serializes to JSON"
            ),
            pytest.param(
                "openapi write -f json",
                json.load,
                id="'openapi write -f json' serializes to JSON",
            ),
            pytest.param(
                "openapi write --format=json",
                json.load,
                id="'openapi write --format=json' serializes to JSON",
            ),
            pytest.param(
                "openapi write -f yaml",
                lambda file: yaml.load(file, yaml.Loader),
                id="'openapi write --f yaml' serializes to YAML",
            ),
            pytest.param(
                "openapi write --format=yaml",
                lambda file: yaml.load(file, yaml.Loader),
                id="'openapi write --format=yaml' serializes to YAML",
            ),
        ],
    )
    def test_apispec_command_write(self, cmd, deserialize_fn, app, tmp_path):
        temp_file = tmp_path / "output"
        api = Api(app)

        result = app.test_cli_runner().invoke(args=cmd.split() + [str(temp_file)])
        assert result.exit_code == 0
        with open(temp_file, encoding="utf-8") as spec_file:
            assert deserialize_fn(spec_file) == api.spec.to_dict()

    @mock.patch("flask_smorest.spec.HAS_PYYAML", False)
    def test_apispec_command_write_output_yaml_no_yaml_module(self, app, tmp_path):
        temp_file = tmp_path / "output"
        Api(app)
        result = app.test_cli_runner().invoke(
            args=["openapi", "write", "--format=yaml", str(temp_file)]
        )
        assert result.exit_code == 0
        assert result.output.startswith(
            "To use yaml output format, please install PyYAML module"
        )

    def test_apispec_command_print_with_multiple_apis(self, app):
        spec_kwargs = {
            "version": "1",
            "openapi_version": "3.0.2",
        }
        Api(app, config_prefix="V1", spec_kwargs={**spec_kwargs, "title": "V1"})
        Api(app, config_prefix="V2", spec_kwargs={**spec_kwargs, "title": "V2"})

        assert (
            "Error:" in app.test_cli_runner().invoke(args=["openapi", "print"]).output
        )
        assert (
            "Error: "
            in app.test_cli_runner()
            .invoke(args=["openapi", "print", "--config-prefix=not_exist"])
            .output
        )

        ret_1 = app.test_cli_runner().invoke(
            args=["openapi", "print", "--config-prefix=v1"]
        )
        assert "V1" in ret_1.output
        assert "V2" not in ret_1.output
        ret_2 = app.test_cli_runner().invoke(
            args=["openapi", "print", "--config-prefix=v2"]
        )
        assert "V1" not in ret_2.output
        assert "V2" in ret_2.output

    def test_apispec_command_write_with_multiple_apis(self, app, tmp_path):
        temp_file1 = tmp_path / "output1"
        temp_file2 = tmp_path / "output2"

        spec_kwargs = {
            "version": "1",
            "openapi_version": "3.0.2",
        }
        Api(app, config_prefix="V1", spec_kwargs={**spec_kwargs, "title": "V1"})
        Api(app, config_prefix="V2", spec_kwargs={**spec_kwargs, "title": "V2"})

        assert (
            "Error: " in app.test_cli_runner().invoke(args=["openapi", "write"]).output
        )
        assert (
            "Error: "
            in app.test_cli_runner()
            .invoke(args=["openapi", "write", "--config-prefix=not_exist"])
            .output
        )

        app.test_cli_runner().invoke(
            args=["openapi", "write", "--config-prefix=v1", str(temp_file1)]
        )
        with open(temp_file1, encoding="utf-8") as spec_file1:
            content1 = spec_file1.read()
            assert "V1" in content1
            assert "V2" not in content1

        app.test_cli_runner().invoke(
            args=["openapi", "write", "--config-prefix=v2", str(temp_file2)]
        )
        with open(temp_file2, encoding="utf-8") as spec_file2:
            content2 = spec_file2.read()
            assert "V1" not in content2
            assert "V2" in content2

    def test_apispec_command_list_config_prefixes(self, app):
        spec_kwargs = {
            "version": "1",
            "openapi_version": "3.0.2",
        }
        Api(app, config_prefix="", spec_kwargs={**spec_kwargs, "title": ""})
        Api(app, config_prefix="V1", spec_kwargs={**spec_kwargs, "title": "V1"})
        Api(app, config_prefix="V2", spec_kwargs={**spec_kwargs, "title": "V2"})
        result = app.test_cli_runner().invoke(args=["openapi", "list-config-prefixes"])
        assert set(result.output.strip().splitlines()) == {'""', '"V1_"', '"V2_"'}
