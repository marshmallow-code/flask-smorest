import pytest

from marshmallow import Schema, fields

from flask_rest_api import Api

class TestSpec():

    def test_schema_definition_extra_fields(self):

        class MySchema(Schema):
            field = fields.Str()

        api = Api()
        api.definition('MySchema')(
            Schema,
            extra_fields={'test': 'ok', 'x-test': 'check, check!'})

        schema_def = api._apispec.spec.to_dict()['definitions']['MySchema']
        assert schema_def['test'] == 'ok'
        assert schema_def['x-test'] == 'check, check!'
