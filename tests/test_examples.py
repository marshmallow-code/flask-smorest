"""Test flask-smorest on more or less realistic examples"""

import json
from contextlib import contextmanager

import pytest

import marshmallow as ma
from flask.views import MethodView

from flask_smorest import Api, Blueprint, abort, Page
from flask_smorest.pagination import PaginationMetadataSchema
from flask_smorest.utils import get_appcontext
from .mocks import ItemNotFound
from .utils import build_ref, get_schemas


def implicit_data_and_schema_etag_blueprint(collection, schemas):
    """Blueprint with implicit data and schema ETag computation

    ETag computed automatically from result data with same schema as data
    Post-pagination is used to reduce boilerplate even more
    """

    DocSchema = schemas.DocSchema

    blp = Blueprint("test", __name__, url_prefix="/test")

    @blp.route("/")
    @blp.etag
    class Resource(MethodView):
        @blp.response(200, DocSchema(many=True))
        @blp.paginate(Page)
        def get(self):
            return collection.items

        @blp.arguments(DocSchema)
        @blp.response(201, DocSchema)
        def post(self, new_item):
            return collection.post(new_item)

    @blp.route("/<int:item_id>")
    @blp.etag
    class ResourceById(MethodView):
        def _get_item(self, item_id):
            try:
                return collection.get_by_id(item_id)
            except ItemNotFound:
                abort(404)

        @blp.response(200, DocSchema)
        def get(self, item_id):
            return self._get_item(item_id)

        @blp.arguments(DocSchema)
        @blp.response(200, DocSchema)
        def put(self, new_item, item_id):
            item = self._get_item(item_id)
            # Check ETag is a manual action and schema must be provided
            blp.check_etag(item, DocSchema)
            return collection.put(item_id, new_item)

        @blp.response(204)
        def delete(self, item_id):
            item = self._get_item(item_id)
            # Check ETag is a manual action and schema must be provided
            blp.check_etag(item, DocSchema)
            collection.delete(item_id)

    return blp


def explicit_data_no_schema_etag_blueprint(collection, schemas):
    """Blueprint with explicit ETag computation, no schema

    ETag computed without schema from arbitrary data

    We're using item['db_field'] for ETag data as a dummy example.
    """

    DocSchema = schemas.DocSchema

    blp = Blueprint("test", __name__, url_prefix="/test")

    @blp.route("/")
    @blp.etag
    class Resource(MethodView):
        @blp.response(200, DocSchema(many=True))
        @blp.paginate()
        def get(self, pagination_parameters):
            pagination_parameters.item_count = len(collection.items)
            # It is better to rely on automatic ETag here, as it includes
            # pagination metadata.
            return collection.items[
                pagination_parameters.first_item : pagination_parameters.last_item + 1
            ]

        @blp.arguments(DocSchema)
        @blp.response(201, DocSchema)
        def post(self, new_item):
            # Compute ETag using arbitrary data and no schema
            blp.set_etag(new_item["db_field"])
            return collection.post(new_item)

    @blp.route("/<int:item_id>")
    @blp.etag
    class ResourceById(MethodView):
        def _get_item(self, item_id):
            try:
                return collection.get_by_id(item_id)
            except ItemNotFound:
                abort(404)

        @blp.response(200, DocSchema)
        def get(self, item_id):
            item = self._get_item(item_id)
            # Compute ETag using arbitrary data and no schema
            blp.set_etag(item["db_field"])
            return item

        @blp.arguments(DocSchema)
        @blp.response(200, DocSchema)
        def put(self, new_item, item_id):
            item = self._get_item(item_id)
            # Check ETag is a manual action, no shema used
            blp.check_etag(item["db_field"])
            new_item = collection.put(item_id, new_item)
            # Compute ETag using arbitrary data and no schema
            blp.set_etag(new_item["db_field"])
            return new_item

        @blp.response(204)
        def delete(self, item_id):
            item = self._get_item(item_id)
            # Check ETag is a manual action, no shema used
            blp.check_etag(item["db_field"])
            collection.delete(item_id)

    return blp


