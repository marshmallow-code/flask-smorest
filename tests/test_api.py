"""Test Api class"""

from unittest import mock

from werkzeug.routing import BaseConverter
import apispec

from flask_rest_api import Api, APISpec


class TestApi():
    """Test Api class"""

    def test_api_definition(self, app, schemas):
        DocSchema = schemas.DocSchema
        api = Api(app)
        with mock.patch.object(apispec.APISpec, 'definition') as mock_def:
            ret = api.definition('Document')(DocSchema)
        assert ret is DocSchema
        mock_def.assert_called_once_with('Document', schema=DocSchema)

    def test_api_register_converter(self, app):
        api = Api(app)

        class CustomConverter(BaseConverter):
            pass

        with mock.patch.object(APISpec, 'register_converter') as mock_reg_conv:
            api.register_converter(
                'custom_str', CustomConverter, 'cust string', 'cust format')

        assert api._app.url_map.converters['custom_str'] == CustomConverter
        mock_reg_conv.assert_called_once_with(
            CustomConverter, 'cust string', 'cust format')
