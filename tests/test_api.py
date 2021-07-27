"""Test Api class"""
import copy
import http

import pytest

from flask.views import MethodView
from werkzeug.routing import BaseConverter
import marshmallow as ma
import apispec

from flask_smorest import Api, Blueprint
from flask_smorest.exceptions import MissingAPIParameterError
from flask_smorest.spec import ResponseReferencesPlugin

from .conftest import AppConfig
from .utils import get_schemas


class TestApi:
    """Test Api class"""

    @pytest.mark.parametrize('openapi_version', ['2.0', '3.0.2'])
    @pytest.mark.parametrize(
        "params",
        [
            ("", {"minLength": 1}),
            ("(minlength=12)", {"minLength": 12}),
            ("(maxlength=12)", {"minLength": 1, "maxLength": 12}),
            ("(length=12)", {"minLength": 12, "maxLength": 12}),

        ]
    )
    def test_api_unicode_converter(self, app, params, openapi_version):
        app.config['OPENAPI_VERSION'] = openapi_version
        api = Api(app)
        blp = Blueprint('test', 'test', url_prefix='/test')

        param, output = params

        @blp.route('/<string{}:val>'.format(param))
        def test(val):
            pass

        api.register_blueprint(blp)
        spec = api.spec.to_dict()

        schema = {'type': 'string'}
        schema.update(output)
        parameter = {'in': 'path', 'name': 'val', 'required': True}
        if openapi_version == '2.0':
            parameter.update(schema)
        else:
            parameter['schema'] = schema
        assert spec['paths']['/test/{val}']['parameters'] == [parameter]

    @pytest.mark.parametrize('openapi_version', ['2.0', '3.0.2'])
    @pytest.mark.parametrize(
        "params",
        [
            ("", {"minimum": 0}),
            ("(min=12)", {"minimum": 12}),
            ("(max=12)", {"minimum": 0, "maximum": 12}),
            ("(signed=True)", {}),

        ]
    )
    @pytest.mark.parametrize('nb_type', ('int', 'float'))
    def test_api_int_float_converter(
            self, app, params, nb_type, openapi_version
    ):
        app.config['OPENAPI_VERSION'] = openapi_version
        api = Api(app)
        blp = Blueprint('test', 'test', url_prefix='/test')

        param, output = params

        @blp.route('/<{}{}:val>'.format(nb_type, param))
        def test(val):
            pass

        api.register_blueprint(blp)
        spec = api.spec.to_dict()

        schema = {
            'int': {'type': 'integer'},
            'float': {'type': 'number'},
        }[nb_type]
        schema.update(output)
        parameter = {'in': 'path', 'name': 'val', 'required': True}
        if openapi_version == '2.0':
            parameter.update(schema)
        else:
            parameter['schema'] = schema
        assert spec['paths']['/test/{val}']['parameters'] == [parameter]

    @pytest.mark.parametrize('openapi_version', ['2.0', '3.0.2'])
    def test_api_uuid_converter(self, app, openapi_version):
        app.config['OPENAPI_VERSION'] = openapi_version
        api = Api(app)
        blp = Blueprint('test', 'test', url_prefix='/test')

        @blp.route('/<uuid:val>')
        def test(val):
            pass

        api.register_blueprint(blp)
        spec = api.spec.to_dict()

        schema = {'type': 'string', 'format': 'uuid'}
        parameter = {'in': 'path', 'name': 'val', 'required': True}
        if openapi_version == '2.0':
            parameter.update(schema)
        else:
            parameter['schema'] = schema
        assert spec['paths']['/test/{val}']['parameters'] == [parameter]

    @pytest.mark.parametrize('openapi_version', ['2.0', '3.0.2'])
    def test_api_any_converter(self, app, openapi_version):
        app.config['OPENAPI_VERSION'] = openapi_version
        api = Api(app)
        blp = Blueprint('test', 'test', url_prefix='/test')

        @blp.route('/<any(foo, bar, "foo+bar"):val>')
        def test(val):
            pass

        api.register_blueprint(blp)
        spec = api.spec.to_dict()

        schema = {'type': 'string', 'enum': ['foo', 'bar', 'foo+bar']}
        parameter = {'in': 'path', 'name': 'val', 'required': True}
        if openapi_version == '2.0':
            parameter.update(schema)
        else:
            parameter['schema'] = schema
        assert spec['paths']['/test/{val}']['parameters'] == [parameter]

    @pytest.mark.parametrize('openapi_version', ['2.0', '3.0.2'])
    @pytest.mark.parametrize('register', (True, False))
    @pytest.mark.parametrize('view_type', ['function', 'method'])
    def test_api_register_converter(
            self, app, view_type, register, openapi_version
    ):
        app.config['OPENAPI_VERSION'] = openapi_version
        api = Api(app)
        blp = Blueprint('test', 'test', url_prefix='/test')

        class CustomConverter(BaseConverter):
            pass

        def converter2paramschema(converter):
            return {'type': 'custom string', 'format': 'custom format'}

        app.url_map.converters['custom_str'] = CustomConverter
        if register:
            api.register_converter(CustomConverter, converter2paramschema)

        if view_type == 'function':
            @blp.route('/<custom_str:val>')
            def test_func(val):
                pass
        else:
            @blp.route('/<custom_str:val>')
            class TestMethod(MethodView):
                def get(self, val):
                    pass

        api.register_blueprint(blp)
        spec = api.spec.to_dict()

        if register:
            schema = {'type': 'custom string', 'format': 'custom format'}
        else:
            schema = {'type': 'string'}
        parameter = {'in': 'path', 'name': 'val', 'required': True}
        if openapi_version == '2.0':
            parameter.update(schema)
        else:
            parameter['schema'] = schema
        assert spec['paths']['/test/{val}']['parameters'] == [parameter]

    @pytest.mark.parametrize('openapi_version', ['2.0', '3.0.2'])
    def test_api_register_converter_before_or_after_init(
            self, app, openapi_version
    ):
        app.config['OPENAPI_VERSION'] = openapi_version
        api = Api()
        blp = Blueprint('test', 'test', url_prefix='/test')

        class CustomConverter_1(BaseConverter):
            pass

        class CustomConverter_2(BaseConverter):
            pass

        def converter12paramschema(converter):
            return {'type': 'custom string 1'}

        def converter22paramschema(converter):
            return {'type': 'custom string 2'}

        app.url_map.converters['custom_str_1'] = CustomConverter_1
        app.url_map.converters['custom_str_2'] = CustomConverter_2
        api.register_converter(CustomConverter_1, converter12paramschema)
        api.init_app(app)
        api.register_converter(CustomConverter_2, converter22paramschema)

        @blp.route('/1/<custom_str_1:val>')
        def test_func_1(val):
            pass

        @blp.route('/2/<custom_str_2:val>')
        def test_func_2(val):
            pass

        api.register_blueprint(blp)
        spec = api.spec.to_dict()
        parameter_1 = spec['paths']['/test/1/{val}']['parameters'][0]
        parameter_2 = spec['paths']['/test/2/{val}']['parameters'][0]
        if openapi_version == '2.0':
            assert parameter_1['type'] == 'custom string 1'
            assert parameter_2['type'] == 'custom string 2'
        else:
            assert parameter_1['schema']['type'] == 'custom string 1'
            assert parameter_2['schema']['type'] == 'custom string 2'

    @pytest.mark.parametrize('mapping', [
        ('custom string', 'custom'),
        ('custom string', None),
        (ma.fields.Integer, ),
    ])
    def test_api_register_field_parameters(self, app, mapping):
        api = Api(app)

        class CustomField(ma.fields.Field):
            pass

        api.register_field(CustomField, *mapping)

        class Document(ma.Schema):
            field = CustomField()

        api.spec.components.schema('Document', schema=Document)

        if len(mapping) == 2:
            properties = {'field': {'type': 'custom string'}}
            # If mapping format is None, it does not appear in the spec
            if mapping[1] is not None:
                properties['field']['format'] = mapping[1]
        else:
            properties = {'field': {'type': 'integer'}}

        assert get_schemas(api.spec)['Document'] == {
            'properties': properties, 'type': 'object'}

    @pytest.mark.parametrize('openapi_version', ['2.0', '3.0.2'])
    def test_api_register_field_before_and_after_init(
            self, app, openapi_version
    ):
        app.config['OPENAPI_VERSION'] = openapi_version
        api = Api()

        class CustomField_1(ma.fields.Field):
            pass

        class CustomField_2(ma.fields.Field):
            pass

        api.register_field(CustomField_1, 'custom string', 'custom')
        api.init_app(app)
        api.register_field(CustomField_2, 'custom string', 'custom')

        class Schema_1(ma.Schema):
            int_1 = ma.fields.Int()
            custom_1 = CustomField_1()

        class Schema_2(ma.Schema):
            int_2 = ma.fields.Int()
            custom_2 = CustomField_2()

        api.spec.components.schema('Schema_1', schema=Schema_1)
        api.spec.components.schema('Schema_2', schema=Schema_2)

        schema_defs = get_schemas(api.spec)
        assert schema_defs['Schema_1']['properties']['custom_1'] == {
            'type': 'custom string', 'format': 'custom'}
        assert schema_defs['Schema_2']['properties']['custom_2'] == {
            'type': 'custom string', 'format': 'custom'}

    @pytest.mark.parametrize('step', ('at_once', 'init', 'init_app'))
    def test_api_extra_spec_kwargs(self, app, step):
        """Test APISpec kwargs can be passed in Api init or app config"""
        app.config['API_SPEC_OPTIONS'] = {'basePath': '/v2'}
        if step == 'at_once':
            api = Api(
                app, spec_kwargs={'basePath': '/v1', 'host': 'example.com'}
            )
        elif step == 'init':
            api = Api(spec_kwargs={'basePath': '/v1', 'host': 'example.com'})
            api.init_app(app)
        elif step == 'init_app':
            api = Api()
            api.init_app(
                app, spec_kwargs={'basePath': '/v1', 'host': 'example.com'}
            )
        spec = api.spec.to_dict()
        assert spec['host'] == 'example.com'
        # app config overrides Api spec_kwargs parameters
        assert spec['basePath'] == '/v2'

    def test_api_extra_spec_kwargs_init_app_update_init(self, app):
        """Test empty APISpec kwargs passed in init_app update init kwargs"""
        api = Api(spec_kwargs={'basePath': '/v1', 'host': 'example.com'})
        api.init_app(app, spec_kwargs={'basePath': '/v2'})
        spec = api.spec.to_dict()
        assert spec['host'] == 'example.com'
        assert spec['basePath'] == '/v2'

    @pytest.mark.parametrize('openapi_version', ['2.0', '3.0.2'])
    def test_api_extra_spec_plugins(self, app, schemas, openapi_version):
        """Test extra plugins can be passed to internal APISpec instance"""
        app.config['OPENAPI_VERSION'] = openapi_version

        class MyPlugin(apispec.BasePlugin):
            def schema_helper(self, name, definition, **kwargs):
                return {'dummy': 'whatever'}

        api = Api(app, spec_kwargs={'extra_plugins': (MyPlugin(), )})
        api.spec.components.schema('Pet', schema=schemas.DocSchema)
        assert get_schemas(api.spec)['Pet']['dummy'] == 'whatever'

    def test_api_register_blueprint_options(self, app):
        api = Api(app)
        blp = Blueprint('test', 'test', url_prefix='/test1')

        @blp.route('/')
        def test_func():
            return {'response': 'OK'}

        api.register_blueprint(blp, url_prefix='/test2')

        spec = api.spec.to_dict()
        assert '/test1/' not in spec['paths']
        assert '/test2/' in spec['paths']

        client = app.test_client()
        response = client.get('/test1/')
        assert response.status_code == 404
        response = client.get('/test2/')
        assert response.status_code == 200
        assert response.json == {'response': 'OK'}

    @pytest.mark.parametrize(
        'parameter',
        [
            ('title', 'API_TITLE', 'Test', 'title'),
            ('version', 'API_VERSION', '2', 'version'),
        ]
    )
    def test_api_api_parameters(self, app, parameter):
        """Test API parameters must be passed, as app param or spec kwarg"""

        param_name, config_param, param_value, oas_name = parameter

        app.config[config_param] = param_value
        api = Api(app)
        assert api.spec.to_dict()['info'][oas_name] == param_value

        del app.config[config_param]
        api = Api(app, spec_kwargs={param_name: param_value})
        assert api.spec.to_dict()['info'][oas_name] == param_value

        with pytest.raises(
                MissingAPIParameterError,
                match='must be specified either as'
        ):
            Api(app)

    @pytest.mark.parametrize('openapi_version', ['2.0', '3.0.2'])
    def test_api_openapi_version_parameter(self, app, openapi_version):
        """Test OpenAPI version must be passed, as app param or spec kwarg"""

        key = {'2.0': 'swagger', '3.0.2': 'openapi'}[openapi_version]

        app.config['OPENAPI_VERSION'] = openapi_version
        api = Api(app)
        assert api.spec.to_dict()[key] == openapi_version

        del app.config['OPENAPI_VERSION']
        api = Api(app, spec_kwargs={'openapi_version': openapi_version})
        assert api.spec.to_dict()[key] == openapi_version

        with pytest.raises(
                MissingAPIParameterError,
                match='OpenAPI version must be specified'
        ):
            Api(app)

    def test_api_multiple_apis(self, app):
        """Test it is possible to create multiple Apis against the same app"""
        Api(app)
        Api(app)

        class NewAppConfig(AppConfig):
            OPENAPI_URL_PREFIX = "/"
            OPENAPI_SWAGGER_UI_PATH = "/"
            OPENAPI_SWAGGER_UI_URL = "https://domain.tld/swagger-ui"
            OPENAPI_SWAGGER_UI_CONFIG = {
                "supportedSubmitMethods": ["get", "put", "post", "delete"],
            }

        app.config.from_object(NewAppConfig)
        Api(app)
        with pytest.raises(
                ValueError,
                match='The name \'api-docs\' is already registered'
        ):
            Api(app)
        Api(app, doc_kwargs={"name": "api-docs-2"})


