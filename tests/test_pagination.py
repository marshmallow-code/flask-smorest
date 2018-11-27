"""Test pagination feature"""

from itertools import product
from collections import namedtuple
import json
from unittest import mock

import pytest

from flask.views import MethodView

from flask_rest_api import Api, Blueprint, Page
from flask_rest_api.pagination import PaginationParameters


CUSTOM_PAGINATION_PARAMS = (2, 5, 10)


def pagination_blueprint(collection, schemas, as_method_view, custom_params):
    """Return a basic API sample with pagination"""

    DocSchema = schemas.DocSchema

    blp = Blueprint('test', __name__, url_prefix='/test')

    if custom_params:
        page, page_size, max_page_size = CUSTOM_PAGINATION_PARAMS
    else:
        page, page_size, max_page_size = None, None, None

    if as_method_view:
        @blp.route('/')
        class Resource(MethodView):
            @blp.response(DocSchema(many=True))
            @blp.paginate(
                page=page, page_size=page_size, max_page_size=max_page_size)
            def get(self, pagination_parameters):
                pagination_parameters.item_count = len(collection.items)
                return collection.items[
                    pagination_parameters.first_item:
                    pagination_parameters.last_item + 1
                ]
    else:
        @blp.route('/')
        @blp.response(DocSchema(many=True))
        @blp.paginate(
            page=page, page_size=page_size, max_page_size=max_page_size)
        def get_resources(pagination_parameters):
                pagination_parameters.item_count = len(collection.items)
                return collection.items[
                    pagination_parameters.first_item:
                    pagination_parameters.last_item + 1
                ]

    return blp


def post_pagination_blueprint(
        collection, schemas, as_method_view, custom_params):
    """Return a basic API sample with post-pagination"""

    DocSchema = schemas.DocSchema

    blp = Blueprint('test', __name__, url_prefix='/test')

    if custom_params:
        page, page_size, max_page_size = CUSTOM_PAGINATION_PARAMS
    else:
        page, page_size, max_page_size = None, None, None

    if as_method_view:
        @blp.route('/')
        class Resource(MethodView):
            @blp.response(DocSchema(many=True))
            @blp.paginate(Page, page=page,
                          page_size=page_size, max_page_size=max_page_size)
            def get(self):
                return collection.items
    else:
        @blp.route('/')
        @blp.response(DocSchema(many=True))
        @blp.paginate(Page, page=page,
                      page_size=page_size, max_page_size=max_page_size)
        def get_resources():
            return collection.items

    return blp


@pytest.fixture(params=product(
    # Pagination in function/ post-pagination
    (pagination_blueprint, post_pagination_blueprint),
    # MethodView
    (True, False),
    # Custom parameters
    (True, False),
))
def app_fixture(request, collection, schemas, app):
    """Return an app client for each configuration

    - pagination in function / post-pagination
    - function / method view
    - default / custom pagination parameters
    """
    blp_factory, as_method_view, custom_params = request.param
    blueprint = blp_factory(collection, schemas, as_method_view, custom_params)
    api = Api(app)
    api.register_blueprint(app, blueprint)
    return namedtuple('AppFixture', ('client', 'custom_params'))(
        app.test_client(), custom_params)


