"""Test ArgumentsMixin"""

import http
import io
import json

import pytest

from flask import request
from werkzeug.datastructures import MultiDict

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
    "form_and_files": "formData",
}

REQUEST_BODY_CONTENT_TYPE = {
    "json": "application/json",
    "form": "application/x-www-form-urlencoded",
    "files": "multipart/form-data",
    "form_and_files": "multipart/form-data",
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
            multipart_spec = spec["components"]["schemas"]["Multipart"]
            assert multipart_spec["type"] == "object"
            assert multipart_spec["properties"] == {
                "file_1": {"type": "string", "format": "binary"},
                "file_2": {"type": "string", "format": "binary"},
            }

    @pytest.mark.parametrize("openapi_version", ("2.0", "3.0.2"))
    @pytest.mark.parametrize("as_kwargs", (False, True))
    @pytest.mark.parametrize("async_view", (False, True))
    def test_arguments_form_and_files(
        self, app, openapi_version, as_kwargs, async_view
    ):
        app.config["OPENAPI_VERSION"] = openapi_version
        api = Api(app)
        blp = Blueprint("test", __name__, url_prefix="/test")

        class MixedMultipartSchema(ma.Schema):
            title = ma.fields.String(required=True)
            count = ma.fields.Integer(required=True)
            file = Upload(required=True)

        def view(*args, **kwargs):
            data = kwargs if as_kwargs else args[0]
            # Parsing must leave the request's form and files intact.
            assert request.form["title"] == data["title"]
            assert "file" not in request.form
            assert request.files["file"] is data["file"]
            assert "title" not in request.files
            return {
                "title": data["title"],
                "count": data["count"],
                "file": data["file"].read().decode(),
            }

        if async_view:

            async def func(*args, **kwargs):
                return view(*args, **kwargs)

        else:
            func = view

        blp.route("/", methods=["POST"])(
            blp.arguments(
                MixedMultipartSchema, location="form_and_files", as_kwargs=as_kwargs
            )(func)
        )
        api.register_blueprint(blp)

        response = app.test_client().post(
            "/test/",
            data={
                "title": "A document",
                "count": "2",
                "file": (io.BytesIO(b"Test"), "test.txt"),
            },
        )
        assert response.status_code == 200
        assert response.json == {"title": "A document", "count": 2, "file": "Test"}

        spec = api.spec.to_dict()
        operation = spec["paths"]["/test/"]["post"]
        if openapi_version == "2.0":
            assert operation["consumes"] == ["multipart/form-data"]
            assert operation["parameters"] == [
                {"in": "formData", "name": "title", "type": "string", "required": True},
                {
                    "in": "formData",
                    "name": "count",
                    "type": "integer",
                    "required": True,
                },
                {"in": "formData", "name": "file", "type": "file", "required": True},
            ]
        else:
            assert "parameters" not in operation
            assert operation["requestBody"] == {
                "required": True,
                "content": {
                    "multipart/form-data": {
                        "schema": {"$ref": "#/components/schemas/MixedMultipart"}
                    }
                },
            }
            schema = spec["components"]["schemas"]["MixedMultipart"]
            assert schema["properties"] == {
                "title": {"type": "string"},
                "count": {"type": "integer"},
                "file": {"type": "string", "format": "binary"},
            }
            assert schema["required"] == ["count", "file", "title"]

    def test_arguments_form_and_files_lists(self, app):
        api = Api(app)
        blp = Blueprint("test", __name__, url_prefix="/test")

        class MixedMultipartSchema(ma.Schema):
            labels = ma.fields.List(ma.fields.String(), data_key="label")
            files = ma.fields.List(Upload(), data_key="file")

        class QuerySchema(ma.Schema):
            page = ma.fields.Integer()

        @blp.route("/", methods=["POST"])
        @blp.arguments(MixedMultipartSchema(), location="form_and_files")
        @blp.arguments(QuerySchema, location="query")
        def func(data, query):
            assert request.form.getlist("label") == data["labels"]
            assert request.files.getlist("file") == data["files"]
            return {
                "labels": data["labels"],
                "files": [file.read().decode() for file in data["files"]],
                "page": query["page"],
            }

        api.register_blueprint(blp)
        response = app.test_client().post(
            "/test/?page=2",
            data=MultiDict(
                [
                    ("label", "first"),
                    ("label", "second"),
                    ("file", (io.BytesIO(b"Test 1"), "first.txt")),
                    ("file", (io.BytesIO(b"Test 2"), "second.txt")),
                ]
            ),
        )
        assert response.status_code == 200
        assert response.json == {
            "labels": ["first", "second"],
            "files": ["Test 1", "Test 2"],
            "page": 2,
        }
        operation = api.spec.to_dict()["paths"]["/test/"]["post"]
        assert operation["parameters"] == [
            {
                "in": "query",
                "name": "page",
                "schema": {"type": "integer"},
                "required": False,
            }
        ]
        schema = api.spec.to_dict()["components"]["schemas"]["MixedMultipart"]
        assert schema["properties"]["file"] == {
            "type": "array",
            "items": {"type": "string", "format": "binary"},
        }

    @pytest.mark.parametrize("error_status_code", (400, 422))
    @pytest.mark.parametrize(
        "invalid", ("missing_form", "missing_file", "invalid_form", "unknown")
    )
    def test_arguments_form_and_files_validation(self, app, invalid, error_status_code):
        api = Api(app)
        blp = Blueprint("test", __name__, url_prefix="/test")

        class MixedMultipartSchema(ma.Schema):
            count = ma.fields.Integer(required=True)
            file = Upload(required=True)

        @blp.route("/", methods=["POST"])
        @blp.arguments(
            MixedMultipartSchema,
            location="form_and_files",
            error_status_code=error_status_code,
        )
        def func(data):
            pytest.fail("Invalid arguments must not reach the view")

        api.register_blueprint(blp)
        data = {"count": "2", "file": (io.BytesIO(b"Test"), "test.txt")}
        if invalid == "missing_form":
            del data["count"]
            errors = {"count": ["Missing data for required field."]}
        elif invalid == "missing_file":
            del data["file"]
            errors = {"file": ["Missing data for required field."]}
        elif invalid == "invalid_form":
            data["count"] = "invalid"
            errors = {"count": ["Not a valid integer."]}
        else:
            data["extra"] = "unknown"
            errors = {"extra": ["Unknown field."]}
        response = app.test_client().post("/test/", data=data)
        assert response.status_code == error_status_code
        assert response.json["errors"] == {"form_and_files": errors}
        operation = api.spec.to_dict()["paths"]["/test/"]["post"]
        assert str(error_status_code) in operation["responses"]

    @pytest.mark.parametrize("unknown", (None, ma.EXCLUDE, ma.INCLUDE))
    def test_arguments_form_and_files_unknown(self, app, unknown):
        api = Api(app)
        blp = Blueprint("test", __name__, url_prefix="/test")

        class MixedMultipartSchema(ma.Schema):
            title = ma.fields.String()
            file = Upload()

            class Meta:
                unknown = ma.EXCLUDE

        kwargs = {} if unknown is None else {"unknown": unknown}

        @blp.route("/", methods=["POST"])
        @blp.arguments(MixedMultipartSchema, location="form_and_files", **kwargs)
        def func(data):
            return {"extra": data.get("extra")}

        api.register_blueprint(blp)
        response = app.test_client().post(
            "/test/",
            data={
                "title": "Title",
                "file": (io.BytesIO(b"Test"), "test.txt"),
                "extra": "unknown",
            },
        )
        assert response.status_code == 200
        assert response.json == {"extra": "unknown" if unknown == ma.INCLUDE else None}

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

    def test_arguments_async_view(self, app, schemas):
        api = Api(app)
        blp = Blueprint("test", __name__, url_prefix="/test")

        @blp.route("/")
        @blp.arguments(schemas.DocSchema, location="query")
        async def func(arg):
            return arg, 200

        api.register_blueprint(blp)
        client = app.test_client()
        response = client.get("/test/?field=1337")
        assert response.status_code == 200
        assert response.json["db_field"] == 1337
