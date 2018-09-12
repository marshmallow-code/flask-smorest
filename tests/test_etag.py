"""Test ETag feature"""

from collections import OrderedDict
import json
import hashlib
from unittest import mock

import pytest

from flask import current_app, Response
from flask.views import MethodView

from flask_rest_api import Api, Blueprint, abort, check_etag, set_etag
from flask_rest_api.etag import (
    _generate_etag, is_etag_enabled,
    disable_etag_for_request, is_etag_enabled_for_request, _get_etag_ctx,
    check_precondition, set_etag_in_response, verify_check_etag)
from flask_rest_api.exceptions import (
    NotModified, PreconditionRequired, PreconditionFailed)
from flask_rest_api.blueprint import HTTP_METHODS
from flask_rest_api.compat import MARSHMALLOW_VERSION_MAJOR

from .mocks import ItemNotFound
from .conftest import AppConfig


class AppConfigEtagEnabled(AppConfig):
    """Basic config with ETag feature enabled"""
    ETAG_ENABLED = True


@pytest.fixture(params=[True, False])
def app_with_etag(request, collection, schemas, app):
    """Return a basic API sample with ETag"""

    as_method_view = request.param
    DocSchema = schemas.DocSchema
    DocEtagSchema = schemas.DocEtagSchema
    blp = Blueprint('test', __name__, url_prefix='/test')

    if as_method_view:
        @blp.route('/')
        class Resource(MethodView):

            @blp.response(
                DocSchema(many=True), etag_schema=DocEtagSchema(many=True))
            def get(self):
                return collection.items

            @blp.arguments(DocSchema)
            @blp.response(DocSchema, code=201, etag_schema=DocEtagSchema)
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
                return self._get_item(item_id)

            @blp.arguments(DocSchema)
            @blp.response(DocSchema, etag_schema=DocEtagSchema)
            def put(self, new_item, item_id):
                item = self._get_item(item_id)
                check_etag(item, DocEtagSchema)
                return collection.put(item_id, new_item)

            @blp.response(code=204, etag_schema=DocEtagSchema)
            def delete(self, item_id):
                item = self._get_item(item_id)
                check_etag(item, DocEtagSchema)
                del collection.items[collection.items.index(item)]

    else:
        @blp.route('/')
        @blp.response(
            DocSchema(many=True), etag_schema=DocEtagSchema(many=True))
        def get_resources():
            return collection.items

        @blp.route('/', methods=('POST',))
        @blp.arguments(DocSchema)
        @blp.response(DocSchema, code=201, etag_schema=DocEtagSchema)
        def post_resource(new_item):
            return collection.post(new_item)

        def _get_item(item_id):
            try:
                return collection.get_by_id(item_id)
            except ItemNotFound:
                abort(404)

        @blp.route('/<int:item_id>')
        @blp.response(
            DocSchema, etag_schema=DocEtagSchema)
        def get_resource(item_id):
            return _get_item(item_id)

        @blp.route('/<int:item_id>', methods=('PUT',))
        @blp.arguments(DocSchema)
        @blp.response(
            DocSchema, etag_schema=DocEtagSchema)
        def put_resource(new_item, item_id):
            item = _get_item(item_id)
            check_etag(item)
            return collection.put(item_id, new_item)

        @blp.route('/<int:item_id>', methods=('DELETE',))
        @blp.response(
            code=204, etag_schema=DocEtagSchema)
        def delete_resource(item_id):
            item = _get_item(item_id)
            check_etag(item)
            del collection.items[collection.items.index(item)]

    api = Api(app)
    api.register_blueprint(blp)

    return app


