"""Test PaginationMixin"""

import http

from itertools import product
from collections import namedtuple
import json

import pytest

from flask.views import MethodView

from flask_smorest import Api, Blueprint, Page
from flask_smorest.pagination import PaginationParameters

from .utils import get_schemas, build_ref

CUSTOM_PAGINATION_PARAMS = (2, 5, 10)


def pagination_blueprint(collection, schemas, as_method_view, custom_params):
    """Return a basic API sample with pagination"""

    blp = Blueprint("test", __name__, url_prefix="/test")

    if custom_params:
        page, page_size, max_page_size = CUSTOM_PAGINATION_PARAMS
    else:
        page, page_size, max_page_size = None, None, None

    if as_method_view:

        @blp.route("/")
        class Resource(MethodView):
            @blp.response(200, schemas.DocSchema(many=True))
            @blp.paginate(page=page, page_size=page_size, max_page_size=max_page_size)
            def get(self, pagination_parameters):
                pagination_parameters.item_count = len(collection.items)
                return collection.items[
                    pagination_parameters.first_item : pagination_parameters.last_item
                    + 1
                ]

    else:

        @blp.route("/")
        @blp.response(200, schemas.DocSchema(many=True))
        @blp.paginate(page=page, page_size=page_size, max_page_size=max_page_size)
        def get_resources(pagination_parameters):
            pagination_parameters.item_count = len(collection.items)
            return collection.items[
                pagination_parameters.first_item : pagination_parameters.last_item + 1
            ]

    return blp


def post_pagination_blueprint(collection, schemas, as_method_view, custom_params):
    """Return a basic API sample with post-pagination"""

    blp = Blueprint("test", __name__, url_prefix="/test")

    if custom_params:
        page, page_size, max_page_size = CUSTOM_PAGINATION_PARAMS
    else:
        page, page_size, max_page_size = None, None, None

    if as_method_view:

        @blp.route("/")
        class Resource(MethodView):
            @blp.response(200, schemas.DocSchema(many=True))
            @blp.paginate(
                Page, page=page, page_size=page_size, max_page_size=max_page_size
            )
            def get(self):
                return collection.items

    else:

        @blp.route("/")
        @blp.response(200, schemas.DocSchema(many=True))
        @blp.paginate(Page, page=page, page_size=page_size, max_page_size=max_page_size)
        def get_resources():
            return collection.items

    return blp


@pytest.fixture(
    params=product(
        # Pagination in function/ post-pagination
        (pagination_blueprint, post_pagination_blueprint),
        # MethodView
        (True, False),
        # Custom parameters
        (True, False),
    )
)
def app_fixture(request, collection, schemas, app):
    """Return an app client for each configuration

    - pagination in function / post-pagination
    - function / method view
    - default / custom pagination parameters
    """
    blp_factory, as_method_view, custom_params = request.param
    blueprint = blp_factory(collection, schemas, as_method_view, custom_params)
    api = Api(app)
    api.register_blueprint(blueprint)
    return namedtuple("AppFixture", ("client", "custom_params"))(
        app.test_client(), custom_params
    )


