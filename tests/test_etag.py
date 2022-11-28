"""Test ETag feature"""

import json
import hashlib

import pytest

from flask import jsonify, Response, request as f_request
from flask.views import MethodView

from flask_smorest import Api, Blueprint, abort
from flask_smorest.etag import _get_etag_ctx
from flask_smorest.exceptions import (
    NotModified,
    PreconditionRequired,
    PreconditionFailed,
)
from flask_smorest.utils import get_appcontext
import marshmallow as ma

from .mocks import ItemNotFound


HTTP_METHODS = ["OPTIONS", "HEAD", "GET", "POST", "PUT", "PATCH", "DELETE"]
HTTP_METHODS_ALLOWING_SET_ETAG = ["GET", "HEAD", "POST", "PUT", "PATCH"]


@pytest.fixture(params=[True, False])
def app_with_etag(request, collection, schemas, app):
    """Return a basic API sample with ETag"""

    as_method_view = request.param
    DocSchema = schemas.DocSchema
    blp = Blueprint("test", __name__, url_prefix="/test")

    if as_method_view:

        # Decorate each function
        @blp.route("/")
        class Resource(MethodView):
            @blp.etag
            @blp.response(200, DocSchema(many=True))
            def get(self):
                return collection.items

            @blp.etag
            @blp.arguments(DocSchema)
            @blp.response(201, DocSchema)
            def post(self, new_item):
                return collection.post(new_item)

        # Better: decorate the whole MethodView
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
                blp.check_etag(item, DocSchema)
                return collection.put(item_id, new_item)

            @blp.response(204)
            def delete(self, item_id):
                item = self._get_item(item_id)
                blp.check_etag(item, DocSchema)
                del collection.items[collection.items.index(item)]

    else:

        @blp.route("/")
        @blp.etag
        @blp.response(200, DocSchema(many=True))
        def get_resources():
            return collection.items

        @blp.route("/", methods=("POST",))
        @blp.etag
        @blp.arguments(DocSchema)
        @blp.response(201, DocSchema)
        def post_resource(new_item):
            return collection.post(new_item)

        def _get_item(item_id):
            try:
                return collection.get_by_id(item_id)
            except ItemNotFound:
                abort(404)

        @blp.route("/<int:item_id>")
        @blp.etag
        @blp.response(200, DocSchema)
        def get_resource(item_id):
            return _get_item(item_id)

        @blp.route("/<int:item_id>", methods=("PUT",))
        @blp.etag
        @blp.arguments(DocSchema)
        @blp.response(200, DocSchema)
        def put_resource(new_item, item_id):
            item = _get_item(item_id)
            blp.check_etag(item, DocSchema)
            return collection.put(item_id, new_item)

        @blp.route("/<int:item_id>", methods=("DELETE",))
        @blp.etag
        @blp.response(204)
        def delete_resource(item_id):
            item = _get_item(item_id)
            blp.check_etag(item, DocSchema)
            del collection.items[collection.items.index(item)]

    api = Api(app)
    api.register_blueprint(blp)

    return app


