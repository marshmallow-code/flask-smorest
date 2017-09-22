"""Test pagination feature"""

import ast

import pytest

from flask.views import MethodView

from flask_rest_api import Api, Blueprint
from flask_rest_api .pagination import set_item_count


@pytest.fixture(params=[True, False])
def app_with_pagination(request, collection, schemas, app):
    """Return a basic API sample with pagination"""

    as_method_view = request.param
    DocSchema = schemas.DocSchema
    blp = Blueprint('test', __name__, url_prefix='/test')

    if as_method_view:
        @blp.route('/')
        class Resource(MethodView):

            @blp.marshal_with(DocSchema, paginate=True)
            def get(self, first_item, last_item):
                set_item_count(len(collection.items))
                return collection.items[first_item: last_item + 1]

    else:
        @blp.route('/')
        @blp.marshal_with(DocSchema, paginate=True)
        def get_resources(first_item, last_item):
            set_item_count(len(collection.items))
            return collection.items[first_item: last_item + 1]

    api = Api(app)
    api.register_blueprint(blp)

    return app


class TestPagination():

    @pytest.mark.parametrize('collection', [1000, ], indirect=True)
    def test_pagination(self, app_with_pagination):

        client = app_with_pagination.test_client()

        # Default: page = 1, page_size = 10
        response = client.get('/test/')
        assert response.status_code == 200
        data = response.json
        headers = response.headers
        assert len(data) == 10
        assert data[0] == {'field': 0, 'item_id': 1}
        assert data[9] == {'field': 9, 'item_id': 10}
        assert ast.literal_eval(headers['X-Pagination']) == {'total': 1000}

        # page = 2, page_size = 5
        response = client.get(
            '/test/', query_string={'page': 2, 'page_size': 5})
        assert response.status_code == 200
        data = response.json
        headers = response.headers
        assert len(data) == 5
        assert data[0] == {'field': 5, 'item_id': 6}
        assert data[4] == {'field': 9, 'item_id': 10}
        assert ast.literal_eval(headers['X-Pagination']) == {'total': 1000}

        # page = 120, page_size = 10
        response = client.get(
            '/test/', query_string={'page': 120, 'page_size': 10})
        assert response.status_code == 200
        data = response.json
        headers = response.headers
        assert len(data) == 0
        assert ast.literal_eval(headers['X-Pagination']) == {'total': 1000}

        # page = 334, page_size = 3
        response = client.get(
            '/test/', query_string={'page': 334, 'page_size': 3})
        assert response.status_code == 200
        data = response.json
        headers = response.headers
        assert len(data) == 1
        assert ast.literal_eval(headers['X-Pagination']) == {'total': 1000}

        # page < 1 => 422
        response = client.get('/test/', query_string={'page': 0})
        assert response.status_code == 422
        response = client.get('/test/', query_string={'page': -42})
        assert response.status_code == 422

        # page_size < 1 => 422
        response = client.get('/test/', query_string={'page_size': 0})
        assert response.status_code == 422
        response = client.get('/test/', query_string={'page_size': -42})
        assert response.status_code == 422

        # page_size > 100 => 422
        response = client.get('/test/', query_string={'page_size': 101})
        assert response.status_code == 422
