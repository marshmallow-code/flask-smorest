"""Test Blueprint extra features"""

import pytest

import flask
from flask.views import MethodView

import marshmallow as ma

from flask_smorest import Api, Blueprint

from .utils import build_ref


class TestBlueprint:
    """Test Blueprint class"""

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