class TestPagination():

    def test_pagination_parameters_repr(self):
        assert(repr(PaginationParameters(1, 10)) ==
               "PaginationParameters(page=1,page_size=10)")

    def test_page_repr(self):
        page_params = PaginationParameters(1, 2)
        assert (repr(Page([1, 2, 3, 4, 5], page_params)) ==
                "Page(collection=[1, 2, 3, 4, 5],page_params={})"
                .format(repr(page_params)))

    @pytest.mark.parametrize('header_name', ('X-Dummy-Name', None))
    def test_pagination_custom_header_field_name(self, app, header_name):
        """Test PAGINATION_HEADER_FIELD_NAME overriding"""
        api = Api(app)

        class CustomBlueprint(Blueprint):
            PAGINATION_HEADER_FIELD_NAME = header_name

        blp = CustomBlueprint('test', __name__, url_prefix='/test')

        @blp.route('/')
        @blp.response()
        @blp.paginate()
        def func(pagination_parameters):
            pagination_parameters.item_count = 2
            return [1, 2]

        api.register_blueprint(app, blp)
        client = app.test_client()
        response = client.get('/test/')
        assert response.status_code == 200
        assert 'X-Pagination' not in response.headers
        if header_name is not None:
            assert response.headers[header_name] == (
                '{"total": 2, "total_pages": 1, '
                '"first_page": 1, "last_page": 1, "page": 1}'
            )

    @pytest.mark.parametrize('header_name', ('X-Pagination', None))
    def test_pagination_item_count_missing(self, app, header_name):
        """If item_count was not set, pass and warn"""
        api = Api(app)

        class CustomBlueprint(Blueprint):
            PAGINATION_HEADER_FIELD_NAME = header_name

        blp = CustomBlueprint('test', __name__, url_prefix='/test')

        @blp.route('/')
        @blp.response()
        @blp.paginate()
        def func(pagination_parameters):
            # Here, we purposely forget to call set_item_count
            # pagination_parameters.item_count = 2
            return [1, 2]

        api.register_blueprint(app, blp)
        client = app.test_client()

        with mock.patch.object(app.logger, 'warning') as mock_warning:
            response = client.get('/test/')
            assert response.status_code == 200
            assert 'X-Pagination' not in response.headers
            if header_name is None:
                assert mock_warning.call_count == 0
            else:
                assert mock_warning.call_count == 1
                assert mock_warning.call_args == (
                    ('item_count not set in endpoint test.func',), )

    @pytest.mark.parametrize('collection', [1000, ], indirect=True)
    def test_pagination_parameters(self, app_fixture):
        # page = 2, page_size = 5
        response = app_fixture.client.get(
            '/test/', query_string={'page': 2, 'page_size': 5})
        assert response.status_code == 200
        data = response.json
        headers = response.headers
        assert len(data) == 5
        assert data[0] == {'field': 5, 'item_id': 6}
        assert data[4] == {'field': 9, 'item_id': 10}
        assert json.loads(headers['X-Pagination']) == {
            'total': 1000, 'total_pages': 200,
            'page': 2, 'first_page': 1, 'last_page': 200,
            'previous_page': 1, 'next_page': 3,
        }
        # page = 334, page_size = 3
        # last page is incomplete if total not multiple of page_size
        response = app_fixture.client.get(
            '/test/', query_string={'page': 334, 'page_size': 3})
        assert response.status_code == 200
        data = response.json
        headers = response.headers
        assert len(data) == 1
        assert json.loads(headers['X-Pagination']) == {
            'total': 1000, 'total_pages': 334,
            'page': 334, 'first_page': 1, 'last_page': 334,
            'previous_page': 333,
        }

    @pytest.mark.parametrize('collection', [1000, ], indirect=True)
    def test_pagination_parameters_default_page_page_size(self, app_fixture):
        # Default: page = 1, page_size = 10
        # Custom: page = 2, page_size = 5
        response = app_fixture.client.get('/test/')
        assert response.status_code == 200
        data = response.json
        headers = response.headers
        if app_fixture.custom_params is False:
            assert len(data) == 10
            assert data[0] == {'field': 0, 'item_id': 1}
            assert data[9] == {'field': 9, 'item_id': 10}
            assert json.loads(headers['X-Pagination']) == {
                'total': 1000, 'total_pages': 100,
                'page': 1, 'first_page': 1, 'last_page': 100,
                'next_page': 2,
            }
        else:
            assert len(data) == 5
            assert data[0] == {'field': 5, 'item_id': 6}
            assert data[4] == {'field': 9, 'item_id': 10}
            assert json.loads(headers['X-Pagination']) == {
                'total': 1000, 'total_pages': 200,
                'page': 2, 'first_page': 1, 'last_page': 200,
                'previous_page': 1, 'next_page': 3,
            }

    def test_pagination_empty_collection(self, app_fixture):
        # empty collection -> 200 with empty list, partial pagination metadata
        response = app_fixture.client.get('/test/')
        assert response.status_code == 200
        assert json.loads(response.headers['X-Pagination']) == {
            'total': 0, 'total_pages': 0,
        }
        assert response.json == []

    @pytest.mark.parametrize('collection', [1000, ], indirect=True)
    def test_pagination_page_out_of_range(self, app_fixture):
        # page = 120, page_size = 10
        # page out of range -> 200 with empty list, partial pagination metadata
        response = app_fixture.client.get(
            '/test/', query_string={'page': 120, 'page_size': 10})
        assert response.status_code == 200
        assert json.loads(response.headers['X-Pagination']) == {
            'total': 1000, 'total_pages': 100,
            'first_page': 1, 'last_page': 100,
        }
        assert response.json == []

    @pytest.mark.parametrize('collection', [1000, ], indirect=True)
    def test_pagination_min_page_page_size(self, app_fixture):
        client = app_fixture.client
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

    @pytest.mark.parametrize('collection', [1000, ], indirect=True)
    def test_pagination_max_page_size(self, app_fixture):
        client = app_fixture.client
        # default: page_size > 100 => 422
        # custom: page_size > 10 => 422
        response = client.get('/test/', query_string={'page_size': 101})
        assert response.status_code == 422
        response = client.get('/test/', query_string={'page_size': 11})
        if app_fixture.custom_params is False:
            assert response.status_code == 200
        else:
            assert response.status_code == 422
