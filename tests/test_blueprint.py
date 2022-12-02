"""Test Blueprint extra features"""

import io
import json
import http

import pytest

import marshmallow as ma

import flask
from flask.views import MethodView

from flask_smorest import Api, Blueprint, Page
from flask_smorest.fields import Upload

from .utils import build_ref, get_responses


LOCATIONS_MAPPING = (
    (
        "querystring",
        "query",
    ),
    (
        "query",
        "query",
    ),
    (
        "json",
        "body",
    ),
    (
        "form",
        "formData",
    ),
    (
        "headers",
        "header",
    ),
    (
        "files",
        "formData",
    ),
)

REQUEST_BODY_CONTENT_TYPE = {
    "json": "application/json",
    "form": "application/x-www-form-urlencoded",
    "files": "multipart/form-data",
}


class TestBlueprint:
    """Test Blueprint class"""

    @pytest.mark.parametrize("openapi_version", ("2.0", "3.0.2"))
    @pytest.mark.parametrize(
        # Also test 'json/body' is default
        "location_map",
        LOCATIONS_MAPPING + ((None, "body"),),
    )
    def test_blueprint_arguments_location(
        self, app, schemas, location_map, openapi_version
    ):
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
    def test_blueprint_arguments_content_type(
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
    def test_blueprint_register_with_custom_name_and_prefix(self, app, openapi_version):
        """Check blueprint can be registered with custom name and prefix

        Also check the doc is not modified by the first registration.
        """
        app.config["OPENAPI_VERSION"] = openapi_version
        blp = Blueprint("test", __name__)

        @blp.route("/")
        def func():
            pass

        api = Api(app)
        api.register_blueprint(blp, name="Test 1", url_prefix="/test_1")
        api.register_blueprint(blp, name="Test 2", url_prefix="/test_2")
        spec = api.spec.to_dict()

        # Check tags are correctly set and docs only differ by tags
        assert [t["name"] for t in spec["tags"]] == ["Test 1", "Test 2"]
        assert list(spec["paths"].keys()) == ["/test_1/", "/test_2/"]
        path_1 = spec["paths"]["/test_1/"]
        path_2 = spec["paths"]["/test_2/"]
        assert path_1["get"].pop("tags") == ["Test 1"]
        assert path_2["get"].pop("tags") == ["Test 2"]
        assert path_1 == path_2

    @pytest.mark.parametrize("openapi_version", ("2.0", "3.0.2"))
    @pytest.mark.parametrize("location_map", LOCATIONS_MAPPING)
    @pytest.mark.parametrize("required", (True, False, None))
    def test_blueprint_arguments_required(
        self, app, schemas, required, location_map, openapi_version
    ):
        app.config["OPENAPI_VERSION"] = openapi_version
        api = Api(app)
        blp = Blueprint("test", __name__, url_prefix="/test")
        location, _ = location_map

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
    @pytest.mark.parametrize("location_map", LOCATIONS_MAPPING)
    @pytest.mark.parametrize("description", ("Description", None))
    def test_blueprint_arguments_description(
        self, app, schemas, description, location_map, openapi_version
    ):
        app.config["OPENAPI_VERSION"] = openapi_version
        api = Api(app)
        blp = Blueprint("test", __name__, url_prefix="/test")
        location, _ = location_map

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
    def test_blueprint_arguments_multiple(self, app, schemas, openapi_version):
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
    def test_blueprint_dict_argument_schema(self, app, schemas, openapi_version):
        app.config["OPENAPI_VERSION"] = openapi_version
        api = Api(app)
        blp = Blueprint("test", __name__, url_prefix="/test")
        client = app.test_client()

        @blp.route("/", methods=("POST",))
        @blp.arguments(schemas.DictSchema)
        def func(document):
            return {"document": document}

        api.register_blueprint(blp)
        spec = api.spec.to_dict()

        # Check parameters are documented
        if openapi_version == "2.0":
            parameters = spec["paths"]["/test/"]["post"]["parameters"]
            assert len(parameters) == 1
            assert parameters[0]["in"] == "body"
            assert "schema" in parameters[0]
        else:
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
        )
        assert response.status_code == 200
        assert response.json == {
            "document": {"db_field": 12},
        }

    @pytest.mark.parametrize("openapi_version", ["2.0", "3.0.2"])
    def test_blueprint_dict_response_schema(self, app, schemas, openapi_version):
        """Check alt_response passes response transparently"""
        app.config["OPENAPI_VERSION"] = openapi_version
        api = Api(app)
        blp = Blueprint("test", "test", url_prefix="/test")
        client = app.test_client()

        @blp.route("/")
        @blp.response(200, schema=schemas.DictSchema)
        def func():
            return {"item_id": 12}

        api.register_blueprint(blp)

        resp = client.get("/test/")
        assert resp.json == {"item_id": 12}

    @pytest.mark.parametrize("openapi_version", ("2.0", "3.0.2"))
    def test_blueprint_arguments_files_multipart(self, app, schemas, openapi_version):
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
    def test_blueprint_arguments_examples(self, app, schemas, openapi_version):
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
    def test_blueprint_arguments_documents_error_response(
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

    @pytest.mark.parametrize("openapi_version", ("2.0", "3.0.2"))
    @pytest.mark.parametrize("decorate", (True, False))
    def test_blueprint_route_add_url_rule_parameters(
        self, app, openapi_version, decorate
    ):
        """Check path parameters docs are merged with auto docs"""
        app.config["OPENAPI_VERSION"] = openapi_version
        api = Api(app)
        blp = Blueprint("test", __name__, url_prefix="/test")

        if decorate:

            @blp.route(
                "/<int:item_id>",
                parameters=[
                    "TestParameter",
                    {"name": "item_id", "in": "path", "description": "Item ID"},
                ],
            )
            def get(item_id):
                pass

        else:

            def get(item_id):
                pass

            blp.add_url_rule(
                "/<int:item_id>",
                view_func=get,
                parameters=[
                    "TestParameter",
                    {"name": "item_id", "in": "path", "description": "Item ID"},
                ],
            )

        api.register_blueprint(blp)
        spec = api.spec.to_dict()
        params = spec["paths"]["/test/{item_id}"]["parameters"]
        assert len(params) == 2
        assert params[0] == build_ref(api.spec, "parameter", "TestParameter")
        assert params[1]["description"] == "Item ID"
        if openapi_version == "2.0":
            assert params[1]["type"] == "integer"
        else:
            assert params[1]["schema"]["type"] == "integer"

    @pytest.mark.parametrize("as_method_view", (True, False))
    def test_blueprint_route_path_parameter_default(self, app, as_method_view):
        api = Api(app)
        blp = Blueprint("test", __name__, url_prefix="/test")

        if as_method_view:

            @blp.route("/<int:user_id>")
            @blp.route("/", defaults={"user_id": 1})
            class Resource(MethodView):
                def get(self, user_id):
                    pass

        else:

            @blp.route("/<int:user_id>")
            @blp.route("/", defaults={"user_id": 1})
            def func(user_id):
                pass

        api.register_blueprint(blp)
        paths = api.spec.to_dict()["paths"]

        assert "parameters" not in paths["/test/"]
        assert paths["/test/{user_id}"]["parameters"][0]["name"] == "user_id"

    @pytest.mark.parametrize("as_method_view", (True, False))
    def test_blueprint_url_prefix_path_parameter(self, app, as_method_view):
        """Test registering a blueprint with path parameter in url_prefix

        Checks path parameters in url_prefix are correctly documented, even
        if registering the same Blueprint multiple times with a different url_prefix.
        """
        api = Api(app)
        blp = Blueprint("test", __name__, url_prefix="/<int:user_id>")

        if as_method_view:

            @blp.route("/")
            class Resource(MethodView):
                def get(self, user_id):
                    pass

        else:

            @blp.route("/")
            def func(user_id):
                pass

        api.register_blueprint(blp)
        api.register_blueprint(blp, url_prefix="/<int:team_id>", name="team")

        paths = api.spec.to_dict()["paths"]

        assert paths["/{user_id}/"]["parameters"][0]["name"] == "user_id"
        assert paths["/{team_id}/"]["parameters"][0]["name"] == "team_id"

    @pytest.mark.parametrize("openapi_version", ("2.0", "3.0.2"))
    def test_blueprint_url_prefix_register_blueprint_parameters(
        self, app, openapi_version
    ):
        """Check url_prefix path parameters docs are merged with auto docs"""
        app.config["OPENAPI_VERSION"] = openapi_version
        api = Api(app)
        blp = Blueprint("test", __name__, url_prefix="/<int:item_id>/")

        parameters = [
            "TestParameter",
            {"name": "item_id", "in": "path", "description": "Item ID"},
        ]

        @blp.route("/")
        def get(item_id):
            pass

        api.register_blueprint(blp, parameters=parameters)
        spec = api.spec.to_dict()
        params = spec["paths"]["/{item_id}/"]["parameters"]
        assert len(params) == 2
        assert params[0] == build_ref(api.spec, "parameter", "TestParameter")
        assert params[1]["description"] == "Item ID"
        if openapi_version == "2.0":
            assert params[1]["type"] == "integer"
        else:
            assert params[1]["schema"]["type"] == "integer"

    @pytest.mark.parametrize("openapi_version", ("2.0", "3.0.2"))
    def test_blueprint_route_multiple_methods(self, app, schemas, openapi_version):
        """Test calling route with multiple methods

        Checks the doc is properly deepcopied between methods
        """
        app.config["OPENAPI_VERSION"] = openapi_version
        api = Api(app)
        blp = Blueprint("test", __name__, url_prefix="/test")

        @blp.route(
            "/",
            methods=(
                "GET",
                "POST",
            ),
        )
        @blp.arguments(schemas.DocSchema)
        @blp.response(200, schemas.DocSchema)
        def func(document, query_args):
            pass

        api.register_blueprint(blp)
        spec = api.spec.to_dict()

        schema_ref = build_ref(api.spec, "schema", "Doc")
        for method in ("get", "post"):
            operation = spec["paths"]["/test/"][method]
            # Check parameters are documented
            if openapi_version == "2.0":
                parameter = operation["parameters"][0]
                assert parameter["in"] == "body"
                assert "schema" in parameter
            else:
                assert (
                    "schema" in operation["requestBody"]["content"]["application/json"]
                )
            # Check responses are documented
            response = operation["responses"]["200"]
            if openapi_version == "2.0":
                assert response["schema"] == schema_ref
            else:
                assert response["content"]["application/json"]["schema"] == schema_ref

    def test_blueprint_route_method_view_specify_methods(self, app):
        """Test calling route on MethodView specifying methods

        Checks only registered methods appear in the doc
        """
        api = Api(app)
        blp = Blueprint("test", __name__, url_prefix="/test")

        @blp.route(
            "/",
            methods=(
                "GET",
                "PUT",
            ),
        )
        class Resource(MethodView):
            def get(self):
                return "get"

            def post(self):
                return "post"

            def put(self):
                return "put"

        api.register_blueprint(blp)
        spec = api.spec.to_dict()

        client = app.test_client()
        assert client.get("test/").status_code == 200
        assert client.post("test/").status_code == 405
        assert client.put("test/").status_code == 200

        assert tuple(spec["paths"]["/test/"].keys()) == ("get", "put")

    def test_blueprint_route_tags(self, app):
        """Check passing tags to route"""
        blp = Blueprint("test", __name__, url_prefix="/test")

        @blp.route("/test_1/", tags=["Tag 1", "Tag 2"])
        def test_1():
            pass

        @blp.route("/test_2/")
        def test_2():
            pass

        api = Api(app)
        api.register_blueprint(blp)
        spec = api.spec.to_dict()

        assert spec["paths"]["/test/test_1/"]["get"]["tags"] == ["Tag 1", "Tag 2"]
        assert spec["paths"]["/test/test_2/"]["get"]["tags"] == [
            "test",
        ]

    @pytest.mark.parametrize("openapi_version", ["2.0", "3.0.2"])
    def test_blueprint_response_schema(self, app, openapi_version, schemas):
        """Check response schema is correctly documented.

        More specifically, check that:
        - plural response is documented as array in the spec
        - schema is document in the right place w.r.t. OpenAPI version
        """
        app.config["OPENAPI_VERSION"] = openapi_version
        api = Api(app)
        blp = Blueprint("test", "test", url_prefix="/test")

        @blp.route("/schema_many_false")
        @blp.response(200, schemas.DocSchema(many=False))
        def many_false():
            pass

        @blp.route("/schema_many_true")
        @blp.response(200, schemas.DocSchema(many=True))
        def many_true():
            pass

        api.register_blueprint(blp)

        paths = api.spec.to_dict()["paths"]

        schema_ref = build_ref(api.spec, "schema", "Doc")

        response = paths["/test/schema_many_false"]["get"]["responses"]["200"]
        if openapi_version == "2.0":
            assert response["schema"] == schema_ref
        else:
            assert response["content"]["application/json"]["schema"] == schema_ref

        response = paths["/test/schema_many_true"]["get"]["responses"]["200"]
        if openapi_version == "2.0":
            assert response["schema"]["items"] == schema_ref
        else:
            assert (
                response["content"]["application/json"]["schema"]["items"] == schema_ref
            )

    def test_blueprint_response_description(self, app):
        api = Api(app)
        blp = Blueprint("test", "test", url_prefix="/test")

        @blp.route("/route_1")
        @blp.response(204)
        def func_1():
            pass

        @blp.route("/route_2")
        @blp.response(204, description="Test")
        def func_2():
            pass

        api.register_blueprint(blp)

        get_1 = api.spec.to_dict()["paths"]["/test/route_1"]["get"]
        assert get_1["responses"]["204"]["description"] == http.HTTPStatus(204).phrase
        get_2 = api.spec.to_dict()["paths"]["/test/route_2"]["get"]
        assert get_2["responses"]["204"]["description"] == "Test"

    @pytest.mark.parametrize("openapi_version", ("2.0", "3.0.2"))
    def test_blueprint_response_example(self, app, openapi_version):
        app.config["OPENAPI_VERSION"] = openapi_version
        api = Api(app)
        blp = Blueprint("test", "test", url_prefix="/test")

        example = {"name": "One"}

        @blp.route("/")
        @blp.response(200, example=example)
        def func():
            pass

        api.register_blueprint(blp)

        get = api.spec.to_dict()["paths"]["/test/"]["get"]
        if openapi_version == "2.0":
            assert get["responses"]["200"]["examples"]["application/json"] == example
        else:
            assert (
                get["responses"]["200"]["content"]["application/json"]["example"]
                == example
            )

    # This is only relevant to OAS3.
    @pytest.mark.parametrize("openapi_version", ("3.0.2",))
    def test_blueprint_response_examples(self, app, openapi_version):
        app.config["OPENAPI_VERSION"] = openapi_version
        api = Api(app)
        blp = Blueprint("test", "test", url_prefix="/test")

        examples = {
            "example 1": {"summary": "Example 1", "value": {"name": "One"}},
            "example 2": {"summary": "Example 2", "value": {"name": "Two"}},
        }

        @blp.route("/")
        @blp.response(200, examples=examples)
        def func():
            pass

        api.register_blueprint(blp)

        get = api.spec.to_dict()["paths"]["/test/"]["get"]
        assert (
            get["responses"]["200"]["content"]["application/json"]["examples"]
            == examples
        )

    def test_blueprint_response_headers(self, app):
        api = Api(app)
        blp = Blueprint("test", "test", url_prefix="/test")

        headers = {"X-Header": {"description": "Custom header"}}

        @blp.route("/")
        @blp.response(200, headers=headers)
        def func():
            pass

        api.register_blueprint(blp)

        get = api.spec.to_dict()["paths"]["/test/"]["get"]
        assert get["responses"]["200"]["headers"] == headers

    @pytest.mark.parametrize("openapi_version", ("2.0", "3.0.2"))
    @pytest.mark.parametrize("content_type", ("application/x-custom", None))
    def test_blueprint_reponse_content_type(
        self, app, schemas, openapi_version, content_type
    ):
        app.config["OPENAPI_VERSION"] = openapi_version
        api = Api(app)
        blp = Blueprint("test", "test", url_prefix="/test")

        @blp.route("/")
        @blp.response(200, schemas.DocSchema, content_type=content_type)
        def func():
            pass

        api.register_blueprint(blp)

        get = api.spec.to_dict()["paths"]["/test/"]["get"]

        if openapi_version == "2.0":
            if content_type is not None:
                assert set(get["produces"]) == {
                    "application/json",
                    "application/x-custom",
                }
            else:
                assert "produces" not in get
        else:
            assert "produces" not in get
            assert get["responses"]["200"]["content"] == {
                content_type
                or "application/json": {"schema": build_ref(api.spec, "schema", "Doc")}
            }

    @pytest.mark.parametrize("default_error", ("default", "override", "None"))
    def test_blueprint_documents_default_error_response(self, app, default_error):
        class MyApi(Api):
            if default_error == "override":
                DEFAULT_ERROR_RESPONSE_NAME = "MY_DEFAULT_ERROR"
            elif default_error == "None":
                DEFAULT_ERROR_RESPONSE_NAME = None

        api = MyApi(app)
        blp = Blueprint("test", "test", url_prefix="/test")

        @blp.route("/")
        def func():
            pass

        api.register_blueprint(blp)

        get = api.spec.to_dict()["paths"]["/test/"]["get"]
        if default_error == "None":
            assert "responses" not in get
        else:
            error_response = {
                "default": "DEFAULT_ERROR",
                "override": "MY_DEFAULT_ERROR",
            }[default_error]
            assert get["responses"]["default"] == build_ref(
                api.spec, "response", error_response
            )

    @pytest.mark.parametrize("openapi_version", ["2.0", "3.0.2"])
    @pytest.mark.parametrize("schema_type", ["object", "ref"])
    def test_blueprint_alt_response(self, app, openapi_version, schemas, schema_type):
        """Check alternate response is correctly documented"""
        app.config["OPENAPI_VERSION"] = openapi_version
        api = Api(app)
        blp = Blueprint("test", "test", url_prefix="/test")

        example = {"error_id": "E1", "text": "client error"}
        examples = {
            "example 1": {"error_id": "E1", "text": "client error 1"},
            "example 2": {"error_id": "E2", "text": "client error 2"},
        }
        headers = {
            "X-Custom-Header": {
                "description": "Custom header",
                "schema": {"type": "integer"},
            }
        }

        if schema_type == "object":
            schema = schemas.ClientErrorSchema
        else:
            schema = "ClientError"

        @blp.route("/")
        @blp.alt_response(400, schema=schema)
        def func():
            pass

        @blp.route("/description")
        @blp.alt_response(400, schema=schema, description="Client error")
        def func_with_description():
            pass

        @blp.route("/example")
        @blp.alt_response(400, schema=schema, example=example)
        def func_with_example():
            pass

        if openapi_version == "3.0.2":

            @blp.route("/examples")
            @blp.alt_response(400, schema=schema, examples=examples)
            def func_with_examples():
                pass

        @blp.route("/headers")
        @blp.alt_response(400, schema=schema, headers=headers)
        def func_with_headers():
            pass

        @blp.route("/content_type")
        @blp.alt_response(400, schema=schema, content_type="application/x-custom")
        def func_with_content_type():
            pass

        api.register_blueprint(blp)

        paths = api.spec.to_dict()["paths"]

        schema_ref = build_ref(api.spec, "schema", "ClientError")

        response = paths["/test/"]["get"]["responses"]["400"]
        if openapi_version == "2.0":
            assert response["schema"] == schema_ref
        else:
            assert response["content"]["application/json"]["schema"] == schema_ref
        assert response["description"] == http.HTTPStatus(400).phrase

        response = paths["/test/description"]["get"]["responses"]["400"]
        assert response["description"] == "Client error"

        response = paths["/test/example"]["get"]["responses"]["400"]
        if openapi_version == "2.0":
            assert response["examples"]["application/json"] == example
        else:
            assert response["content"]["application/json"]["example"] == example

        if openapi_version == "3.0.2":
            response = paths["/test/examples"]["get"]["responses"]["400"]
            assert response["content"]["application/json"]["examples"] == examples

        response = paths["/test/headers"]["get"]["responses"]["400"]
        assert response["headers"] == headers

        get = paths["/test/content_type"]["get"]
        if openapi_version == "2.0":
            assert set(get["produces"]) == {"application/json", "application/x-custom"}
        else:
            assert "produces" not in get
        if openapi_version == "3.0.2":
            assert get["responses"]["400"]["content"] == {
                "application/x-custom": {"schema": schema_ref}
            }

    @pytest.mark.parametrize("openapi_version", ["2.0", "3.0.2"])
    def test_blueprint_alt_response_ref(self, app, openapi_version):
        """Check alternate response passed as reference"""
        app.config["OPENAPI_VERSION"] = openapi_version
        api = Api(app)
        api.spec.components.response("ClientErrorResponse")

        blp = Blueprint("test", "test", url_prefix="/test")

        @blp.route("/")
        @blp.alt_response(400, "ClientErrorResponse")
        def func():
            pass

        api.register_blueprint(blp)

        paths = api.spec.to_dict()["paths"]

        response_ref = build_ref(api.spec, "response", "ClientErrorResponse")

        assert paths["/test/"]["get"]["responses"]["400"] == response_ref

    @pytest.mark.parametrize("openapi_version", ["2.0", "3.0.2"])
    def test_blueprint_multiple_alt_response(self, app, openapi_version, schemas):
        """Check multiple nested calls to alt_response"""
        app.config["OPENAPI_VERSION"] = openapi_version
        api = Api(app)
        blp = Blueprint("test", "test", url_prefix="/test")

        @blp.route("/")
        @blp.alt_response(400, schema=schemas.ClientErrorSchema)
        @blp.alt_response(404, "NotFoundErrorResponse")
        def func():
            pass

        api.register_blueprint(blp)

        paths = api.spec.to_dict()["paths"]

        schema_ref = build_ref(api.spec, "schema", "ClientError")
        response_ref = build_ref(api.spec, "response", "NotFoundErrorResponse")

        response = paths["/test/"]["get"]["responses"]["400"]
        if openapi_version == "2.0":
            assert response["schema"] == schema_ref
        else:
            assert response["content"]["application/json"]["schema"] == schema_ref

        assert paths["/test/"]["get"]["responses"]["404"] == response_ref

    @pytest.mark.parametrize("openapi_version", ["2.0", "3.0.2"])
    def test_blueprint_alt_response_wrapper(self, app, schemas, openapi_version):
        """Check alt_response passes response transparently"""
        app.config["OPENAPI_VERSION"] = openapi_version
        api = Api(app)
        api.spec.components.response("ClientErrorResponse")

        blp = Blueprint("test", "test", url_prefix="/test")
        client = app.test_client()

        @blp.route("/")
        @blp.response(200, schema=schemas.DocSchema)
        @blp.alt_response(400, "ClientErrorResponse")
        def func():
            return {"item_id": 12}

        api.register_blueprint(blp)

        paths = api.spec.to_dict()["paths"]

        response_ref = build_ref(api.spec, "response", "ClientErrorResponse")

        assert paths["/test/"]["get"]["responses"]["400"] == response_ref

        resp = client.get("test/")
        assert resp.json == {"item_id": 12}

    @pytest.mark.parametrize("openapi_version", ["2.0", "3.0.2"])
    @pytest.mark.parametrize("success", (True, False))
    def test_blueprint_alt_response_success_response(
        self, app, schemas, openapi_version, success
    ):
        """Check alt_response documenting a success response"""
        app.config["OPENAPI_VERSION"] = openapi_version
        api = Api(app)

        blp = Blueprint("test", "test", url_prefix="/test")

        @blp.route("/")
        @blp.etag
        @blp.paginate()
        # response vs. alt_response order doesn't matter
        @blp.alt_response(201, success=success)
        @blp.response(200)
        @blp.alt_response(202, success=success)
        def func():
            pass

        api.register_blueprint(blp)

        paths = api.spec.to_dict()["paths"]
        responses = paths["/test/"]["get"]["responses"]

        response = responses["200"]
        assert "X-Pagination" in response["headers"]
        assert "ETag" in response["headers"]

        for response in (responses["201"], responses["202"]):
            if success:
                assert "X-Pagination" in response["headers"]
                assert "ETag" in response["headers"]
            else:
                assert "X-Pagination" not in response.get("headers", [])
                assert "ETag" not in response.get("headers", [])

    @pytest.mark.parametrize("openapi_version", ("2.0", "3.0.2"))
    def test_blueprint_pagination(self, app, schemas, openapi_version):
        app.config["OPENAPI_VERSION"] = openapi_version
        api = Api(app)
        blp = Blueprint("test", __name__, url_prefix="/test")

        @blp.route("/")
        @blp.arguments(schemas.QueryArgsSchema, location="query")
        @blp.paginate()
        def func():
            """Dummy view func"""

        api.register_blueprint(blp)
        spec = api.spec.to_dict()

        # Check parameters are documented
        parameters = spec["paths"]["/test/"]["get"]["parameters"]
        # Query string parameters
        assert parameters[0]["name"] == "arg1"
        assert parameters[0]["in"] == "query"
        assert parameters[1]["name"] == "arg2"
        assert parameters[1]["in"] == "query"
        # Page
        assert parameters[2]["name"] == "page"
        assert parameters[2]["in"] == "query"
        assert parameters[2]["required"] is False
        if openapi_version == "2.0":
            assert parameters[2]["type"] == "integer"
            assert parameters[2]["default"] == 1
            assert parameters[2]["minimum"] == 1
        else:
            assert parameters[2]["schema"]["type"] == "integer"
            assert parameters[2]["schema"]["default"] == 1
            assert parameters[2]["schema"]["minimum"] == 1
        # Page size
        assert parameters[3]["name"] == "page_size"
        assert parameters[3]["in"] == "query"
        assert parameters[3]["required"] is False
        if openapi_version == "2.0":
            assert parameters[3]["type"] == "integer"
            assert parameters[3]["default"] == 10
            assert parameters[3]["minimum"] == 1
            assert parameters[3]["maximum"] == 100
        else:
            assert parameters[3]["schema"]["type"] == "integer"
            assert parameters[3]["schema"]["default"] == 10
            assert parameters[3]["schema"]["minimum"] == 1
            assert parameters[3]["schema"]["maximum"] == 100

    @pytest.mark.parametrize("error_code", (400, 422))
    @pytest.mark.parametrize("openapi_version", ("2.0", "3.0.2"))
    def test_blueprint_pagination_documents_error_response(
        self, app, openapi_version, error_code
    ):
        app.config["OPENAPI_VERSION"] = openapi_version
        api = Api(app)
        blp = Blueprint("test", __name__, url_prefix="/test")
        blp.PAGINATION_ARGUMENTS_PARSER.DEFAULT_VALIDATION_STATUS = error_code

        @blp.route("/")
        @blp.paginate(Page)
        def func():
            """Dummy view func"""

        api.register_blueprint(blp)
        spec = api.spec.to_dict()
        assert spec["paths"]["/test/"]["get"]["responses"][
            str(error_code)
        ] == build_ref(api.spec, "response", http.HTTPStatus(error_code).name)

    def test_blueprint_doc_function(self, app):
        api = Api(app)
        blp = Blueprint("test", __name__, url_prefix="/test")
        client = app.test_client()

        @blp.route(
            "/",
            methods=(
                "PUT",
                "PATCH",
            ),
        )
        @blp.doc(summary="Dummy func", description="Do dummy stuff")
        def view_func():
            return {"Value": "OK"}

        api.register_blueprint(blp)
        spec = api.spec.to_dict()
        path = spec["paths"]["/test/"]
        for method in (
            "put",
            "patch",
        ):
            assert path[method]["summary"] == "Dummy func"
            assert path[method]["description"] == "Do dummy stuff"

        response = client.put("/test/")
        assert response.status_code == 200
        assert response.json == {"Value": "OK"}

    def test_blueprint_doc_method_view(self, app):
        api = Api(app)
        blp = Blueprint("test", __name__, url_prefix="/test")

        @blp.route("/")
        class Resource(MethodView):
            @blp.doc(summary="Dummy put", description="Do dummy put")
            def put(self):
                pass

            @blp.doc(summary="Dummy patch", description="Do dummy patch")
            def patch(self):
                pass

        api.register_blueprint(blp)
        spec = api.spec.to_dict()
        path = spec["paths"]["/test/"]
        for method in (
            "put",
            "patch",
        ):
            assert path[method]["summary"] == f"Dummy {method}"
            assert path[method]["description"] == f"Do dummy {method}"

    def test_blueprint_doc_called_twice(self, app):
        api = Api(app)
        blp = Blueprint("test", __name__, url_prefix="/test")

        @blp.route("/")
        @blp.doc(summary="Dummy func")
        @blp.doc(description="Do dummy stuff")
        def view_func():
            pass

        api.register_blueprint(blp)
        spec = api.spec.to_dict()
        path = spec["paths"]["/test/"]
        assert path["get"]["summary"] == "Dummy func"
        assert path["get"]["description"] == "Do dummy stuff"

    # Regression test for
    # https://github.com/marshmallow-code/flask-smorest/issues/19
    def test_blueprint_doc_merged_after_prepare_doc(self, app):
        app.config["OPENAPI_VERSION"] = "3.0.2"
        api = Api(app)
        blp = Blueprint("test", __name__, url_prefix="/test")

        # This is a dummy example. In real-life, use 'example' parameter.
        doc_example = {"content": {"application/json": {"example": {"test": 123}}}}

        class ItemSchema(ma.Schema):
            test = ma.fields.Int()

        @blp.route("/")
        class Resource(MethodView):
            @blp.doc(**{"requestBody": doc_example})
            @blp.doc(**{"responses": {200: doc_example}})
            @blp.arguments(ItemSchema)
            @blp.response(200, ItemSchema)
            def get(self):
                pass

        api.register_blueprint(blp)
        spec = api.spec.to_dict()
        get = spec["paths"]["/test/"]["get"]
        assert get["requestBody"]["content"]["application/json"]["example"] == {
            "test": 123
        }
        resp = get["responses"]["200"]
        assert resp["content"]["application/json"]["example"] == {"test": 123}
        assert "schema" in resp["content"]["application/json"]

    @pytest.mark.parametrize("status_code", (200, "200", http.HTTPStatus.OK))
    def test_blueprint_response_status_code_cast_to_string(self, app, status_code):
        api = Api(app)
        blp = Blueprint("test", __name__, url_prefix="/test")

        # This is a dummy example. In real-life, use 'description' parameter.
        doc_desc = {"description": "Description"}

        class ItemSchema(ma.Schema):
            test = ma.fields.Int()

        @blp.route("/")
        class Resource(MethodView):

            # When documenting a response, @blp.doc MUST use the same type
            # to express the status code as the one used in @blp.response.
            # (Default is 200 expressed as int.)
            @blp.doc(**{"responses": {status_code: doc_desc}})
            @blp.arguments(ItemSchema)
            @blp.response(status_code, ItemSchema)
            def get(self):
                pass

        api.register_blueprint(blp)
        spec = api.spec.to_dict()
        resp = spec["paths"]["/test/"]["get"]["responses"]["200"]
        assert resp["description"] == "Description"
        assert "schema" in resp["content"]["application/json"]

    @pytest.mark.parametrize("delimiter", (False, None, "---"))
    def test_blueprint_doc_info_from_docstring(self, app, delimiter):
        api = Api(app)

        class MyBlueprint(Blueprint):
            # Check delimiter default value
            if delimiter is not False:
                DOCSTRING_INFO_DELIMITER = delimiter

        blp = MyBlueprint("test", __name__, url_prefix="/test")

        @blp.route("/")
        class Resource(MethodView):
            def get(self):
                """Get summary"""

            def put(self):
                """Put summary

                Put description
                ---
                Private docstring
                """

            def patch(self):
                pass

        api.register_blueprint(blp)
        spec = api.spec.to_dict()
        path = spec["paths"]["/test/"]

        assert path["get"]["summary"] == "Get summary"
        assert "description" not in path["get"]
        assert path["put"]["summary"] == "Put summary"
        if delimiter is None:
            assert (
                path["put"]["description"] == "Put description\n---\nPrivate docstring"
            )
        else:
            assert path["put"]["description"] == "Put description"
        assert "summary" not in path["patch"]
        assert "description" not in path["patch"]

    @pytest.mark.parametrize(
        "http_methods",
        (
            ["OPTIONS", "HEAD", "GET", "POST", "PUT", "PATCH", "DELETE"],
            ["PUT", "PATCH", "DELETE", "OPTIONS", "HEAD", "GET", "POST"],
        ),
    )
    def test_blueprint_route_enforces_method_order_for_methodviews(
        self, app, http_methods
    ):
        api = Api(app)

        class MyBlueprint(Blueprint):
            HTTP_METHODS = http_methods

        blp = MyBlueprint("test", __name__, url_prefix="/test")

        @blp.route("/")
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
        methods = list(api.spec.to_dict()["paths"]["/test/"].keys())
        assert methods == [m.lower() for m in http_methods]

    @pytest.mark.parametrize(
        "http_methods",
        (
            ["OPTIONS", "HEAD", "GET", "POST", "PUT", "PATCH", "DELETE"],
            ["PUT", "PATCH", "DELETE", "OPTIONS", "HEAD", "GET", "POST"],
        ),
    )
    def test_blueprint_route_enforces_method_order_for_view_functions(
        self, app, http_methods
    ):
        api = Api(app)

        class MyBlueprint(Blueprint):
            HTTP_METHODS = http_methods

        blp = MyBlueprint("test", __name__, url_prefix="/test")

        @blp.route("/", methods=("GET", "PUT"))
        def func(self):
            pass

        api.register_blueprint(blp)
        methods = list(api.spec.to_dict()["paths"]["/test/"].keys())
        assert methods == [m.lower() for m in http_methods if m in ("GET", "PUT")]

    @pytest.mark.parametrize("as_method_view", (True, False))
    def test_blueprint_multiple_routes_per_view(self, app, as_method_view):
        api = Api(app)
        blp = Blueprint("test", __name__, url_prefix="/test")

        if as_method_view:
            # Blueprint.route ensures a different endpoint is used for each
            # route. Otherwise, this would break in Blueprint.route when
            # calling as_view for the second time with the same endpoint.
            @blp.route("/route_1")
            @blp.route("/route_2")
            class Resource(MethodView):
                def get(self):
                    pass

        else:

            @blp.route("/route_1")
            @blp.route("/route_2")
            def func():
                pass

        api.register_blueprint(blp)
        paths = api.spec.to_dict()["paths"]

        assert "get" in paths["/test/route_1"]
        assert "get" in paths["/test/route_2"]

    @pytest.mark.parametrize("as_method_view", (True, False))
    @pytest.mark.parametrize("endpoint", (None, "test"))
    def test_blueprint_add_url_rule(self, app, as_method_view, endpoint):
        api = Api(app)
        blp = Blueprint("test", __name__, url_prefix="/test")

        if as_method_view:

            class Resource(MethodView):
                def get(self):
                    pass

            blp.add_url_rule("/test", endpoint=endpoint, view_func=Resource)

        else:

            def func():
                pass

            blp.add_url_rule("/test", endpoint=endpoint, view_func=func)

        api.register_blueprint(blp)
        paths = api.spec.to_dict()["paths"]

        assert "get" in paths["/test/test"]
        assert "get" in paths["/test/test"]

    def test_blueprint_add_url_rule_without_view_func(self):
        blp = Blueprint("test", __name__, url_prefix="/test")
        with pytest.raises(TypeError, match="view_func must be provided"):
            blp.add_url_rule("/test", "dummy_endpoint")

    def test_blueprint_response_tuple(self, app):
        api = Api(app)
        blp = Blueprint("test", __name__, url_prefix="/test")
        client = app.test_client()

        @blp.route("/response")
        @blp.response(200)
        def func_response():
            return {}

        @blp.route("/response_code_int")
        @blp.response(200)
        def func_response_code_int():
            return {}, 201

        @blp.route("/response_code_str")
        @blp.response(200)
        def func_response_code_str():
            return {}, "201 CREATED"

        @blp.route("/response_headers")
        @blp.response(200)
        def func_response_headers():
            return {}, {"X-header": "test"}

        @blp.route("/response_code_int_headers")
        @blp.response(200)
        def func_response_code_int_headers():
            return {}, 201, {"X-header": "test"}

        @blp.route("/response_code_str_headers")
        @blp.response(200)
        def func_response_code_str_headers():
            return {}, "201 CREATED", {"X-header": "test"}

        @blp.route("/response_wrong_tuple")
        @blp.response(200)
        def func_response_wrong_tuple():
            return {}, 201, {"X-header": "test"}, "extra"

        @blp.route("/response_tuple_subclass")
        @blp.response(200)
        def func_response_tuple_subclass():
            class MyTuple(tuple):
                pass

            return MyTuple((1, 2))

        api.register_blueprint(blp)

        response = client.get("/test/response")
        assert response.status_code == 200
        assert response.json == {}
        response = client.get("/test/response_code_int")
        assert response.status_code == 201
        assert response.status == "201 CREATED"
        assert response.json == {}
        response = client.get("/test/response_code_str")
        assert response.status_code == 201
        assert response.status == "201 CREATED"
        assert response.json == {}
        response = client.get("/test/response_headers")
        assert response.status_code == 200
        assert response.json == {}
        assert response.headers["X-header"] == "test"
        response = client.get("/test/response_code_int_headers")
        assert response.status_code == 201
        assert response.status == "201 CREATED"
        assert response.json == {}
        assert response.headers["X-header"] == "test"
        response = client.get("/test/response_code_str_headers")
        assert response.status_code == 201
        assert response.status == "201 CREATED"
        assert response.json == {}
        assert response.headers["X-header"] == "test"
        response = client.get("/test/response_wrong_tuple")
        assert response.status_code == 500
        response = client.get("/test/response_tuple_subclass")
        assert response.status_code == 200
        assert response.json == [1, 2]

    def test_blueprint_pagination_response_tuple(self, app):
        api = Api(app)
        blp = Blueprint("test", __name__, url_prefix="/test")
        client = app.test_client()

        @blp.route("/response")
        @blp.response(200)
        @blp.paginate(Page)
        def func_response():
            return [1, 2]

        @blp.route("/response_code")
        @blp.response(200)
        @blp.paginate(Page)
        def func_response_code():
            return [1, 2], 201

        @blp.route("/response_headers")
        @blp.response(200)
        @blp.paginate(Page)
        def func_response_headers():
            return [1, 2], {"X-header": "test"}

        @blp.route("/response_code_headers")
        @blp.response(200)
        @blp.paginate(Page)
        def func_response_code_headers():
            return [1, 2], 201, {"X-header": "test"}

        @blp.route("/response_wrong_tuple")
        @blp.response(200)
        @blp.paginate(Page)
        def func_response_wrong_tuple():
            return [1, 2], 201, {"X-header": "test"}, "extra"

        @blp.route("/response_tuple_subclass")
        @blp.response(200)
        @blp.paginate(Page)
        def func_response_tuple_subclass():
            class MyTuple(tuple):
                pass

            return MyTuple((1, 2))

        api.register_blueprint(blp)

        response = client.get("/test/response")
        assert response.status_code == 200
        assert response.json == [1, 2]
        response = client.get("/test/response_code")
        assert response.status_code == 201
        assert response.json == [1, 2]
        response = client.get("/test/response_headers")
        assert response.status_code == 200
        assert response.json == [1, 2]
        assert response.headers["X-header"] == "test"
        response = client.get("/test/response_code_headers")
        assert response.status_code == 201
        assert response.json == [1, 2]
        assert response.headers["X-header"] == "test"
        response = client.get("/test/response_wrong_tuple")
        assert response.status_code == 500
        response = client.get("/test/response_tuple_subclass")
        assert response.status_code == 200
        assert response.json == [1, 2]

    def test_blueprint_response_response_object(self, app, schemas):
        api = Api(app)
        blp = Blueprint("test", __name__, url_prefix="/test")
        client = app.test_client()

        @blp.route("/response")
        # Schema is ignored when response object is returned
        @blp.response(200, schemas.DocSchema)
        def func_response():
            return flask.jsonify({"test": "test"}), 201, {"X-header": "test"}

        api.register_blueprint(blp)

        response = client.get("/test/response")
        assert response.status_code == 201
        assert response.status == "201 CREATED"
        assert response.json == {"test": "test"}
        assert response.headers["X-header"] == "test"

    @pytest.mark.parametrize("decorate", (True, False))
    @pytest.mark.parametrize("has_response", (True, False))
    @pytest.mark.parametrize("etag_disabled", (True, False))
    @pytest.mark.parametrize(
        "method", ("OPTIONS", "HEAD", "GET", "POST", "PUT", "PATCH", "DELETE")
    )
    def test_blueprint_etag_documents_responses(
        self,
        app,
        method,
        decorate,
        etag_disabled,
        has_response,
    ):
        app.config["ETAG_DISABLED"] = etag_disabled
        api = Api(app)
        blp = Blueprint("test", "test", url_prefix="/test")

        if decorate:
            if has_response:

                @blp.route("/", methods=[method])
                @blp.response(204)
                @blp.etag
                def func():
                    pass

            else:

                @blp.route("/", methods=[method])
                @blp.etag
                def func():
                    pass

        else:
            if has_response:

                @blp.route("/", methods=[method])
                @blp.response(204)
                def func():
                    pass

            else:

                @blp.route("/", methods=[method])
                def func():
                    pass

        api.register_blueprint(blp)

        operation = api.spec.to_dict()["paths"]["/test/"][method.lower()]
        responses = operation.get("responses", {})
        response_headers = responses.get("204", {}).get("headers", {})
        parameters = operation.get("parameters", [])

        if not decorate or etag_disabled:
            assert "304" not in responses
            assert "412" not in responses
            assert "428" not in responses
            assert "IF_NONE_MATCH" not in parameters
            assert "IF_MATCH" not in parameters
            assert "ETag" not in response_headers
        else:
            assert ("304" in responses) == (method in ["GET", "HEAD"])
            assert ("412" in responses) == (method in ["PUT", "PATCH", "DELETE"])
            assert ("428" in responses) == (method in ["PUT", "PATCH", "DELETE"])
            assert (
                build_ref(api.spec, "parameter", "IF_NONE_MATCH") in parameters
            ) == (method in ["GET", "HEAD"])
            assert (build_ref(api.spec, "parameter", "IF_MATCH") in parameters) == (
                method in ["PUT", "PATCH", "DELETE"]
            )
            assert not has_response or (
                response_headers.get("ETag") == build_ref(api.spec, "header", "ETAG")
            ) == (method in ["GET", "HEAD", "POST", "PUT", "PATCH"])

    def test_blueprint_nested_blueprint(
        self,
        app: flask.Flask,
    ):
        api = Api(app)
        par_blp = Blueprint(
            "parent", "parent", url_prefix="/parent", description="Parent decription"
        )
        child_1_blp = Blueprint(
            "child_1_blp",
            "child_1_blp",
            url_prefix="/child-1",
            description="Child 1 decription",
        )
        child_2_blp = Blueprint(
            "child_2_blp",
            "child_2_blp",
            url_prefix="/child-2",
            description="Child 2 decription",
        )

        @par_blp.route("/")
        def par_view():
            """Dummy parent view func"""
            pass

        @child_1_blp.route("/")
        def child_1_view():
            """Dummy child 1 view func"""
            pass

        @child_2_blp.route("/")
        def child_2_view():
            """Dummy child 2 view func"""
            pass

        par_blp.register_blueprint(child_1_blp)
        par_blp.register_blueprint(child_2_blp)
        api.register_blueprint(par_blp)
        spec = api.spec.to_dict()

        # All endpoints documented
        assert list(spec["paths"].keys()) == [
            "/parent/",
            "/parent/child-1/",
            "/parent/child-2/",
        ]
        assert spec["paths"]["/parent/"]["get"]["summary"] == "Dummy parent view func"
        assert (
            spec["paths"]["/parent/child-1/"]["get"]["summary"]
            == "Dummy child 1 view func"
        )
        assert (
            spec["paths"]["/parent/child-2/"]["get"]["summary"]
            == "Dummy child 2 view func"
        )
        # Only top level blueprints create new "tags"
        assert (
            spec["paths"]["/parent/"]["get"]["tags"]
            == spec["paths"]["/parent/child-1/"]["get"]["tags"]
            == spec["paths"]["/parent/child-2/"]["get"]["tags"]
            == ["parent"]
        )
        assert spec["tags"] == [{"name": "parent", "description": "Parent decription"}]
