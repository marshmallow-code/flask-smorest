"""Test flask-rest-api on more or less realistic examples"""

import ast
import json

import pytest

from flask.views import MethodView

from flask_rest_api import (
    Api, Blueprint, abort, check_etag, set_etag, Page, set_item_count)

from .conftest import AppConfig
from .mocks import ItemNotFound


class AppConfigFullExample(AppConfig):
    """Basic config with ETag feature enabled"""
    ETAG_ENABLED = True


def implicit_data_and_schema_etag_blueprint(collection, schemas):
    """Blueprint with implicit data and schema ETag computation

    ETag computed automatically from result data with same schema as data
    Post-pagination is used to reduce boilerplate even more
    """

    DocSchema = schemas.DocSchema

    blp = Blueprint('test', __name__, url_prefix='/test')

    @blp.route('/')
    class Resource(MethodView):

        @blp.response(DocSchema(many=True), paginate_with=Page)
        def get(self):
            return collection.items

        @blp.arguments(DocSchema)
        @blp.response(DocSchema, code=201)
        def post(self, new_item):
            return collection.post(new_item)

    @blp.route('/<int:item_id>')
    class ResourceById(MethodView):

        def _get_item(self, item_id):
            try:
                return collection.get_by_id(item_id)
            except ItemNotFound:
                abort(404)

        @blp.response(DocSchema)
        def get(self, item_id):
            return self._get_item(item_id)

        @blp.arguments(DocSchema)
        @blp.response(DocSchema)
        def put(self, new_item, item_id):
            item = self._get_item(item_id)
            # Check ETag is a manual action and schema must be provided
            check_etag(item, DocSchema)
            return collection.put(item_id, new_item)

        @blp.response(code=204)
        def delete(self, item_id):
            item = self._get_item(item_id)
            # Check ETag is a manual action and schema must be provided
            check_etag(item, DocSchema)
            del collection.items[collection.items.index(item)]

    return blp


def implicit_data_explicit_schema_etag_blueprint(collection, schemas):
    """Blueprint with implicit ETag computation, explicit schema

    ETag computed automatically with specific ETag schema
    """

    DocSchema = schemas.DocSchema
    DocEtagSchema = schemas.DocEtagSchema

    blp = Blueprint('test', __name__, url_prefix='/test')

    @blp.route('/')
    class Resource(MethodView):

        @blp.response(DocSchema(many=True), paginate=True,
                      etag_schema=DocEtagSchema)
        def get(self, first_item, last_item):
            set_item_count(len(collection.items))
            return collection.items[first_item: last_item + 1]

        @blp.arguments(DocSchema)
        @blp.response(DocSchema, code=201,
                      etag_schema=DocEtagSchema)
        def post(self, new_item):
            return collection.post(new_item)

    @blp.route('/<int:item_id>')
    class ResourceById(MethodView):

        def _get_item(self, item_id):
            try:
                return collection.get_by_id(item_id)
            except ItemNotFound:
                abort(404)

        @blp.response(DocSchema, etag_schema=DocEtagSchema)
        def get(self, item_id):
            item = self._get_item(item_id)
            return item

        @blp.arguments(DocSchema)
        @blp.response(DocSchema, etag_schema=DocEtagSchema)
        def put(self, new_item, item_id):
            item = self._get_item(item_id)
            # Check ETag is a manual action, ETag schema is used
            check_etag(item)
            new_item = collection.put(item_id, new_item)
            return new_item

        @blp.response(code=204, etag_schema=DocEtagSchema)
        def delete(self, item_id):
            item = self._get_item(item_id)
            # Check ETag is a manual action, ETag schema is used
            check_etag(item)
            del collection.items[collection.items.index(item)]

    return blp


def explicit_data_no_schema_etag_blueprint(collection, schemas):
    """Blueprint with explicit ETag computation, no schema

    ETag computed without schema from arbitrary data

    We're using item['db_field'] for ETag data as a dummy example.
    """

    DocSchema = schemas.DocSchema

    blp = Blueprint('test', __name__, url_prefix='/test')

    @blp.route('/')
    class Resource(MethodView):

        @blp.response(DocSchema(many=True), paginate=True)
        def get(self, first_item, last_item):
            set_item_count(len(collection.items))
            return collection.items[first_item: last_item + 1]

        @blp.arguments(DocSchema)
        @blp.response(DocSchema, code=201)
        def post(self, new_item):
            # Compute ETag using arbitrary data and no schema
            set_etag(new_item['db_field'])
            return collection.post(new_item)

    @blp.route('/<int:item_id>')
    class ResourceById(MethodView):

        def _get_item(self, item_id):
            try:
                return collection.get_by_id(item_id)
            except ItemNotFound:
                abort(404)

        @blp.response(DocSchema)
        def get(self, item_id):
            item = self._get_item(item_id)
            # Compute ETag using arbitrary data and no schema
            set_etag(item['db_field'])
            return item

        @blp.arguments(DocSchema)
        @blp.response(DocSchema)
        def put(self, new_item, item_id):
            item = self._get_item(item_id)
            # Check ETag is a manual action, no shema used
            check_etag(item['db_field'])
            new_item = collection.put(item_id, new_item)
            # Compute ETag using arbitrary data and no schema
            set_etag(new_item['db_field'])
            return new_item

        @blp.response(code=204)
        def delete(self, item_id):
            item = self._get_item(item_id)
            # Check ETag is a manual action, no shema used
            check_etag(item['db_field'])
            del collection.items[collection.items.index(item)]

    return blp


