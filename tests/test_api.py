"""Test Api class"""

from unittest import mock

import pytest

from flask import jsonify
from flask.views import MethodView
from werkzeug.routing import BaseConverter
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

    @pytest.mark.parametrize('custom_format', ['custom', None])
    def test_register_converter(self, app, custom_format):
        api = Api(app)
        blp = Blueprint('test', 'test', url_prefix='/test')

        class CustomConverter(BaseConverter):
            pass

        app.url_map.converters['custom_str'] = CustomConverter
        api.register_converter(CustomConverter, 'custom string', custom_format)

        # Test both view function and method view
        @blp.route('/test_func/<custom_str:val>')
        def test_func(val):
            return jsonify(val)

        @blp.route('/test_method/<custom_str:val>')
        class TestMethod(MethodView):
            def get(self, val):
                return jsonify(val)

        api.register_blueprint(blp)

        spec_paths = api._apispec.to_dict()['paths']
        test_func_spec_paths = spec_paths['/test/test_func/{val}']
        test_method_spec_paths = spec_paths['/test/test_method/{val}']

        if custom_format is not None:
            assert (test_func_spec_paths['get']['parameters'] ==
                    [{'in': 'path', 'name': 'val', 'required': True,
                      'type': 'custom string', 'format': 'custom'}])
            assert (test_method_spec_paths['get']['parameters'] ==
                    [{'in': 'path', 'name': 'val', 'required': True,
                      'type': 'custom string', 'format': 'custom'}])
        # If custom_format is None (default), it does not appear in the spec
        else:
            assert (test_func_spec_paths['get']['parameters'] ==
                    [{'in': 'path', 'name': 'val', 'required': True,
                      'type': 'custom string'}])
            assert (test_method_spec_paths['get']['parameters'] ==
                    [{'in': 'path', 'name': 'val', 'required': True,
                      'type': 'custom string'}])
