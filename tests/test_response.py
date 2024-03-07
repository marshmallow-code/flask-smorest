"""Test ResponseMixin"""

import http

import pytest

import flask
from flask.views import MethodView

import marshmallow as ma

from flask_smorest import Api, Blueprint

from .utils import build_ref


class TestResponse:
    """Test ResponseMixin"""

    @pytest.mark.parametrize("openapi_version", ["2.0", "3.0.2"])
    def test_response_schema(self, app, openapi_version, schemas):
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

    def test_response_description(self, app):
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
    def test_response_example(self, app, openapi_version):
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
    def test_response_examples(self, app, openapi_version):
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

    def test_response_headers(self, app):
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
    def test_response_content_type(self, app, schemas, openapi_version, content_type):
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
                content_type or "application/json": {
                    "schema": build_ref(api.spec, "schema", "Doc")
                }
            }

    @pytest.mark.parametrize("openapi_version", ["2.0", "3.0.2"])
    @pytest.mark.parametrize("schema_type", ["object", "ref"])
    def test_alt_response(self, app, openapi_version, schemas, schema_type):
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
    def test_alt_response_ref(self, app, openapi_version):
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

    # This is only relevant to OAS3.
    @pytest.mark.parametrize("openapi_version", ("3.0.2",))
    def test_blueprint_multiple_alt_response_same_status_code(
        self, app, openapi_version
    ):
        """Check multiple calls to response and alt_response with same status code"""
        app.config["OPENAPI_VERSION"] = openapi_version
        api = Api(app)
        blp = Blueprint("test", "test", url_prefix="/test")

        @blp.route("/")
        @blp.response(200, schema="JSONDocSchema")
        @blp.alt_response(200, schema="HTMLDocSchema", content_type="text/html")
        @blp.alt_response(200, schema="CSVDocSchema", content_type="text/csv")
        def func():
            pass

        api.register_blueprint(blp)

        paths = api.spec.to_dict()["paths"]

        json_schema_ref = build_ref(api.spec, "schema", "JSONDocSchema")
        html_schema_ref = build_ref(api.spec, "schema", "HTMLDocSchema")
        csv_schema_ref = build_ref(api.spec, "schema", "CSVDocSchema")

        response = paths["/test/"]["get"]["responses"]["200"]

        assert response["content"] == {
            "application/json": {"schema": json_schema_ref},
            "text/html": {"schema": html_schema_ref},
            "text/csv": {"schema": csv_schema_ref},
        }

    @pytest.mark.parametrize("openapi_version", ["2.0", "3.0.2"])
    def test_alt_response_wrapper(self, app, schemas, openapi_version):
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
    def test_alt_response_success_response(self, app, openapi_version, success):
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

    @pytest.mark.parametrize("status_code", (200, "200", http.HTTPStatus.OK))
    def test_response_status_code_cast_to_string(self, app, status_code):
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

    def test_response_tuple(self, app):
        # Unset TESTING to let Flask return 500 on unhandled exception
        app.config["TESTING"] = False
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

    def test_response_response_object(self, app, schemas):
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