class TestEtag():

    def test_etag_is_deterministic(self):
        """Check etag computation is deterministic

           _generate_etag should return the same value everytime the same
           dictionary is passed. This is not obvious since dictionaries
           are unordered by design. We check this by feeding it different
           OrderedDict instances that are equivalent to the same dictionary.
        """

        data = OrderedDict([
            ('a', 1),
            ('b', 2),
            ('c', OrderedDict([('a', 1), ('b', 2)]))
        ])
        etag = _generate_etag(data)

        data_copies = [
            OrderedDict([
                ('b', 2),
                ('a', 1),
                ('c', OrderedDict([('a', 1), ('b', 2)])),
            ]),
            OrderedDict([
                ('a', 1),
                ('b', 2),
                ('c', OrderedDict([('b', 2), ('a', 1)])),
            ]),
            OrderedDict([
                ('a', 1),
                ('c', OrderedDict([('a', 1), ('b', 2)])),
                ('b', 2),
            ]),
            OrderedDict([
                ('c', OrderedDict([('a', 1), ('b', 2)])),
                ('b', 2),
                ('a', 1),
            ]),
        ]

        data_copies_etag = [_generate_etag(d) for d in data_copies]
        assert all(e == etag for e in data_copies_etag)

    @pytest.mark.parametrize('extra_data', [None, {}, {'answer': 42}])
    def test_etag_generate_etag(self, schemas, extra_data):
        etag_schema = schemas.DocEtagSchema
        item = {'item_id': 1, 'db_field': 0}
        item_schema_dump = etag_schema().dump(item)
        if MARSHMALLOW_VERSION_MAJOR < 3:
            item_schema_dump = item_schema_dump[0]
        if extra_data is None or extra_data == {}:
            data = item
            data_dump = item_schema_dump
        else:
            data = (item, extra_data)
            data_dump = (item_schema_dump, extra_data)

        etag = _generate_etag(item, extra_data=extra_data)
        assert etag == hashlib.sha1(
            bytes(json.dumps(data, sort_keys=True), 'utf-8')
            ).hexdigest()
        etag = _generate_etag(item, etag_schema, extra_data=extra_data)
        assert etag == hashlib.sha1(
            bytes(json.dumps(data_dump, sort_keys=True), 'utf-8')
            ).hexdigest()
        etag = _generate_etag(item, etag_schema(), extra_data=extra_data)
        assert etag == hashlib.sha1(
            bytes(json.dumps(data_dump, sort_keys=True), 'utf-8')
            ).hexdigest()

    @pytest.mark.parametrize(
        'app', [AppConfig, AppConfigEtagEnabled], indirect=True)
    def test_etag_is_etag_enabled_for_request(self, app):

        with app.test_request_context('/'):
            assert (
                is_etag_enabled_for_request() == is_etag_enabled(current_app))
            disable_etag_for_request()
            assert not is_etag_enabled_for_request()

    @pytest.mark.parametrize(
        'app', [AppConfig, AppConfigEtagEnabled], indirect=True)
    @pytest.mark.parametrize('method', HTTP_METHODS)
    def test_etag_check_precondition(self, app, method):

        with app.test_request_context('/', method=method):
            if method in ['PUT', 'PATCH', 'DELETE'] and is_etag_enabled(app):
                with pytest.raises(PreconditionRequired):
                    check_precondition()
            else:
                check_precondition()
            disable_etag_for_request()
            check_precondition()

    @pytest.mark.parametrize(
        'app', [AppConfig, AppConfigEtagEnabled], indirect=True)
    def test_etag_check_etag(self, app, schemas):

        etag_schema = schemas.DocEtagSchema
        old_item = {'item_id': 1, 'db_field': 0}
        new_item = {'item_id': 1, 'db_field': 1}

        old_etag = _generate_etag(old_item)
        old_etag_with_schema = _generate_etag(old_item, etag_schema)

        with app.test_request_context('/', headers={'If-Match': old_etag}):
            check_etag(old_item)
            if is_etag_enabled(app):
                with pytest.raises(PreconditionFailed):
                    check_etag(new_item)
            else:
                check_etag(new_item)
            disable_etag_for_request()
            check_etag(old_item)
            check_etag(new_item)
        with app.test_request_context(
                '/', headers={'If-Match': old_etag_with_schema}):
            check_etag(old_item, etag_schema)
            if is_etag_enabled(app):
                with pytest.raises(PreconditionFailed):
                    check_etag(new_item, etag_schema)
            else:
                check_etag(new_item)
            disable_etag_for_request()
            check_etag(old_item)
            check_etag(new_item)

    @pytest.mark.parametrize(
        'app', [AppConfig, AppConfigEtagEnabled], indirect=True)
    @pytest.mark.parametrize('method', HTTP_METHODS)
    def test_etag_verify_check_etag(self, app, method):

        old_item = {'item_id': 1, 'db_field': 0}
        old_etag = _generate_etag(old_item)

        with mock.patch.object(app.logger, 'warning') as mock_warning:
            with app.test_request_context('/', method=method,
                                          headers={'If-Match': old_etag}):
                verify_check_etag()
                if (is_etag_enabled(app) and
                        method in ['PUT', 'PATCH', 'DELETE']):
                    assert mock_warning.called
                    mock_warning.reset_mock()
                else:
                    assert not mock_warning.called
                check_etag(old_item)
                verify_check_etag()
                assert not mock_warning.called
                disable_etag_for_request()
                verify_check_etag()
                assert not mock_warning.called
                check_etag(old_item)
                verify_check_etag()
                assert not mock_warning.called

    @pytest.mark.parametrize(
        'app', [AppConfig, AppConfigEtagEnabled], indirect=True)
    def test_etag_set_etag(self, app, schemas):

        etag_schema = schemas.DocEtagSchema
        item = {'item_id': 1, 'db_field': 0}

        etag = _generate_etag(item)
        etag_with_schema = _generate_etag(item, etag_schema)

        with app.test_request_context('/'):
            set_etag(item)
            if is_etag_enabled(app):
                assert _get_etag_ctx()['etag'] == etag
                del _get_etag_ctx()['etag']
            else:
                assert 'etag' not in _get_etag_ctx()
            disable_etag_for_request()
            set_etag(item)
            assert 'etag' not in _get_etag_ctx()
        with app.test_request_context(
                '/', headers={'If-None-Match': etag}):
            if is_etag_enabled(app):
                with pytest.raises(NotModified):
                    set_etag(item)
            else:
                set_etag(item)
                assert 'etag' not in _get_etag_ctx()
            disable_etag_for_request()
            set_etag(item)
            assert 'etag' not in _get_etag_ctx()
        with app.test_request_context(
                '/', headers={'If-None-Match': etag_with_schema}):
            if is_etag_enabled(app):
                with pytest.raises(NotModified):
                    set_etag(item, etag_schema)
            else:
                set_etag(item, etag_schema)
                assert 'etag' not in _get_etag_ctx()
            disable_etag_for_request()
            set_etag(item, etag_schema)
            assert 'etag' not in _get_etag_ctx()
        with app.test_request_context(
                '/', headers={'If-None-Match': 'dummy'}):
            if is_etag_enabled(app):
                set_etag(item)
                assert _get_etag_ctx()['etag'] == etag
                del _get_etag_ctx()['etag']
                set_etag(item, etag_schema)
                assert _get_etag_ctx()['etag'] == etag_with_schema
                del _get_etag_ctx()['etag']
            else:
                set_etag(item)
                assert 'etag' not in _get_etag_ctx()
                set_etag(item, etag_schema)
                assert 'etag' not in _get_etag_ctx()
            disable_etag_for_request()
            set_etag(item)
            assert 'etag' not in _get_etag_ctx()
            set_etag(item, etag_schema)
            assert 'etag' not in _get_etag_ctx()

    @pytest.mark.parametrize(
        'app', [AppConfig, AppConfigEtagEnabled], indirect=True)
    @pytest.mark.parametrize('method', HTTP_METHODS)
    def test_set_etag_method_not_allowed_warning(self, app, method):

        with mock.patch.object(app.logger, 'warning') as mock_warning:
            with app.test_request_context('/', method=method):
                set_etag(None)
            if method in ['GET', 'HEAD', 'POST', 'PUT', 'PATCH']:
                assert not mock_warning.called
            else:
                assert mock_warning.called

    @pytest.mark.parametrize(
        'app', [AppConfig, AppConfigEtagEnabled], indirect=True)
    @pytest.mark.parametrize('paginate', (True, False))
    def test_etag_set_etag_in_response(self, app, schemas, paginate):

        etag_schema = schemas.DocEtagSchema
        item = {'item_id': 1, 'db_field': 0}
        extra_data = ('Dummy pagination header', ) if paginate else tuple()
        etag = _generate_etag(item, extra_data=extra_data)
        etag_with_schema = _generate_etag(
            item, etag_schema, extra_data=extra_data)

        with app.test_request_context('/'):
            resp = Response()
            if extra_data:
                resp.headers['X-Pagination'] = 'Dummy pagination header'
            if is_etag_enabled(app):
                set_etag_in_response(resp, item, None)
                assert resp.get_etag() == (etag, False)
                set_etag_in_response(resp, item, etag_schema)
                assert resp.get_etag() == (etag_with_schema, False)
            else:
                set_etag_in_response(resp, item, None)
                assert resp.get_etag() == (None, None)
                set_etag_in_response(resp, item, etag_schema)
                assert resp.get_etag() == (None, None)
            disable_etag_for_request()
            resp = Response()
            set_etag_in_response(resp, item, None)
            assert resp.get_etag() == (None, None)
            set_etag_in_response(resp, item, etag_schema)
            assert resp.get_etag() == (None, None)

    @pytest.mark.parametrize('app', [AppConfigEtagEnabled], indirect=True)
    def test_etag_operations_etag_enabled(self, app_with_etag):

        client = app_with_etag.test_client()
        assert is_etag_enabled(app_with_etag)

        # GET without ETag: OK
        response = client.get('/test/')
        assert response.status_code == 200
        list_etag = response.headers['ETag']

        # GET with correct ETag: Not modified
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

        # GET with wrong/outdated ETag: OK
        response = client.get(
            '/test/',
            headers={'If-None-Match': list_etag}
        )
        assert response.status_code == 200

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

    def test_etag_operations_etag_disabled(self, app_with_etag):

        client = app_with_etag.test_client()
        assert not is_etag_enabled(app_with_etag)

        # GET without ETag: OK
        response = client.get('/test/')
        assert response.status_code == 200

        # GET with whatever ETag: OK (dummy ETag ignored)
        response = client.get(
            '/test/',
            headers={'If-None-Match': 'dummy_etag'}
        )
        assert response.status_code == 200

        # POST item_1
        item_1_data = {'field': 0}
        response = client.post(
            '/test/',
            data=json.dumps(item_1_data),
            content_type='application/json'
        )
        assert response.status_code == 201
        item_1_id = response.json['item_id']

        # GET by ID: OK
        response = client.get('/test/{}'.format(item_1_id))
        assert response.status_code == 200

        # GET by ID with whatever ETag: OK (dummy ETag ignored)
        response = client.get(
            '/test/{}'.format(item_1_id),
            headers={'If-None-Match': 'dummy_etag'}
        )
        assert response.status_code == 200

        # PUT without ETag: OK
        item_1_data['field'] = 1
        response = client.put(
            '/test/{}'.format(item_1_id),
            data=json.dumps(item_1_data),
            content_type='application/json'
        )
        assert response.status_code == 200

        # PUT with whatever ETag: OK (dummy ETag ignored)
        item_1_data['field'] = 2
        response = client.put(
            '/test/{}'.format(item_1_id),
            data=json.dumps(item_1_data),
            content_type='application/json'
        )
        assert response.status_code == 200

        # POST item_2
        item_2_data = {'field': 9}
        response = client.post(
            '/test/',
            data=json.dumps(item_2_data),
            content_type='application/json'
        )
        assert response.status_code == 201
        item_2_id = response.json['item_id']

        # DELETE without ETag: No Content (dummy ETag ignored)
        response = client.delete('/test/{}'.format(item_1_id))
        assert response.status_code == 204

        # DELETE with whatever ETag: No Content (dummy ETag ignored)
        response = client.delete(
            '/test/{}'.format(item_2_id),
            headers={'If-Match': 'dummy_etag'}
        )
        assert response.status_code == 204