class TestPagination:
    """Test PaginationMixin"""

    def test_pagination_parameters_repr(self):
        assert (
            repr(PaginationParameters(1, 10))
            == "PaginationParameters(page=1,page_size=10)"
        )

    def test_page_repr(self):
        page_params = PaginationParameters(1, 2)
        assert (
            repr(Page([1, 2, 3, 4, 5], page_params))
            == f"Page(collection=[1, 2, 3, 4, 5],page_params={repr(page_params)})"
        )

    @pytest.mark.parametrize("header_name", ("X-Dummy-Name", None))
    def test_pagination_custom_header_field_name(self, app, header_name):
        """Test PAGINATION_HEADER_NAME overriding"""
        api = Api(app)

        class CustomBlueprint(Blueprint):
            PAGINATION_HEADER_NAME = header_name

        blp = CustomBlueprint("test", __name__, url_prefix="/test")

        @blp.route("/")
        @blp.response(200)
        @blp.paginate()
        def func(pagination_parameters):
            pagination_parameters.item_count = 2
            return [1, 2]

        api.register_blueprint(blp)
        client = app.test_client()
        response = client.get("/test/")
        assert response.status_code == 200
        assert "X-Pagination" not in response.headers
        if header_name is not None:
            assert response.headers[header_name] == (
                '{"total": 2, "total_pages": 1, '
                '"first_page": 1, "last_page": 1, "page": 1}'
            )
            # Also check there is only one pagination header
            assert len(response.headers.getlist(header_name)) == 1

    @pytest.mark.parametrize("openapi_version", ("2.0", "3.0.2"))
    def test_pagination_header_documentation(self, app, openapi_version):
        """Test pagination header is documented"""
        app.config["OPENAPI_VERSION"] = openapi_version
        api = Api(app)

        class CustomBlueprint(Blueprint):
            PAGINATION_HEADER_NAME = "X-Custom-Pagination-Header"

        blp = CustomBlueprint("test", __name__, url_prefix="/test")

        @blp.route("/")
        @blp.response(200)
        @blp.paginate()
        def func(pagination_parameters):
            """Dummy view func"""

        api.register_blueprint(blp)
        spec = api.spec.to_dict()
        get = spec["paths"]["/test/"]["get"]
        assert "PaginationMetadata" in get_schemas(api.spec)
        if openapi_version == "2.0":
            assert get["responses"]["200"]["headers"] == {
                "X-Custom-Pagination-Header": {
                    "description": "Pagination metadata",
                    "schema": {"$ref": "#/definitions/PaginationMetadata"},
                }
            }
        else:
            assert get["responses"]["200"]["headers"] == {
                "X-Custom-Pagination-Header": {
                    "$ref": "#/components/headers/PAGINATION"
                }
            }

    @pytest.mark.parametrize("header_name", ("X-Pagination", None))
    def test_pagination_item_count_missing(self, app, header_name, recwarn):
        """If item_count was not set, pass and warn"""
        api = Api(app)

        class CustomBlueprint(Blueprint):
            PAGINATION_HEADER_NAME = header_name

        blp = CustomBlueprint("test", __name__, url_prefix="/test")

        @blp.route("/")
        @blp.response(200)
        @blp.paginate()
        def func(pagination_parameters):
            # Here, we purposely forget to set item_count
            # pagination_parameters.item_count = 2
            return [1, 2]

        api.register_blueprint(blp)
        client = app.test_client()

        response = client.get("/test/")
        if header_name is None:
            assert not recwarn
        else:
            assert len(recwarn) == 1
            assert recwarn[0].category == UserWarning
            assert str(recwarn[0].message) == (
                "item_count not set in endpoint test.func."
            )
        assert response.status_code == 200
        assert "X-Pagination" not in response.headers

    @pytest.mark.parametrize(
        "collection",
        [
            1000,
        ],
        indirect=True,
    )
    def test_pagination_parameters(self, app_fixture):
        # page = 2, page_size = 5
        response = app_fixture.client.get(
            "/test/", query_string={"page": 2, "page_size": 5}
        )
        assert response.status_code == 200
        data = response.json
        headers = response.headers
        assert len(data) == 5
        assert data[0] == {"field": 5, "item_id": 6}
        assert data[4] == {"field": 9, "item_id": 10}
        assert json.loads(headers["X-Pagination"]) == {
            "total": 1000,
            "total_pages": 200,
            "page": 2,
            "first_page": 1,
            "last_page": 200,
            "previous_page": 1,
            "next_page": 3,
        }
        # page = 334, page_size = 3
        # last page is incomplete if total not multiple of page_size
        response = app_fixture.client.get(
            "/test/", query_string={"page": 334, "page_size": 3}
        )
        assert response.status_code == 200
        data = response.json
        headers = response.headers
        assert len(data) == 1
        assert json.loads(headers["X-Pagination"]) == {
            "total": 1000,
            "total_pages": 334,
            "page": 334,
            "first_page": 1,
            "last_page": 334,
            "previous_page": 333,
        }

    @pytest.mark.parametrize(
        "collection",
        [
            1000,
        ],
        indirect=True,
    )
    def test_pagination_parameters_default_page_page_size(self, app_fixture):
        # Default: page = 1, page_size = 10
        # Custom: page = 2, page_size = 5
        response = app_fixture.client.get("/test/")
        assert response.status_code == 200
        data = response.json
        headers = response.headers
        if app_fixture.custom_params is False:
            assert len(data) == 10
            assert data[0] == {"field": 0, "item_id": 1}
            assert data[9] == {"field": 9, "item_id": 10}
            assert json.loads(headers["X-Pagination"]) == {
                "total": 1000,
                "total_pages": 100,
                "page": 1,
                "first_page": 1,
                "last_page": 100,
                "next_page": 2,
            }
        else:
            assert len(data) == 5
            assert data[0] == {"field": 5, "item_id": 6}
            assert data[4] == {"field": 9, "item_id": 10}
            assert json.loads(headers["X-Pagination"]) == {
                "total": 1000,
                "total_pages": 200,
                "page": 2,
                "first_page": 1,
                "last_page": 200,
                "previous_page": 1,
                "next_page": 3,
            }

    def test_pagination_empty_collection(self, app_fixture):
        # empty collection -> 200 with empty list, partial pagination metadata
        response = app_fixture.client.get("/test/")
        assert response.status_code == 200
        assert json.loads(response.headers["X-Pagination"]) == {
            "total": 0,
            "total_pages": 0,
        }
        assert response.json == []

    @pytest.mark.parametrize(
        "collection",
        [
            1000,
        ],
        indirect=True,
    )
    def test_pagination_page_out_of_range(self, app_fixture):
        # page = 120, page_size = 10
        # page out of range -> 200 with empty list, partial pagination metadata
        response = app_fixture.client.get(
            "/test/", query_string={"page": 120, "page_size": 10}
        )
        assert response.status_code == 200
        assert json.loads(response.headers["X-Pagination"]) == {
            "total": 1000,
            "total_pages": 100,
            "first_page": 1,
            "last_page": 100,
        }
        assert response.json == []

    @pytest.mark.parametrize(
        "collection",
        [
            1000,
        ],
        indirect=True,
    )
    def test_pagination_min_page_page_size(self, app_fixture):
        client = app_fixture.client
        # page < 1 => 422
        response = client.get("/test/", query_string={"page": 0})
        assert response.status_code == 422
        response = client.get("/test/", query_string={"page": -42})
        assert response.status_code == 422
        # page_size < 1 => 422
        response = client.get("/test/", query_string={"page_size": 0})
        assert response.status_code == 422
        response = client.get("/test/", query_string={"page_size": -42})
        assert response.status_code == 422

    @pytest.mark.parametrize(
        "collection",
        [
            1000,
        ],
        indirect=True,
    )
    def test_pagination_max_page_size(self, app_fixture):
        client = app_fixture.client
        # default: page_size > 100 => 422
        # custom: page_size > 10 => 422
        response = client.get("/test/", query_string={"page_size": 101})
        assert response.status_code == 422
        response = client.get("/test/", query_string={"page_size": 11})
        if app_fixture.custom_params is False:
            assert response.status_code == 200
        else:
            assert response.status_code == 422

    def test_pagination_parameters_not_in_query_string(self, app):
        api = Api(app)
        blp = Blueprint("test", __name__, url_prefix="/test")

        @blp.route("/")
        @blp.response(200)
        @blp.paginate(Page)
        def func():
            return range(30)

        api.register_blueprint(blp)
        client = app.test_client()

        # Pagination params in query string: OK
        response = client.get("/test/", query_string={"page": 2, "page_size": 20})
        assert response.json == list(range(20, 30))

        # Pagination params in another location are ignored
        response = client.get(
            "/test/",
            data=json.dumps({"page": 2, "page_size": 20}),
        )
        assert response.json == list(range(0, 10))

    def test_pagination_parameters_and_query_string_args(self, app, schemas):
        api = Api(app)
        blp = Blueprint("test", __name__, url_prefix="/test")

        @blp.route("/")
        @blp.arguments(schemas.QueryArgsSchema, location="query")
        @blp.response(200)
        @blp.paginate(Page)
        def func(query_args):
            assert query_args["arg1"] == "Test"
            assert query_args["arg2"] == 12
            return range(30)

        api.register_blueprint(blp)
        client = app.test_client()

        # Pagination params in query string: OK
        response = client.get(
            "/test/",
            query_string={"page": 2, "page_size": 20, "arg1": "Test", "arg2": 12},
        )
        assert response.json == list(range(20, 30))

    @pytest.mark.parametrize("openapi_version", ("2.0", "3.0.2"))
    def test_pagination_is_documented(self, app, schemas, openapi_version):
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
    def test_pagination_documents_error_response(
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

    def test_pagination_response_tuple(self, app):
        # Unset TESTING to let Flask return 500 on unhandled exception
        app.config["TESTING"] = False
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