@pytest.fixture(params=[
    implicit_data_and_schema_etag_blueprint,
    implicit_data_explicit_schema_etag_blueprint,
    explicit_data_no_schema_etag_blueprint,
])
def blueprint(request, collection, schemas):
    blp_factory = request.param
    return blp_factory(collection, schemas)


class TestFullExample():

    @pytest.mark.parametrize('app', [AppConfigFullExample], indirect=True)
    def test_examples(self, app, blueprint):

        api = Api(app)
        api.register_blueprint(blueprint)

        client = app.test_client()

        # GET collection without ETag: OK
        response = client.get('/test/')
        assert response.status_code == 200
        list_etag = response.headers['ETag']
        assert len(response.json) == 0
        assert ast.literal_eval(response.headers['X-Pagination']) == {
            'total': 0, 'total_pages': 0}

        # GET collection with correct ETag: Not modified
        response = client.get(
            '/test/',
            headers={'If-None-Match': list_etag}
        )
        assert response.status_code == 304

        # POST item_1
        item_1_data = {'field': 0}
        response = client.post(
            '/test/',
            data=json.dumps(item_1_data),
            content_type='application/json'
        )
        assert response.status_code == 201
        item_1_id = response.json['item_id']

        # GET collection with wrong/outdated ETag: OK
        response = client.get(
            '/test/',
            headers={'If-None-Match': list_etag}
        )
        assert response.status_code == 200
        list_etag = response.headers['ETag']
        assert len(response.json) == 1
        assert response.json[0] == {'field': 0, 'item_id': 1}
        assert ast.literal_eval(response.headers['X-Pagination']) == {
            'total': 1, 'total_pages': 1, 'first_page': 1, 'last_page': 1}

        # GET by ID without ETag: OK
        response = client.get('/test/{}'.format(item_1_id))
        assert response.status_code == 200
        item_etag = response.headers['ETag']

        # GET by ID with correct ETag: Not modified
        response = client.get(
            '/test/{}'.format(item_1_id),
            headers={'If-None-Match': item_etag}
        )
        assert response.status_code == 304

        # PUT without ETag: Precondition required error
        item_1_data['field'] = 1
        response = client.put(
            '/test/{}'.format(item_1_id),
            data=json.dumps(item_1_data),
            content_type='application/json'
        )
        assert response.status_code == 428

        # PUT with correct ETag: OK
        response = client.put(
            '/test/{}'.format(item_1_id),
            data=json.dumps(item_1_data),
            content_type='application/json',
            headers={'If-Match': item_etag}
        )
        assert response.status_code == 200
        new_item_etag = response.headers['ETag']

        # PUT with wrong/outdated ETag: Precondition failed error
        item_1_data['field'] = 2
        response = client.put(
            '/test/{}'.format(item_1_id),
            data=json.dumps(item_1_data),
            content_type='application/json',
            headers={'If-Match': item_etag}
        )
        assert response.status_code == 412

        # GET by ID with wrong/outdated ETag: OK
        response = client.get(
            '/test/{}'.format(item_1_id),
            headers={'If-None-Match': item_etag}
        )
        assert response.status_code == 200

        # GET collection with pagination set to 1 element per page
        response = client.get(
            '/test/',
            headers={'If-None-Match': list_etag},
            query_string={'page': 1, 'page_size': 1}
        )
        assert response.status_code == 200
        list_etag = response.headers['ETag']
        assert len(response.json) == 1
        assert response.json[0] == {'field': 1, 'item_id': 1}
        assert ast.literal_eval(response.headers['X-Pagination']) == {
            'total': 1, 'total_pages': 1, 'first_page': 1, 'last_page': 1}

        # POST item_2
        item_2_data = {'field': 1}
        response = client.post(
            '/test/',
            data=json.dumps(item_2_data),
            content_type='application/json'
        )
        assert response.status_code == 201

        # GET collection with pagination set to 1 element per page
        # Content is the same (item_1) but pagination metadata has changed
        # so we don't get a 304 and the data is returned again
        response = client.get(
            '/test/',
            headers={'If-None-Match': list_etag},
            query_string={'page': 1, 'page_size': 1}
        )
        assert response.status_code == 200
        list_etag = response.headers['ETag']
        assert len(response.json) == 1
        assert response.json[0] == {'field': 1, 'item_id': 1}
        assert ast.literal_eval(response.headers['X-Pagination']) == {
            'total': 2, 'total_pages': 2, 'first_page': 1, 'last_page': 2,
            'next_page': 2}

        # DELETE without ETag: Precondition required error
        response = client.delete('/test/{}'.format(item_1_id))
        assert response.status_code == 428

        # DELETE with wrong/outdated ETag: Precondition failed error
        response = client.delete(
            '/test/{}'.format(item_1_id),
            headers={'If-Match': item_etag}
        )
        assert response.status_code == 412

        # DELETE with correct ETag: No Content
        response = client.delete(
            '/test/{}'.format(item_1_id),
            headers={'If-Match': new_item_etag}
        )
        assert response.status_code == 204
