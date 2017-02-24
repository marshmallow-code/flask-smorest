"""Test ETag feature"""

from collections import OrderedDict
import json

import pytest

from werkzeug.datastructures import Headers

from flask_rest_api.etag import generate_etag, is_etag_enabled

from .mocks import AppConfig


class AppConfigEtagDisabled(AppConfig):
    """Basic config with ETag feature disabled"""
    ETAG_DISABLED = True


class TestEtag():

    def test_etag_is_deterministic(self):
        """Check etag computation is deterministic

           generate_etag should return the same value everytime the same
           dictionary is passed. This is not obvious since dictionaries
           are unordered by design. We check this by feeding it different
           OrderedDict instances that are equivalent to the same dictionary.
        """

        data = OrderedDict([
            ('a', 1),
            ('b', 2),
            ('c', OrderedDict([('a', 1), ('b', 2)]))
        ])
        etag = generate_etag(data)

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

        data_copies_etag = [generate_etag(d) for d in data_copies]
        assert all(e == etag for e in data_copies_etag)

    def test_etag_operations_etag_enabled(self, app_mock):

        client = app_mock.test_client()

        assert is_etag_enabled(app_mock)

        # GET without ETag: OK
        response = client.get('/test/')
        assert response.status_code == 200
        list_etag = response.headers['ETag']

        # GET with correct ETag: Not modified
        response = client.get(
            '/test/',
            headers=Headers({'If-None-Match': list_etag})
        )
        assert response.status_code == 304

        # Post item_1
        item_1_data = {'field': 1}
        response = client.post(
            '/test/',
            data=json.dumps(item_1_data),
            content_type='application/json'
        )
        assert response.status_code == 201
        item_1_id = response.json['data']['item_id']

        # GET with wrong/outdated ETag: OK
        response = client.get(
            '/test/',
            headers=Headers({'If-None-Match': list_etag})
        )
        assert response.status_code == 200

        # GET by ID without ETag: OK
        response = client.get('/test/{}'.format(item_1_id))
        assert response.status_code == 200
        item_etag = response.headers['ETag']

        # GET by ID with correct ETag: Not modified
        response = client.get(
            '/test/{}'.format(item_1_id),
            headers=Headers({'If-None-Match': item_etag})
        )
        assert response.status_code == 304

        # PUT without ETag: Precondition required error
        item_1_data['field'] = 2
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
            headers=Headers({'If-Match': item_etag})
        )
        assert response.status_code == 200
        new_item_etag = response.headers['ETag']

        # PUT with wrong/outdated ETag: Precondition failed error
        item_1_data['field'] = 3
        response = client.put(
            '/test/{}'.format(item_1_id),
            data=json.dumps(item_1_data),
            content_type='application/json',
            headers=Headers({'If-Match': item_etag})
        )
        assert response.status_code == 412

        # GET by ID with wrong/outdated ETag: OK
        response = client.get(
            '/test/{}'.format(item_1_id),
            headers=Headers({'If-None-Match': item_etag})
        )
        assert response.status_code == 200

        # DELETE without ETag: Precondition required error
        response = client.delete('/test/{}'.format(item_1_id))
        assert response.status_code == 428

        # DELETE with wrong/outdated ETag: Precondition failed error
        response = client.delete(
            '/test/{}'.format(item_1_id),
            headers=Headers({'If-Match': item_etag})
        )
        assert response.status_code == 412

        # DELETE with correct ETag: No Content
        response = client.delete(
            '/test/{}'.format(item_1_id),
            headers=Headers({'If-Match': new_item_etag})
        )
        assert response.status_code == 204

    @pytest.mark.parametrize(
        'app_mock', [AppConfigEtagDisabled, ], indirect=True)
    def test_etag_operations_etag_disabled(self, app_mock):

        client = app_mock.test_client()

        assert not is_etag_enabled(app_mock)

        # GET without ETag: OK
        response = client.get('/test/')
        assert response.status_code == 200

        # GET with whatever ETag: OK (dummy ETag ignored)
        response = client.get(
            '/test/',
            headers=Headers({'If-None-Match': 'dummy_etag'})
        )
        assert response.status_code == 200

        # Post item_1
        item_1_data = {'field': 1}
        response = client.post(
            '/test/',
            data=json.dumps(item_1_data),
            content_type='application/json'
        )
        assert response.status_code == 201
        item_1_id = response.json['data']['item_id']

        # GET by ID: OK
        response = client.get('/test/{}'.format(item_1_id))
        assert response.status_code == 200

        # GET by ID with whatever ETag: OK (dummy ETag ignored)
        response = client.get(
            '/test/{}'.format(item_1_id),
            headers=Headers({'If-None-Match': 'dummy_etag'})
        )
        assert response.status_code == 200

        # PUT without ETag: OK
        item_1_data['field'] = 2
        response = client.put(
            '/test/{}'.format(item_1_id),
            data=json.dumps(item_1_data),
            content_type='application/json'
        )
        assert response.status_code == 200

        # PUT with whatever ETag: OK (dummy ETag ignored)
        item_1_data['field'] = 3
        response = client.put(
            '/test/{}'.format(item_1_id),
            data=json.dumps(item_1_data),
            content_type='application/json'
        )
        assert response.status_code == 200

        # Post item_2
        item_2_data = {'field': 10}
        response = client.post(
            '/test/',
            data=json.dumps(item_2_data),
            content_type='application/json'
        )
        assert response.status_code == 201
        item_2_id = response.json['data']['item_id']

        # DELETE without ETag: No Content (dummy ETag ignored)
        response = client.delete('/test/{}'.format(item_1_id))
        assert response.status_code == 204

        # DELETE with whatever ETag: No Content (dummy ETag ignored)
        response = client.delete(
            '/test/{}'.format(item_2_id),
            headers=Headers({'If-Match': 'dummy_etag'})
        )
        assert response.status_code == 204