class TestEtag:
    @pytest.mark.parametrize("extra_data", [None, {}, {"answer": 42}])
    def test_etag_generate_etag(self, extra_data):
        blp = Blueprint("test", __name__)
        item = {"item_id": 1, "db_field": 0}
        data = (item, extra_data) if extra_data else item

        assert (
            blp._generate_etag(item, extra_data=extra_data)
            == hashlib.sha1(
                bytes(json.dumps(data, sort_keys=True), "utf-8")
            ).hexdigest()
        )

    def test_etag_generate_etag_order_insensitive(self):
        blp = Blueprint("test", __name__)
        data_1 = {"a": 1, "b": 2}
        data_2 = {"b": 2, "a": 1}
        assert blp._generate_etag(data_1) == blp._generate_etag(data_2)

    @pytest.mark.parametrize("method", HTTP_METHODS)
    def test_etag_check_precondition(self, app, method):
        blp = Blueprint("test", __name__)

        with app.test_request_context("/", method=method):
            if method in ["PUT", "PATCH", "DELETE"]:
                with pytest.raises(PreconditionRequired):
                    blp._check_precondition()
            else:
                blp._check_precondition()

    @pytest.mark.parametrize("method", ["PUT", "PATCH", "DELETE"])
    @pytest.mark.parametrize("etag_disabled", (True, False))
    def test_etag_check_etag(self, app, schemas, method, etag_disabled):
        app.config["ETAG_DISABLED"] = etag_disabled
        blp = Blueprint("test", __name__)
        schema = schemas.DocSchema
        old_item = {"item_id": 1, "db_field": 0}
        new_item = {"item_id": 1, "db_field": 1}
        old_etag = blp._generate_etag(old_item)
        old_etag_with_schema = blp._generate_etag(schema().dump(old_item))

        with app.test_request_context(
            "/",
            method=method,
            headers={"If-Match": old_etag},
        ):
            blp.check_etag(old_item)
            if not etag_disabled:
                with pytest.raises(PreconditionFailed):
                    blp.check_etag(new_item)
            else:
                blp.check_etag(new_item)
        with app.test_request_context(
            "/",
            method=method,
            headers={"If-Match": old_etag_with_schema},
        ):
            blp.check_etag(old_item, schema)
            if not etag_disabled:
                with pytest.raises(PreconditionFailed):
                    blp.check_etag(new_item, schema)
            else:
                blp.check_etag(new_item)

    @pytest.mark.parametrize("method", HTTP_METHODS)
    @pytest.mark.parametrize("etag_disabled", (True, False))
    def test_etag_check_etag_wrong_method_warning(self, app, method, etag_disabled):
        app.config["ETAG_DISABLED"] = etag_disabled
        blp = Blueprint("test", __name__)

        with pytest.warns(None) as record:
            with app.test_request_context(
                "/",
                method=method,
                headers={"If-Match": ""},
            ):
                # Ignore ETag check fail. Just testing the warning.
                try:
                    blp.check_etag(None)
                except PreconditionFailed:
                    pass
                if method in ["PUT", "PATCH", "DELETE"]:
                    assert not record
                else:
                    assert len(record) == 1
                    assert record[0].category == UserWarning
                    assert str(record[0].message) == (
                        f"ETag cannot be checked on {method} request."
                    )

    @pytest.mark.parametrize("method", HTTP_METHODS)
    def test_etag_verify_check_etag_warning(self, app, method):
        blp = Blueprint("test", __name__)
        old_item = {"item_id": 1, "db_field": 0}
        old_etag = blp._generate_etag(old_item)

        with pytest.warns(None) as record:
            with app.test_request_context(
                "/",
                method=method,
                headers={"If-Match": old_etag},
            ):
                blp._verify_check_etag()
                if method in ["PUT", "PATCH", "DELETE"]:
                    assert len(record) == 1
                    assert record[0].category == UserWarning
                    assert str(record[0].message) == (
                        "ETag not checked in endpoint {} on {} request.".format(
                            f_request.endpoint, method
                        )
                    )
                else:
                    assert not record
                blp.check_etag(old_item)
                record.clear()
                blp._verify_check_etag()
                assert not record

    @pytest.mark.parametrize("method", HTTP_METHODS_ALLOWING_SET_ETAG)
    @pytest.mark.parametrize("etag_disabled", (True, False))
    def test_etag_set_etag(self, app, schemas, method, etag_disabled):
        app.config["ETAG_DISABLED"] = etag_disabled
        blp = Blueprint("test", __name__)
        schema = schemas.DocSchema
        item = {"item_id": 1, "db_field": 0}
        etag = blp._generate_etag(item)
        etag_with_schema = blp._generate_etag(schema().dump(item))

        with app.test_request_context("/", method=method):
            blp.set_etag(item)
            if not etag_disabled:
                assert _get_etag_ctx()["etag"] == etag
                del _get_etag_ctx()["etag"]
            else:
                assert "etag" not in _get_etag_ctx()
        with app.test_request_context(
            "/",
            method=method,
            headers={"If-None-Match": etag},
        ):
            if not etag_disabled:
                if method in ["GET", "HEAD"]:
                    with pytest.raises(NotModified):
                        blp.set_etag(item)
            else:
                blp.set_etag(item)
                assert "etag" not in _get_etag_ctx()
        with app.test_request_context(
            "/",
            method=method,
            headers={"If-None-Match": etag_with_schema},
        ):
            if not etag_disabled:
                if method in ["GET", "HEAD"]:
                    with pytest.raises(NotModified):
                        blp.set_etag(item, schema)
            else:
                blp.set_etag(item, schema)
                assert "etag" not in _get_etag_ctx()
        with app.test_request_context(
            "/",
            method=method,
            headers={"If-None-Match": "dummy"},
        ):
            if not etag_disabled:
                blp.set_etag(item)
                assert _get_etag_ctx()["etag"] == etag
                del _get_etag_ctx()["etag"]
                blp.set_etag(item, schema)
                assert _get_etag_ctx()["etag"] == etag_with_schema
                del _get_etag_ctx()["etag"]
            else:
                blp.set_etag(item)
                assert "etag" not in _get_etag_ctx()
                blp.set_etag(item, schema)
                assert "etag" not in _get_etag_ctx()

    @pytest.mark.parametrize("etag_disabled", (True, False))
    @pytest.mark.parametrize("method", HTTP_METHODS)
    def test_etag_set_etag_method_not_allowed_warning(self, app, method, etag_disabled):
        app.config["ETAG_DISABLED"] = etag_disabled
        blp = Blueprint("test", __name__)

        with pytest.warns(None) as record:
            with app.test_request_context("/", method=method):
                blp.set_etag(None)
            if method in HTTP_METHODS_ALLOWING_SET_ETAG:
                assert not record
            else:
                assert len(record) == 1
                assert record[0].category == UserWarning
                assert str(record[0].message) == (
                    f"ETag cannot be set on {method} request."
                )

    @pytest.mark.parametrize("paginate", (True, False))
    def test_etag_set_etag_in_response(self, app, schemas, paginate):
        blp = Blueprint("test", __name__)
        item = {"item_id": 1, "db_field": 0}
        if paginate:
            extra_data = (("X-Pagination", "Dummy pagination header"),)
        else:
            extra_data = tuple()
        etag = blp._generate_etag(item, extra_data=extra_data)

        with app.test_request_context("/"):
            resp = Response()
            if extra_data:
                resp.headers["X-Pagination"] = "Dummy pagination header"
            get_appcontext()["result_dump"] = item
            blp._set_etag_in_response(resp)
            assert resp.get_etag() == (etag, False)

    def test_etag_duplicate_header(self, app):
        """Check duplicate header results in a different ETag"""

        class CustomBlueprint(Blueprint):
            ETAG_INCLUDE_HEADERS = Blueprint.ETAG_INCLUDE_HEADERS + ["X-test"]

        blp = CustomBlueprint("test", __name__, url_prefix="/test")

        with app.test_request_context("/"):
            resp = Response()
            resp.headers.add("X-test", "Test")
            get_appcontext()["result_dump"] = {}
            blp._set_etag_in_response(resp)
            etag_1 = resp.get_etag()

        with app.test_request_context("/"):
            resp = Response()
            resp.headers.add("X-test", "Test")
            resp.headers.add("X-test", "Test")
            get_appcontext()["result_dump"] = {}
            blp._set_etag_in_response(resp)
            etag_2 = resp.get_etag()

        assert etag_1 != etag_2

    def test_etag_response_object(self, app):
        api = Api(app)
        blp = Blueprint("test", __name__, url_prefix="/test")
        client = app.test_client()

        @blp.route("/<code>")
        @blp.etag
        @blp.response(200)
        @blp.alt_response(201, success=True)
        def func_response_etag(code):
            # When the view function returns a Response object,
            # the ETag must be specified manually
            # This is always the case when using alt_response
            blp.set_etag("test")
            return jsonify({}), code

        api.register_blueprint(blp)

        response = client.get("/test/200")
        assert response.json == {}
        assert response.get_etag() == (blp._generate_etag("test"), False)
        response = client.get("/test/201")
        assert response.json == {}
        assert response.get_etag() == (blp._generate_etag("test"), False)

    def test_etag_operations_etag_enabled(self, app_with_etag):

        client = app_with_etag.test_client()

        # GET without ETag: OK
        response = client.get("/test/")
        assert response.status_code == 200
        list_etag = response.headers["ETag"]

        # GET with correct ETag: Not modified
        response = client.get("/test/", headers={"If-None-Match": list_etag})
        assert response.status_code == 304

        # POST item_1
        item_1_data = {"field": 0}
        response = client.post(
            "/test/", data=json.dumps(item_1_data), content_type="application/json"
        )
        assert response.status_code == 201
        item_1_id = response.json["item_id"]

        # GET with wrong/outdated ETag: OK
        response = client.get("/test/", headers={"If-None-Match": list_etag})
        assert response.status_code == 200

        # GET by ID without ETag: OK
        response = client.get(f"/test/{item_1_id}")
        assert response.status_code == 200
        item_etag = response.headers["ETag"]

        # GET by ID with correct ETag: Not modified
        response = client.get(
            f"/test/{item_1_id}", headers={"If-None-Match": item_etag}
        )
        assert response.status_code == 304

        # PUT without ETag: Precondition required error
        item_1_data["field"] = 1
        response = client.put(
            f"/test/{item_1_id}",
            data=json.dumps(item_1_data),
            content_type="application/json",
        )
        assert response.status_code == 428

        # PUT with correct ETag: OK
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
        response = client.put(
            f"/test/{item_1_id}",
            data=json.dumps(item_1_data),
            content_type="application/json",
            headers={"If-Match": item_etag},
        )
        assert response.status_code == 412

        # GET by ID with wrong/outdated ETag: OK
        response = client.get(
            f"/test/{item_1_id}", headers={"If-None-Match": item_etag}
        )
        assert response.status_code == 200

        # DELETE without ETag: Precondition required error
        response = client.delete(f"/test/{item_1_id}")
        assert response.status_code == 428

        # DELETE with wrong/outdated ETag: Precondition failed error
        response = client.delete(f"/test/{item_1_id}", headers={"If-Match": item_etag})
        assert response.status_code == 412

        # DELETE with correct ETag: No Content
        response = client.delete(
            f"/test/{item_1_id}", headers={"If-Match": new_item_etag}
        )
        assert response.status_code == 204

    def test_etag_operations_etag_disabled(self, app_with_etag):

        app_with_etag.config["ETAG_DISABLED"] = True
        client = app_with_etag.test_client()

        # GET without ETag: OK
        response = client.get("/test/")
        assert response.status_code == 200

        # GET with whatever ETag: OK (dummy ETag ignored)
        response = client.get("/test/", headers={"If-None-Match": "dummy_etag"})
        assert response.status_code == 200

        # POST item_1
        item_1_data = {"field": 0}
        response = client.post(
            "/test/", data=json.dumps(item_1_data), content_type="application/json"
        )
        assert response.status_code == 201
        item_1_id = response.json["item_id"]

        # GET by ID: OK
        response = client.get(f"/test/{item_1_id}")
        assert response.status_code == 200

        # GET by ID with whatever ETag: OK (dummy ETag ignored)
        response = client.get(
            f"/test/{item_1_id}", headers={"If-None-Match": "dummy_etag"}
        )
        assert response.status_code == 200

        # PUT without ETag: OK
        item_1_data["field"] = 1
        response = client.put(
            f"/test/{item_1_id}",
            data=json.dumps(item_1_data),
            content_type="application/json",
        )
        assert response.status_code == 200

        # PUT with whatever ETag: OK (dummy ETag ignored)
        item_1_data["field"] = 2
        response = client.put(
            f"/test/{item_1_id}",
            data=json.dumps(item_1_data),
            content_type="application/json",
        )
        assert response.status_code == 200

        # POST item_2
        item_2_data = {"field": 9}
        response = client.post(
            "/test/", data=json.dumps(item_2_data), content_type="application/json"
        )
        assert response.status_code == 201
        item_2_id = response.json["item_id"]

        # DELETE without ETag: No Content (dummy ETag ignored)
        response = client.delete(f"/test/{item_1_id}")
        assert response.status_code == 204

        # DELETE with whatever ETag: No Content (dummy ETag ignored)
        response = client.delete(
            f"/test/{item_2_id}", headers={"If-Match": "dummy_etag"}
        )
        assert response.status_code == 204

    @pytest.mark.parametrize("etag_disabled_for_v1", [False, True])
    @pytest.mark.parametrize("etag_disabled_for_v2", [False, True])
    def test_multiple_apis_per_app(
        self, app, etag_disabled_for_v1, etag_disabled_for_v2
    ):
        # All created APIs are using prefix. So default ETAG_DISABLED should be ignored
        app.config["ETAG_DISABLED"] = True
        app.config["V1_ETAG_DISABLED"] = etag_disabled_for_v1
        app.config["V2_ETAG_DISABLED"] = etag_disabled_for_v2

        for i in [1, 2]:
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

            class HomeSchema(ma.Schema):
                field = ma.fields.String()

            @blp.route("/")
            @blp.etag
            @blp.response(200, HomeSchema)
            def home():
                return {"field": "value"}

            api.register_blueprint(blp)

        client = app.test_client()
        headers1 = client.get("/test-1/").headers
        headers2 = client.get("/test-2/").headers

        if etag_disabled_for_v1:
            assert "ETag" not in headers1
        else:
            assert "ETag" in headers1

        if etag_disabled_for_v2:
            assert "ETag" not in headers2
        else:
            assert "ETag" in headers2