class TestResponseReferencesPlugin:
    """Test ResponseReferencesPlugin class"""

    @pytest.mark.parametrize('kwargs', [
        ({}),
        ({'operations': None}),
        ({'operations': {}}),
        ({'operations': {'get': 'not a dict'}}),
        ({'operations': {'get': {}}}),
        ({'operations': {'get': {'responses': {}}}}),
        ({'operations': {'get': {'responses': {200: {}}}}}),
        ({'operations': {'get': {'responses': {200: 'unknown response'}}}}),
    ])
    def test_operation_helper_unapplicable(self, kwargs):
        """Should ignore if there are no applicable responses.

        Applicable responses are string in the defined applicable responses.
        Any other cases should pass right through without changing anything.
        """
        plugin = ResponseReferencesPlugin()
        expected = copy.deepcopy(kwargs)
        plugin.operation_helper(**kwargs)
        assert kwargs == expected  # Nothing mutated

    @pytest.mark.parametrize('openapi_version', ['2.0', '3.0.2'])
    @pytest.mark.parametrize('http_status_code, http_status_name', [
        *[(s.value, s.name) for s in http.HTTPStatus],
        ('DEFAULT_ERROR', 'DEFAULT_ERROR'),
    ])
    def test_api_registers_error_responses(
            self, openapi_version, http_status_code, http_status_name):
        """Responses should be added to spec."""
        spec = apispec.APISpec('title', 'version', openapi_version)
        plugin = ResponseReferencesPlugin()
        plugin.init_spec(spec)

        operations = {'get': {'responses': {
            http_status_code: http_status_name,
        }}}

        plugin.operation_helper(operations=operations)

        components = spec.to_dict()
        if openapi_version == '3.0.2':
            components = components['components']

        assert len(components['responses']) == 1
        assert http_status_name in components['responses']

    @pytest.mark.parametrize('openapi_version', ['2.0', '3.0.2'])
    def test_multi_operation_multi_reponses(self, openapi_version):
        """Should loop all operations and all responses."""
        spec = apispec.APISpec('title', 'version', openapi_version)
        plugin = ResponseReferencesPlugin()
        plugin.init_spec(spec)

        operations = {
            'get': {'responses': {
                http.HTTPStatus.OK.value:
                    http.HTTPStatus.OK.name,
                http.HTTPStatus.NO_CONTENT.value:
                    http.HTTPStatus.NO_CONTENT.name,
            }},
            'post': {'responses': {
                http.HTTPStatus.OK.value:
                    http.HTTPStatus.OK.name,  # Ignored repeat
                http.HTTPStatus.CREATED.value:
                    http.HTTPStatus.CREATED.name,
            }},
        }

        plugin.operation_helper(operations=operations)

        components = spec.to_dict()
        if openapi_version == '3.0.2':
            components = components['components']

        assert len(components['responses']) == 3  # 200, 201, 204

    @pytest.mark.parametrize('openapi_version', ['2.0', '3.0.2'])
    def test_repeated_response(self, openapi_version):
        """Repeated response, different endpoint."""
        spec = apispec.APISpec('title', 'version', openapi_version)
        plugin = ResponseReferencesPlugin()
        plugin.init_spec(spec)

        operations = {'get': {'responses': {
            http.HTTPStatus.OK.value: http.HTTPStatus.OK.name,
        }}}

        # operation_helper is called on each path, so this simulates
        # 2 endpoints with the same response
        plugin.operation_helper(operations=copy.deepcopy(operations))
        plugin.operation_helper(operations=copy.deepcopy(operations))

        components = spec.to_dict()
        if openapi_version == '3.0.2':
            components = components['components']

        assert len(components['responses']) == 1
