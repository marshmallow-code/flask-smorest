"""Test arguments parser"""

import marshmallow as ma

from flask import jsonify
from flask.views import MethodView

from flask_rest_api import Api, Blueprint
from flask_rest_api.arguments import NestedQueryArgsParser
from flask_rest_api.compat import MARSHMALLOW_VERSION_MAJOR


class TestArgsParser():

    def test_args_parser_nested_query_arguments(self, app):
        api = Api(app)

        class CustomBlueprint(Blueprint):
            ARGUMENTS_PARSER = NestedQueryArgsParser()

        blp = CustomBlueprint('test', 'test', url_prefix='/test')

        class UserNameSchema(ma.Schema):
            if MARSHMALLOW_VERSION_MAJOR < 3:
                class Meta:
                    strict = True
            first_name = ma.fields.String()
            last_name = ma.fields.String()

        class UserSchema(ma.Schema):
            if MARSHMALLOW_VERSION_MAJOR < 3:
                class Meta:
                    strict = True
            user = ma.fields.Nested(UserNameSchema)

        @blp.route('/')
        class TestMethod(MethodView):
            @blp.arguments(UserSchema, location='query')
            def get(self, args):
                return jsonify(args)

        api.register_blueprint(blp)

        res = app.test_client().get('/test/', query_string={
            'user.first_name': 'Chuck', 'user.last_name': 'Norris'})

        assert res.json == {
            'user': {'first_name': 'Chuck', 'last_name': 'Norris'}}
