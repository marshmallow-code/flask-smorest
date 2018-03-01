"""Test Api class"""

from unittest import mock

import pytest

from flask import jsonify
from flask.views import MethodView
from werkzeug.routing import BaseConverter
import marshmallow as ma
import apispec

from flask_rest_api import Api, Blueprint


class TestApi():
    """Test Api class"""

    def test_api_definition(self, app, schemas):
        DocSchema = schemas.DocSchema
        api = Api(app)
        with mock.patch.object(apispec.APISpec, 'definition') as mock_def:
            ret = api.definition('Document')(DocSchema)
        assert ret is DocSchema
        mock_def.assert_called_once_with('Document', schema=DocSchema)

    @pytest.mark.parametrize('view_type', ['function', 'method'])
    @pytest.mark.parametrize('custom_format', ['custom', None])
    def test_register_converter(self, app, view_type, custom_format):
        api = Api(app)
        blp = Blueprint('test', 'test', url_prefix='/test')

        class CustomConverter(BaseConverter):
            pass

        app.url_map.converters['custom_str'] = CustomConverter
        api.register_converter(CustomConverter, 'custom string', custom_format)

        if view_type == 'function':
            @blp.route('/<custom_str:val>')
            def test_func(val):
                return jsonify(val)
        else:
            @blp.route('/<custom_str:val>')
            class TestMethod(MethodView):
                def get(self, val):
                    return jsonify(val)

        api.register_blueprint(blp)
        spec = api._apispec.to_dict()

        # If custom_format is None (default), it does not appear in the spec
        if custom_format is not None:
            parameters = [{'in': 'path', 'name': 'val', 'required': True,
                           'type': 'custom string', 'format': 'custom'}]
        else:
            parameters = [{'in': 'path', 'name': 'val', 'required': True,
                           'type': 'custom string'}]
        assert spec['paths']['/test/{val}']['get']['parameters'] == parameters

    @pytest.mark.parametrize('view_type', ['function', 'method'])
    @pytest.mark.parametrize('custom_format', ['custom', None])
    def test_register_field(self, app, view_type, custom_format):
        api = Api(app)
        blp = Blueprint('test', 'test', url_prefix='/test')

        class CustomField(ma.fields.Field):
            pass

        api.register_field(CustomField, 'custom string', custom_format)

        class Document(ma.Schema):
            field = CustomField()

        if view_type == 'function':
            @blp.route('/')
            @blp.arguments(Document)
            def test_func(args):
                return jsonify(None)
        else:
            @blp.route('/')
            class TestMethod(MethodView):
                @blp.arguments(Document)
                def get(self, args):
                    return jsonify(None)

        api.register_blueprint(blp)
        spec = api._apispec.to_dict()

        # If custom_format is None (default), it does not appear in the spec
        properties = {'field': {'type': 'custom string'}}
        if custom_format is not None:
            properties['field']['format'] = 'custom'

        assert (spec['paths']['/test/']['get']['parameters'] ==
                [{'in': 'body', 'required': False, 'name': 'body',
                  'schema': {'properties': properties, 'type': 'object'}, }])