@pytest.fixture(
    params=[
        (implicit_data_and_schema_etag_blueprint, True),
        (explicit_data_no_schema_etag_blueprint, False),
    ]
)
def blueprint_fixture(request, collection, schemas):
    blp_factory = request.param[0]
    etag_schema = request.param[1]
    return blp_factory(collection, schemas), etag_schema


class TestFullExample:
    def test_examples(self, app, blueprint_fixture, schemas):
        blueprint, etag_schema = blueprint_fixture

        api = Api(app)
        api.register_blueprint(blueprint)

        client = app.test_client()

        @contextmanager
        def assert_counters(schema_load, schema_dump):
            """Check number of calls to dump/load methods of schema"""
            schemas.DocSchema.reset_load_count()
            schemas.DocSchema.reset_dump_count()
            yield
            assert schemas.DocSchema.load_count == schema_load
            assert schemas.DocSchema.dump_count == schema_dump

        # GET collection without ETag: OK
        with assert_counters(0, 1):
            response = client.get("/test/")
            assert response.status_code == 200
            list_etag = response.headers["ETag"]
            assert len(response.json) == 0
            assert json.loads(response.headers["X-Pagination"]) == {
                "total": 0,
                "total_pages": 0,
            }

        # GET collection with correct ETag: Not modified
        with assert_counters(0, 1):
            response = client.get("/test/", headers={"If-None-Match": list_etag})
        assert response.status_code == 304

        # POST item_1
        item_1_data = {"field": 0}
        with assert_counters(1, 1):
            response = client.post(
                "/test/", data=json.dumps(item_1_data), content_type="application/json"
            )
        assert response.status_code == 201
        item_1_id = response.json["item_id"]

        # GET collection with wrong/outdated ETag: OK
        with assert_counters(0, 1):
            response = client.get("/test/", headers={"If-None-Match": list_etag})
        assert response.status_code == 200
        list_etag = response.headers["ETag"]
        assert len(response.json) == 1
        assert response.json[0] == {"field": 0, "item_id": 1}
        assert json.loads(response.headers["X-Pagination"]) == {
            "total": 1,
            "total_pages": 1,
            "page": 1,
            "first_page": 1,
            "last_page": 1,
        }

        # GET by ID without ETag: OK
        with assert_counters(0, 1):
            response = client.get(f"/test/{item_1_id}")
        assert response.status_code == 200
        item_etag = response.headers["ETag"]

        # GET by ID with correct ETag: Not modified
        with assert_counters(0, 1 if etag_schema else 0):
            response = client.get(
                f"/test/{item_1_id}", headers={"If-None-Match": item_etag}
            )
        assert response.status_code == 304

        # PUT without ETag: Precondition required error
        item_1_data["field"] = 1
        with assert_counters(0, 0):
            response = client.put(
                f"/test/{item_1_id}",
                data=json.dumps(item_1_data),
                content_type="application/json",
            )
        assert response.status_code == 428

        # PUT with correct ETag: OK
        with assert_counters(1, 2 if etag_schema else 1):
            response = client.put(
                f"/test/{item_1_id}",
                data=json.dumps(item_1_data),
                content_type="application/json",
                headers={"If-Match": item_etag},
            )
        assert response.status_code == 200
        new_item_etag = response.headers["ETag"]

        # PUT with wrong/outdated ETag: Precondition failed error
        item_1_data["field"] = 2
        with assert_counters(1, 1 if etag_schema else 0):
            response = client.put(
                f"/test/{item_1_id}",
                data=json.dumps(item_1_data),
                content_type="application/json",
                headers={"If-Match": item_etag},
            )
        assert response.status_code == 412

        # GET by ID with wrong/outdated ETag: OK
        with assert_counters(0, 1):
            response = client.get(
                f"/test/{item_1_id}", headers={"If-None-Match": item_etag}
            )
        assert response.status_code == 200

        # GET collection with pagination set to 1 element per page
        with assert_counters(0, 1):
            response = client.get(
                "/test/",
                headers={"If-None-Match": list_etag},
                query_string={"page": 1, "page_size": 1},
            )
        assert response.status_code == 200
        list_etag = response.headers["ETag"]
        assert len(response.json) == 1
        assert response.json[0] == {"field": 1, "item_id": 1}
        assert json.loads(response.headers["X-Pagination"]) == {
            "total": 1,
            "total_pages": 1,
            "page": 1,
            "first_page": 1,
            "last_page": 1,
        }

        # POST item_2
        item_2_data = {"field": 1}
        with assert_counters(1, 1):
            response = client.post(
                "/test/", data=json.dumps(item_2_data), content_type="application/json"
            )
        assert response.status_code == 201

        # GET collection with pagination set to 1 element per page
        # Content is the same (item_1) but pagination metadata has changed
        # so we don't get a 304 and the data is returned again
        with assert_counters(0, 1):
            response = client.get(
                "/test/",
                headers={"If-None-Match": list_etag},
                query_string={"page": 1, "page_size": 1},
            )
        assert response.status_code == 200
        list_etag = response.headers["ETag"]
        assert len(response.json) == 1
        assert response.json[0] == {"field": 1, "item_id": 1}
        assert json.loads(response.headers["X-Pagination"]) == {
            "total": 2,
            "total_pages": 2,
            "page": 1,
            "first_page": 1,
            "last_page": 2,
            "next_page": 2,
        }

        # DELETE without ETag: Precondition required error
        with assert_counters(0, 0):
            response = client.delete(f"/test/{item_1_id}")
        assert response.status_code == 428

        # DELETE with wrong/outdated ETag: Precondition failed error
        with assert_counters(0, 1 if etag_schema else 0):
            response = client.delete(
                f"/test/{item_1_id}", headers={"If-Match": item_etag}
            )
        assert response.status_code == 412

        # DELETE with correct ETag: No Content
        with assert_counters(0, 1 if etag_schema else 0):
            response = client.delete(
                f"/test/{item_1_id}", headers={"If-Match": new_item_etag}
            )
        assert response.status_code == 204


