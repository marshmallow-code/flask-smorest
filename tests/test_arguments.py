"""Test ArgumentsMixin"""

import http
import io
import json

import pytest

import marshmallow as ma

from flask_smorest import Api, Blueprint
from flask_smorest.fields import Upload

from .utils import build_ref, get_responses

LOCATIONS_MAPPING = {
    "querystring": "query",
    "query": "query",
    "json": "body",
    "form": "formData",
    "headers": "header",
    "files": "formData",
}

REQUEST_BODY_CONTENT_TYPE = {
    "json": "application/json",
    "form": "application/x-www-form-urlencoded",
    "files": "multipart/form-data",
}


class TestArguments:
    """Test ArgumentsMixin"""

    @pytest.mark.parametrize("openapi_version", ("2.0", "3.0.2"))
    @pytest.mark.parametrize(
        # Also test 'json/body' is default
        "location_map",
        list(LOCATIONS_MAPPING.items()) + [(None, "body")],
    )
    def test_arguments_location(self, app, schemas, location_map, openapi_version):
        app.config["OPENAPI_VERSION"] = openapi_version
        api = Api(app)
        blp = Blueprint("test", __name__, url_prefix="/test")
        location, openapi_location = location_map

        if location is not None:

            @blp.route("/")
            @blp.arguments(schemas.DocSchema, location=location)
            def func():
                """Dummy view func"""

        else:

            @blp.route("/")
            @blp.arguments(schemas.DocSchema)
            def func():
                """Dummy view func"""

        location = location or "json"

        api.register_blueprint(blp)
        spec = api.spec.to_dict()
        get = spec["paths"]["/test/"]["get"]
        if openapi_version == "3.0.2" and location in REQUEST_BODY_CONTENT_TYPE:
            assert "parameters" not in get
            assert "requestBody" in get
            assert len(get["requestBody"]["content"]) == 1
            assert REQUEST_BODY_CONTENT_TYPE[location] in get["requestBody"]["content"]
        else:
            loc = get["parameters"][0]["in"]
            assert loc == openapi_location
            assert "requestBody" not in get
            if location in REQUEST_BODY_CONTENT_TYPE and location != "json":
                assert get["consumes"] == [REQUEST_BODY_CONTENT_TYPE[location]]
            else:
                assert "consumes" not in get

    @pytest.mark.parametrize("openapi_version", ("2.0", "3.0.2"))
    @pytest.mark.parametrize("location", REQUEST_BODY_CONTENT_TYPE.keys())
    @pytest.mark.parametrize("content_type", ("application/x-custom", None))
    def test_arguments_content_type(
        self, app, schemas, location, content_type, openapi_version
    ):
        app.config["OPENAPI_VERSION"] = openapi_version
        api = Api(app)
        blp = Blueprint("test", __name__, url_prefix="/test")
        content_type = content_type or REQUEST_BODY_CONTENT_TYPE[location]

        @blp.route("/")
        @blp.arguments(schemas.DocSchema, location=location, content_type=content_type)
        def func():
            """Dummy view func"""

        api.register_blueprint(blp)
        spec = api.spec.to_dict()
        get = spec["paths"]["/test/"]["get"]
        if openapi_version == "3.0.2":
            assert len(get["requestBody"]["content"]) == 1
            assert content_type in get["requestBody"]["content"]
        else:
            if content_type != "application/json":
                assert get["consumes"] == [content_type]
            else:
                assert "consumes" not in get

    @pytest.mark.parametrize("openapi_version", ("2.0", "3.0.2"))
    @pytest.mark.parametrize("location", LOCATIONS_MAPPING.keys())
    @pytest.mark.parametrize("required", (True, False, None))
    def test_arguments_required(
        self, app, schemas, required, location, openapi_version
    ):
        app.config["OPENAPI_VERSION"] = openapi_version
        api = Api(app)
        blp = Blueprint("test", __name__, url_prefix="/test")

        if required is None:

            @blp.route("/")
            @blp.arguments(schemas.DocSchema, location=location)
            def func():
                pass

        else:

            @blp.route("/")
            @blp.arguments(schemas.DocSchema, required=required, location=location)
            def func():
                pass

        api.register_blueprint(blp)
        get = api.spec.to_dict()["paths"]["/test/"]["get"]
        # OAS3 / json, form, files
        if openapi_version == "3.0.2" and location in REQUEST_BODY_CONTENT_TYPE:
            # Body parameter in 'requestBody'
            assert "requestBody" in get
            # Check required defaults to True
            assert get["requestBody"]["required"] == (required is not False)
        # OAS2 / json
        elif location == "json":
            parameters = get["parameters"]
            # One parameter: the schema
            assert len(parameters) == 1
            assert "schema" in parameters[0]
            assert "requestBody" not in get
            # Check required defaults to True
            assert parameters[0]["required"] == (required is not False)
        # OAS2-3 / all
        else:
            parameters = get["parameters"]
            # One parameter: the 'field' field in DocSchema
            assert len(parameters) == 1
            assert parameters[0]["name"] == "field"
            assert "requestBody" not in get
            # Check the required parameter has no impact.
            # Only the required attribute of the field matters
            assert parameters[0]["required"] is False

    @pytest.mark.parametrize("openapi_version", ("2.0", "3.0.2"))
    @pytest.mark.parametrize("location", LOCATIONS_MAPPING.keys())
    @pytest.mark.parametrize("description", ("Description", None))
    def test_arguments_description(
        self, app, schemas, description, location, openapi_version
    ):
        app.config["OPENAPI_VERSION"] = openapi_version
        api = Api(app)
        blp = Blueprint("test", __name__, url_prefix="/test")

        @blp.route("/")
        @blp.arguments(schemas.DocSchema, description=description, location=location)
        def func():
            pass

        api.register_blueprint(blp)
        get = api.spec.to_dict()["paths"]["/test/"]["get"]
        # OAS3 / json, form, files
        if openapi_version == "3.0.2" and location in REQUEST_BODY_CONTENT_TYPE:
            # Body parameter in 'requestBody'
            assert "requestBody" in get
            if description is not None:
                assert get["requestBody"]["description"] == description
            else:
                assert "description" not in get["requestBody"]
        # OAS2 / json
        elif location == "json":
            parameters = get["parameters"]
            # One parameter: the schema
            assert len(parameters) == 1
            assert "schema" in parameters[0]
            assert "requestBody" not in get
            if description is not None:
                assert parameters[0]["description"] == description
            else:
                assert "description" not in parameters[0]
        # OAS2-3 / all
        else:
            parameters = get["parameters"]
            # One parameter: the 'field' field in DocSchema
            assert len(parameters) == 1
            assert parameters[0]["name"] == "field"
            assert "requestBody" not in get
            # Check the description parameter has no impact.
            # Only the description attribute of the field matters
            assert "description" not in parameters[0]

    @pytest.mark.parametrize("openapi_version", ("2.0", "3.0.2"))
    def test_arguments_multiple(self, app, schemas, openapi_version):
        app.config["OPENAPI_VERSION"] = openapi_version
        api = Api(app)
        blp = Blueprint("test", __name__, url_prefix="/test")
        client = app.test_client()

        @blp.route("/", methods=("POST",))
        @blp.arguments(schemas.DocSchema)
        @blp.arguments(schemas.QueryArgsSchema, location="query")
        def func(document, query_args):
            return {"document": document, "query_args": query_args}

        api.register_blueprint(blp)
        spec = api.spec.to_dict()

        # Check parameters are documented
        parameters = spec["paths"]["/test/"]["post"]["parameters"]
        assert parameters[0]["name"] == "arg1"
        assert parameters[0]["in"] == "query"
        assert parameters[1]["name"] == "arg2"
        assert parameters[1]["in"] == "query"

        if openapi_version == "2.0":
            assert len(parameters) == 3
            assert parameters[2]["in"] == "body"
            assert "schema" in parameters[2]
        else:
            assert len(parameters) == 2
            assert (
                "schema"
                in spec["paths"]["/test/"]["post"]["requestBody"]["content"][
                    "application/json"
                ]
            )

        # Check parameters are passed as arguments to view function
        item_data = {"field": 12}
        response = client.post(
            "/test/",
            data=json.dumps(item_data),
            content_type="application/json",
            query_string={"arg1": "test"},
        )
        assert response.status_code == 200
        assert response.json == {
            "document": {"db_field": 12},
            "query_args": {"arg1": "test"},
        }

    @pytest.mark.parametrize("openapi_version", ("2.0", "3.0.2"))
    def test_arguments_files_multipart(self, app, schemas, openapi_version):
        app.config["OPENAPI_VERSION"] = openapi_version
        api = Api(app)
        blp = Blueprint("test", __name__, url_prefix="/test")
        client = app.test_client()

        class MultipartSchema(ma.Schema):
            file_1 = Upload()
            file_2 = Upload()

        @blp.route("/", methods=["POST"])
        @blp.arguments(MultipartSchema, location="files")
        def func(files):
            return {
                "file_1": files["file_1"].read().decode(),
                "file_2": files["file_2"].read().decode(),
            }

        api.register_blueprint(blp)
        spec = api.spec.to_dict()

        files = {
            "file_1": (io.BytesIO(b"Test 1"), "file_1.txt"),
            "file_2": (io.BytesIO(b"Test 2"), "file_2.txt"),
        }

        response = client.post("/test/", data=files)
        assert response.json == {"file_1": "Test 1", "file_2": "Test 2"}

        if openapi_version == "2.0":
            for param in spec["paths"]["/test/"]["post"]["parameters"]:
                assert param["in"] == "formData"
                assert param["type"] == "file"
        else:
            assert spec["paths"]["/test/"]["post"]["requestBody"]["content"] == {
                "multipart/form-data": {
                    "schema": {"$ref": "#/components/schemas/Multipart"}
                }
            }
            assert spec["components"]["schemas"]["Multipart"] == {
                "type": "object",
                "properties": {
                    "file_1": {"type": "string", "format": "binary"},
                    "file_2": {"type": "string", "format": "binary"},
                },
            }

    # This is only relevant to OAS3.
    @pytest.mark.parametrize("openapi_version", ("3.0.2",))
    def test_arguments_examples(self, app, schemas, openapi_version):
        app.config["OPENAPI_VERSION"] = openapi_version
        api = Api(app)
        blp = Blueprint("test", __name__, url_prefix="/test")

        example = {"field": 12}
        examples = {"example 1": {"field": 12}, "example 2": {"field": 42}}

        @blp.route("/example")
        @blp.arguments(schemas.DocSchema, example=example)
        def func_example():
            """Dummy view func"""

        @blp.route("/examples")
        @blp.arguments(schemas.DocSchema, examples=examples)
        def func_examples():
            """Dummy view func"""

        api.register_blueprint(blp)
        spec = api.spec.to_dict()
        get = spec["paths"]["/test/example"]["get"]
        assert get["requestBody"]["content"]["application/json"]["example"] == example
        get = spec["paths"]["/test/examples"]["get"]
        assert get["requestBody"]["content"]["application/json"]["examples"] == examples

    @pytest.mark.parametrize("error_code", (403, 422, None))
    @pytest.mark.parametrize("openapi_version", ("2.0", "3.0.2"))
    def test_arguments_documents_error_response(
        self, app, schemas, openapi_version, error_code
    ):
        app.config["OPENAPI_VERSION"] = openapi_version
        api = Api(app)
        blp = Blueprint("test", __name__, url_prefix="/test")
        blp.ARGUMENTS_PARSER.DEFAULT_VALIDATION_STATUS = 400

        kwargs = {}
        if error_code:
            kwargs["error_status_code"] = error_code

        @blp.route("/")
        @blp.arguments(schemas.DocSchema, **kwargs)
        def func():
            """Dummy view func"""

        api.register_blueprint(blp)
        spec = api.spec.to_dict()
        error_code = error_code or 400
        assert spec["paths"]["/test/"]["get"]["responses"][
            str(error_code)
        ] == build_ref(api.spec, "response", http.HTTPStatus(error_code).name)
        assert http.HTTPStatus(error_code).name in get_responses(api.spec)
