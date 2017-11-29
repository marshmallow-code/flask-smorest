"""Test pagination feature"""

import ast

import pytest

from flask.views import MethodView

from flask_rest_api import Api, Blueprint, Page, set_item_count
from flask_rest_api.pagination import PaginationParameters, PaginationMetadata


def pagination_blueprint(collection, schemas, as_method_view):
    """Return a basic API sample with pagination"""

    DocSchema = schemas.DocSchema

    blp = Blueprint('test', __name__, url_prefix='/test')

    if as_method_view:
        @blp.route('/')
        class Resource(MethodView):
            @blp.response(DocSchema, paginate=True)
            def get(self, first_item, last_item):
                set_item_count(len(collection.items))
                return collection.items[first_item: last_item + 1]
    else:
        @blp.route('/')
        @blp.response(DocSchema, paginate=True)
        def get_resources(first_item, last_item):
            set_item_count(len(collection.items))
            return collection.items[first_item: last_item + 1]

    return blp


def post_pagination_blueprint(collection, schemas, as_method_view):
    """Return a basic API sample with post-pagination"""

    DocSchema = schemas.DocSchema

    blp = Blueprint('test', __name__, url_prefix='/test')

    if as_method_view:
        @blp.route('/')
        class Resource(MethodView):
            @blp.response(DocSchema, paginate_with=Page)
            def get(self):
                return collection.items
    else:
        @blp.route('/')
        @blp.response(DocSchema, paginate_with=Page)
        def get_resources():
            return collection.items

    return blp


@pytest.fixture(params=[
    (pagination_blueprint, True),
    (pagination_blueprint, False),
    (post_pagination_blueprint, True),
    (post_pagination_blueprint, False),
])
def blueprint(request, collection, schemas):
    blp_factory, as_method_view = request.param
    return blp_factory(collection, schemas, as_method_view)


class TestPagination():

    def test_pagination_parameters_repr(self):
        assert(repr(PaginationParameters(1, 10)) ==
               "PaginationParameters(page=1,page_size=10)")

    def test_pagination_metadata_repr(self):
        assert(repr(PaginationMetadata(1, 10, 12)) ==
               "PaginationMetadata(page=1,page_size=10,item_count=12)")

    def test_page_repr(self):
        page_params = PaginationParameters(1, 2)
        assert (repr(Page([1, 2, 3, 4, 5], page_params)) ==
                "Page(collection=[1, 2, 3, 4, 5],page_params={})"
                .format(repr(page_params)))

    @pytest.mark.parametrize('collection', [1000, ], indirect=True)
    def test_pagination(self, app, blueprint):

        api = Api(app)
        api.register_blueprint(blueprint)

        client = app.test_client()

        # Default: page = 1, page_size = 10
        response = client.get('/test/')
        assert response.status_code == 200
        data = response.json
        headers = response.headers
        assert len(data) == 10
        assert data[0] == {'field': 0, 'item_id': 1}
        assert data[9] == {'field': 9, 'item_id': 10}
        assert ast.literal_eval(headers['X-Pagination']) == {
            'total': 1000, 'total_pages': 100,
            'first_page': 1, 'last_page': 100,
            'next_page': 2,
        }

        # page = 2, page_size = 5
        response = client.get(
            '/test/', query_string={'page': 2, 'page_size': 5})
        assert response.status_code == 200
        data = response.json
        headers = response.headers
        assert len(data) == 5
        assert data[0] == {'field': 5, 'item_id': 6}
        assert data[4] == {'field': 9, 'item_id': 10}
        assert ast.literal_eval(headers['X-Pagination']) == {
            'total': 1000, 'total_pages': 200,
            'first_page': 1, 'last_page': 200,
            'previous_page': 1, 'next_page': 3,
        }

        # page = 120, page_size = 10: page out of range -> 404
        response = client.get(
            '/test/', query_string={'page': 120, 'page_size': 10})
        assert response.status_code == 404
        assert 'errors' in response.json

        # page = 334, page_size = 3
        response = client.get(
            '/test/', query_string={'page': 334, 'page_size': 3})
        assert response.status_code == 200
        data = response.json
        headers = response.headers
        assert len(data) == 1
        assert ast.literal_eval(headers['X-Pagination']) == {
            'total': 1000, 'total_pages': 334,
            'first_page': 1, 'last_page': 334,
            'previous_page': 333,
        }

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