class TestCustomExamples:
    @pytest.mark.parametrize("openapi_version", ("2.0", "3.0.2"))
    def test_response_payload_wrapping(self, app, schemas, openapi_version):
        """Demonstrates how to wrap response payload in a data field"""

        class WrapperBlueprint(Blueprint):
            # Wrap payload data
            @staticmethod
            def _prepare_response_content(data):
                if data is not None:
                    return {"data": data}
                return None

            # Document data wrapper
            # The schema is not used to dump the payload, only to generate doc
            @staticmethod
            def _make_doc_response_schema(schema):
                if schema:
                    return type(
                        "Wrap" + schema.__class__.__name__,
                        (ma.Schema,),
                        {"data": ma.fields.Nested(schema)},
                    )
                return None

        app.config["OPENAPI_VERSION"] = openapi_version
        api = Api(app)
        client = app.test_client()
        blp = WrapperBlueprint("test", __name__, url_prefix="/test")

        @blp.route("/")
        @blp.response(200, schemas.DocSchema)
        def func():
            return {"item_id": 1, "db_field": 42}

        api.register_blueprint(blp)
        spec = api.spec.to_dict()

        # Test data is wrapped
        resp = client.get("/test/")
        assert resp.json == {"data": {"item_id": 1, "field": 42}}

        # Test wrapping is correctly documented
        if openapi_version == "3.0.2":
            content = spec["paths"]["/test/"]["get"]["responses"]["200"]["content"][
                "application/json"
            ]
        else:
            content = spec["paths"]["/test/"]["get"]["responses"]["200"]
        assert content["schema"] == build_ref(api.spec, "schema", "WrapDoc")
        assert get_schemas(api.spec)["WrapDoc"] == {
            "type": "object",
            "properties": {"data": build_ref(api.spec, "schema", "Doc")},
        }
        assert "Doc" in get_schemas(api.spec)

    @pytest.mark.parametrize("openapi_version", ("2.0", "3.0.2"))
    def test_pagination_in_response_payload(self, app, schemas, openapi_version):
        """Demonstrates how to add pagination metadata in response payload"""

        class WrapperBlueprint(Blueprint):
            # Set pagination metadata in app context
            def _set_pagination_metadata(self, page_params, result, headers):
                page_meta = self._make_pagination_metadata(
                    page_params.page, page_params.page_size, page_params.item_count
                )
                get_appcontext()["pagination_metadata"] = page_meta
                return result, headers

            # Wrap payload data and add pagination metadata if any
            @staticmethod
            def _prepare_response_content(data):
                if data is not None:
                    ret = {"data": data}
                    page_meta = get_appcontext().get("pagination_metadata")
                    if page_meta is not None:
                        ret["pagination"] = page_meta
                    return ret
                return None

            # Document data wrapper and pagination in payload
            @staticmethod
            def _prepare_response_doc(doc, doc_info, spec, **kwargs):
                operation = doc_info.get("response", {})
                if operation:
                    success_status_codes = doc_info.get("success_status_codes", [])
                    for success_status_code in success_status_codes:
                        response = operation.get("responses", {}).get(
                            success_status_code
                        )
                        if response is not None:
                            if "schema" in response:
                                schema = response["schema"]
                                response["schema"] = type(
                                    "Wrap" + schema.__class__.__name__,
                                    (ma.Schema,),
                                    {"data": ma.fields.Nested(schema)},
                                )
                                if "pagination" in doc_info:
                                    schema = response["schema"]
                                    response["schema"] = type(
                                        "Pagination" + schema.__name__,
                                        (schema,),
                                        {
                                            "pagination": ma.fields.Nested(
                                                PaginationMetadataSchema
                                            )
                                        },
                                    )
                return super(WrapperBlueprint, WrapperBlueprint)._prepare_response_doc(
                    doc, doc_info, spec=spec, **kwargs
                )

        app.config["OPENAPI_VERSION"] = openapi_version
        api = Api(app)
        client = app.test_client()
        blp = WrapperBlueprint("test", __name__, url_prefix="/test")

        @blp.route("/")
        @blp.response(200, schemas.DocSchema(many=True))
        @blp.paginate(Page)
        def func():
            return [
                {"item_id": 1, "db_field": 42},
                {"item_id": 2, "db_field": 69},
            ]

        api.register_blueprint(blp)
        spec = api.spec.to_dict()

        # Test data is wrapped and pagination metadata added
        resp = client.get("/test/")
        assert resp.json == {
            "data": [{"field": 42, "item_id": 1}, {"field": 69, "item_id": 2}],
            "pagination": {
                "page": 1,
                "first_page": 1,
                "last_page": 1,
                "total": 2,
                "total_pages": 1,
            },
        }

        # Test pagination is correctly documented
        if openapi_version == "3.0.2":
            content = spec["paths"]["/test/"]["get"]["responses"]["200"]["content"][
                "application/json"
            ]
        else:
            content = spec["paths"]["/test/"]["get"]["responses"]["200"]
        assert content["schema"] == build_ref(api.spec, "schema", "PaginationWrapDoc")
        assert get_schemas(api.spec)["PaginationWrapDoc"] == {
            "type": "object",
            "properties": {
                "data": {
                    "items": build_ref(api.spec, "schema", "Doc"),
                    "type": "array",
                },
                "pagination": build_ref(api.spec, "schema", "PaginationMetadata"),
            },
        }
        assert "Doc" in get_schemas(api.spec)
