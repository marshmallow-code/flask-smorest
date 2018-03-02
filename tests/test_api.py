"""Test Api class"""

from unittest import mock

import apispec

from flask_rest_api import Api


class TestApi():
    """Test Api class"""

    def test_api_definition(self, app, schemas):
        DocSchema = schemas.DocSchema
        api = Api(app)
        with mock.patch.object(apispec.APISpec, 'definition') as mock_def:
            ret = api.definition('Document')(DocSchema)
        assert ret is DocSchema
        mock_def.assert_called_once_with('Document', schema=DocSchema)
