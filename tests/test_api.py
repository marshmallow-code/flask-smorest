"""Test Api class"""

import json

import pytest

from flask import jsonify
from flask.json.provider import DefaultJSONProvider
from flask.views import MethodView
from werkzeug.routing import BaseConverter

import apispec
import marshmallow as ma

from flask_smorest import Api, Blueprint, current_api
from flask_smorest.exceptions import MissingAPIParameterError

from .utils import get_responses, get_schemas


class TestApi:
    """Test Api class"""

    @pytest.mark.parametrize("openapi_version", ["2.0", "3.0.2"])
    @pytest.mark.parametrize(
        "params",
        [
            ("", {"minLength": 1}),
            ("(minlength=12)", {"minLength": 12}),
            ("(maxlength=12)", {"minLength": 1, "maxLength": 12}),
            ("(length=12)", {"minLength": 12, "maxLength": 12}),
        ],
    )
    def test_api_unicode_converter(self, app, params, openapi_version):
        app.config["OPENAPI_VERSION"] = openapi_version
        api = Api(app)
        blp = Blueprint("test", "test", url_prefix="/test")

        param, output = params

        @blp.route(f"/<string{param}:val>")
        def test(val):
            pass

        api.register_blueprint(blp)
        spec = api.spec.to_dict()

        schema = {"type": "string"}
        schema.update(output)
        parameter = {"in": "path", "name": "val", "required": True}
        if openapi_version == "2.0":
            parameter.update(schema)
        else:
            parameter["schema"] = schema
        assert spec["paths"]["/test/{val}"]["parameters"] == [parameter]

    @pytest.mark.parametrize("openapi_version", ["2.0", "3.0.2"])
    @pytest.mark.parametrize(
        "params",
        [
            ("", {"minimum": 0}),
            ("(min=12)", {"minimum": 12}),
            ("(max=12)", {"minimum": 0, "maximum": 12}),
            ("(signed=True)", {}),
        ],
    )
    @pytest.mark.parametrize("nb_type", ("int", "float"))
    def test_api_int_float_converter(self, app, params, nb_type, openapi_version):
        app.config["OPENAPI_VERSION"] = openapi_version
        api = Api(app)
        blp = Blueprint("test", "test", url_prefix="/test")

        param, output = params

        @blp.route(f"/<{nb_type}{param}:val>")
        def test(val):
            pass

        api.register_blueprint(blp)
        spec = api.spec.to_dict()

        schema = {
            "int": {"type": "integer"},
            "float": {"type": "number"},
        }[nb_type]
        schema.update(output)
        parameter = {"in": "path", "name": "val", "required": True}
        if openapi_version == "2.0":
            parameter.update(schema)
        else:
            parameter["schema"] = schema
        assert spec["paths"]["/test/{val}"]["parameters"] == [parameter]

    @pytest.mark.parametrize("openapi_version", ["2.0", "3.0.2"])
    def test_api_uuid_converter(self, app, openapi_version):
        app.config["OPENAPI_VERSION"] = openapi_version
        api = Api(app)
        blp = Blueprint("test", "test", url_prefix="/test")

        @blp.route("/<uuid:val>")
        def test(val):
            pass

        api.register_blueprint(blp)
        spec = api.spec.to_dict()

        schema = {"type": "string", "format": "uuid"}
        parameter = {"in": "path", "name": "val", "required": True}
        if openapi_version == "2.0":
            parameter.update(schema)
        else:
            parameter["schema"] = schema
        assert spec["paths"]["/test/{val}"]["parameters"] == [parameter]

    @pytest.mark.parametrize("openapi_version", ["2.0", "3.0.2"])
    def test_api_any_converter(self, app, openapi_version):
        app.config["OPENAPI_VERSION"] = openapi_version
        api = Api(app)
        blp = Blueprint("test", "test", url_prefix="/test")

        @blp.route('/<any(foo, bar, "foo+bar"):val>')
        def test(val):
            pass

        api.register_blueprint(blp)
        spec = api.spec.to_dict()

        schema = {"type": "string", "enum": ["foo", "bar", "foo+bar"]}
        parameter = {"in": "path", "name": "val", "required": True}
        if openapi_version == "2.0":
            parameter.update(schema)
        else:
            parameter["schema"] = schema
        assert spec["paths"]["/test/{val}"]["parameters"] == [parameter]

    @pytest.mark.parametrize("openapi_version", ["2.0", "3.0.2"])
    @pytest.mark.parametrize("register", (True, False))
    @pytest.mark.parametrize("view_type", ["function", "method"])
    def test_api_register_converter(self, app, view_type, register, openapi_version):
        app.config["OPENAPI_VERSION"] = openapi_version
        api = Api(app)
        blp = Blueprint("test", "test", url_prefix="/test")

        class CustomConverter(BaseConverter):
            pass

        def converter2paramschema(converter):
            return {"type": "custom string", "format": "custom format"}

        app.url_map.converters["custom_str"] = CustomConverter
        if register:
            api.register_converter(CustomConverter, converter2paramschema)

        if view_type == "function":

            @blp.route("/<custom_str:val>")
            def test_func(val):
                pass

        else:

            @blp.route("/<custom_str:val>")
            class TestMethod(MethodView):
                def get(self, val):
                    pass

        api.register_blueprint(blp)
        spec = api.spec.to_dict()

        if register:
            schema = {"type": "custom string", "format": "custom format"}
        else:
            schema = {"type": "string"}
        parameter = {"in": "path", "name": "val", "required": True}
        if openapi_version == "2.0":
            parameter.update(schema)
        else:
            parameter["schema"] = schema
        assert spec["paths"]["/test/{val}"]["parameters"] == [parameter]

    @pytest.mark.parametrize("openapi_version", ["2.0", "3.0.2"])
    def test_api_register_converter_before_or_after_init(self, app, openapi_version):
        app.config["OPENAPI_VERSION"] = openapi_version
        api = Api()
        blp = Blueprint("test", "test", url_prefix="/test")

        class CustomConverter_1(BaseConverter):
            pass

        class CustomConverter_2(BaseConverter):
            pass

        def converter12paramschema(converter):
            return {"type": "custom string 1"}

        def converter22paramschema(converter):
            return {"type": "custom string 2"}

        app.url_map.converters["custom_str_1"] = CustomConverter_1
        app.url_map.converters["custom_str_2"] = CustomConverter_2
        api.register_converter(CustomConverter_1, converter12paramschema)
        api.init_app(app)
        api.register_converter(CustomConverter_2, converter22paramschema)

        @blp.route("/1/<custom_str_1:val>")
        def test_func_1(val):
            pass

        @blp.route("/2/<custom_str_2:val>")
        def test_func_2(val):
            pass

        api.register_blueprint(blp)
        spec = api.spec.to_dict()
        parameter_1 = spec["paths"]["/test/1/{val}"]["parameters"][0]
        parameter_2 = spec["paths"]["/test/2/{val}"]["parameters"][0]
        if openapi_version == "2.0":
            assert parameter_1["type"] == "custom string 1"
            assert parameter_2["type"] == "custom string 2"
        else:
            assert parameter_1["schema"]["type"] == "custom string 1"
            assert parameter_2["schema"]["type"] == "custom string 2"

    @pytest.mark.parametrize(
        "mapping",
        [
            ("custom string", "custom"),
            ("custom string", None),
            (ma.fields.Integer,),
        ],
    )
    def test_api_register_field_parameters(self, app, mapping):
        api = Api(app)

        class CustomField(ma.fields.Field):
            pass

        api.register_field(CustomField, *mapping)

        class Document(ma.Schema):
            field = CustomField()

        api.spec.components.schema("Document", schema=Document)

        if len(mapping) == 2:
            properties = {"field": {"type": "custom string"}}
            # If mapping format is None, it does not appear in the spec
            if mapping[1] is not None:
                properties["field"]["format"] = mapping[1]
        else:
            properties = {"field": {"type": "integer"}}

        assert get_schemas(api.spec)["Document"] == {
            "properties": properties,
            "type": "object",
        }

    @pytest.mark.parametrize("openapi_version", ["2.0", "3.0.2"])
    def test_api_register_field_before_and_after_init(self, app, openapi_version):
        app.config["OPENAPI_VERSION"] = openapi_version
        api = Api()

        class CustomField_1(ma.fields.Field):
            pass

        class CustomField_2(ma.fields.Field):
            pass

        api.register_field(CustomField_1, "custom string", "custom")
        api.init_app(app)
        api.register_field(CustomField_2, "custom string", "custom")

        class Schema_1(ma.Schema):
            int_1 = ma.fields.Int()
            custom_1 = CustomField_1()

        class Schema_2(ma.Schema):
            int_2 = ma.fields.Int()
            custom_2 = CustomField_2()

        api.spec.components.schema("Schema_1", schema=Schema_1)
        api.spec.components.schema("Schema_2", schema=Schema_2)

        schema_defs = get_schemas(api.spec)
        assert schema_defs["Schema_1"]["properties"]["custom_1"] == {
            "type": "custom string",
            "format": "custom",
        }
        assert schema_defs["Schema_2"]["properties"]["custom_2"] == {
            "type": "custom string",
            "format": "custom",
        }

    @pytest.mark.parametrize("step", ("at_once", "init", "init_app"))
    def test_api_extra_spec_kwargs(self, app, step):
        """Test APISpec kwargs can be passed in Api init or app config"""
        app.config["API_SPEC_OPTIONS"] = {"basePath": "/v2"}
        if step == "at_once":
            api = Api(app, spec_kwargs={"basePath": "/v1", "host": "example.com"})
        elif step == "init":
            api = Api(spec_kwargs={"basePath": "/v1", "host": "example.com"})
            api.init_app(app)
        elif step == "init_app":
            api = Api()
            api.init_app(app, spec_kwargs={"basePath": "/v1", "host": "example.com"})
        spec = api.spec.to_dict()
        assert spec["host"] == "example.com"
        # app config overrides Api spec_kwargs parameters
        assert spec["basePath"] == "/v2"

    def test_api_extra_spec_kwargs_init_app_update_init(self, app):
        """Test empty APISpec kwargs passed in init_app update init kwargs"""
        api = Api(spec_kwargs={"basePath": "/v1", "host": "example.com"})
        api.init_app(app, spec_kwargs={"basePath": "/v2"})
        spec = api.spec.to_dict()
        assert spec["host"] == "example.com"
        assert spec["basePath"] == "/v2"

    @pytest.mark.parametrize("openapi_version", ["2.0", "3.0.2"])
    def test_api_extra_spec_plugins(self, app, schemas, openapi_version):
        """Test extra plugins can be passed to internal APISpec instance"""
        app.config["OPENAPI_VERSION"] = openapi_version

        class MyPlugin(apispec.BasePlugin):
            def schema_helper(self, name, definition, **kwargs):
                return {"dummy": "whatever"}

        api = Api(app, spec_kwargs={"extra_plugins": (MyPlugin(),)})
        api.spec.components.schema("Pet", schema=schemas.DocSchema)
        assert get_schemas(api.spec)["Pet"]["dummy"] == "whatever"

    def test_api_register_blueprint_options(self, app):
        api = Api(app)
        blp = Blueprint("test", "test", url_prefix="/test1")

        @blp.route("/")
        def test_func():
            return {"response": "OK"}

        api.register_blueprint(blp, url_prefix="/test2")

        spec = api.spec.to_dict()
        assert "/test1/" not in spec["paths"]
        assert "/test2/" in spec["paths"]

        client = app.test_client()
        response = client.get("/test1/")
        assert response.status_code == 404
        response = client.get("/test2/")
        assert response.status_code == 200
        assert response.json == {"response": "OK"}

    @pytest.mark.parametrize(
        "parameter",
        [
            ("title", "API_TITLE", "Test", "title"),
            ("version", "API_VERSION", "2", "version"),
        ],
    )
    def test_api_api_parameters(self, app, parameter):
        """Test API parameters must be passed, as app param or spec kwarg"""

        param_name, config_param, param_value, oas_name = parameter

        app.config[config_param] = param_value
        api = Api(app)
        assert api.spec.to_dict()["info"][oas_name] == param_value

        del app.config[config_param]
        api = Api(app, spec_kwargs={param_name: param_value})
        assert api.spec.to_dict()["info"][oas_name] == param_value

        with pytest.raises(
            MissingAPIParameterError, match="must be specified either as"
        ):
            Api(app)

    @pytest.mark.parametrize("openapi_version", ["2.0", "3.0.2"])
    def test_api_openapi_version_parameter(self, app, openapi_version):
        """Test OpenAPI version must be passed, as app param or spec kwarg"""

        key = {"2.0": "swagger", "3.0.2": "openapi"}[openapi_version]

        app.config["OPENAPI_VERSION"] = openapi_version
        api = Api(app)
        assert api.spec.to_dict()[key] == openapi_version

        del app.config["OPENAPI_VERSION"]
        api = Api(app, spec_kwargs={"openapi_version": openapi_version})
        assert api.spec.to_dict()[key] == openapi_version

        with pytest.raises(
            MissingAPIParameterError, match="OpenAPI version must be specified"
        ):
            Api(app)

    @pytest.mark.parametrize("openapi_version", ["2.0", "3.0.2"])
    def test_api_lazy_registers_default_error_response(self, app, openapi_version):
        """Test default error response is registered"""
        app.config["OPENAPI_VERSION"] = openapi_version
        api = Api(app)

        # Declare a dummy response to ensure get_response doesn't fail
        response_1 = {"description": "Response 1"}
        api.spec.components.response("Response_1", response_1)

        # No route registered -> default error not registered
        assert "DEFAULT_ERROR" not in get_responses(api.spec)

        # Register a route
        blp = Blueprint("test", "test", url_prefix="/test")

        @blp.route("/test")
        def test(val):
            pass

        api.register_blueprint(blp)

        # Default error is now registered
        assert "DEFAULT_ERROR" in get_responses(api.spec)

    def test_multiple_apis_using_config_prefix_attribute(self, app):
        app.config.update(
            {
                "API_TITLE": "Ignore this title",
                "API_V1_API_TITLE": "V1 Title",
                "API_V1_API_VERSION": "1",
                "API_V1_OPENAPI_VERSION": "2.0",
                "API_V2_API_TITLE": "V2 Title",
                "API_V2_API_VERSION": "2",
                "API_V2_OPENAPI_VERSION": "3.0.2",
            }
        )
        api1 = Api(app, config_prefix="API_V1_")
        api2 = Api(app, config_prefix="API_V2")

        assert api1.spec.title == "V1 Title"
        assert api2.spec.title == "V2 Title"

    def test_prefixed_api_to_raise_correctly_formatted_error(self, app):
        with pytest.raises(
            MissingAPIParameterError,
            match='API title must be specified either as "API_V1_API_TITLE"',
        ):
            Api(app, config_prefix="API_V1_")

    def test_current_api(self, app):
        def get_current_api_config_prefix():
            return jsonify(current_api.config_prefix)

        a_blp = Blueprint("A", "A")
        a_blp.route("/")(get_current_api_config_prefix)

        b_blp = Blueprint("B", "B")
        b_blp.route("/")(get_current_api_config_prefix)

        a_blp.register_blueprint(b_blp, url_prefix="/b")

        api1 = Api(
            app,
            config_prefix="V1",
            spec_kwargs={
                "title": "V1",
                "version": "1",
                "openapi_version": "3.0.2",
            },
        )
        api2 = Api(
            app,
            config_prefix="V2",
            spec_kwargs={
                "title": "V2",
                "version": "2",
                "openapi_version": "3.0.2",
            },
        )

        api1.register_blueprint(a_blp, url_prefix="/v1/a", name="1A")
        api1.register_blueprint(b_blp, url_prefix="/v1/b", name="1B")
        api2.register_blueprint(a_blp, url_prefix="/v2/a", name="2A")
        api2.register_blueprint(b_blp, url_prefix="/v2/b", name="2B")

        client = app.test_client()
        assert client.get("/v1/a/").json == "V1_"
        assert client.get("/v1/a/b/").json == "V1_"
        assert client.get("/v1/b/").json == "V1_"
        assert client.get("/v2/a/").json == "V2_"
        assert client.get("/v2/a/b/").json == "V2_"
        assert client.get("/v2/b/").json == "V2_"

    def test_api_config_proxying_flask_config(self, app):
        app.config.update(
            {
                "DEBUG": True,
                "SECRET_KEY": "secret",
                "API_TITLE": "No Prefix Title",
                "API_VERSION": "2",
                "OPENAPI_VERSION": "3.0.2",
                "API_V1_API_TITLE": "V1 Title",
                "API_V1_API_VERSION": "1",
                "API_V1_OPENAPI_VERSION": "2.0",
                "API_V2_API_TITLE": "V2 Title",
                "API_V2_API_VERSION": "2",
                "API_V2_OPENAPI_VERSION": "3.0.2",
            }
        )

        api_empty = Api(app)
        # It is expected behaviour for Api with no config prefix to just
        # proxy whole App config
        assert "DEBUG" in api_empty.config
        assert set(api_empty.config) == set(app.config)
        assert len(api_empty.config) == len(app.config)

        api_v1 = Api(app, config_prefix="API_V1")
        assert set(api_v1.config) == {
            "API_V1_API_TITLE",
            "API_V1_API_VERSION",
            "API_V1_OPENAPI_VERSION",
        }
        assert len(api_v1.config) == 3

        api_v2 = Api(app, config_prefix="API_V2")
        assert set(api_v2.config) == {
            "API_V2_API_TITLE",
            "API_V2_API_VERSION",
            "API_V2_OPENAPI_VERSION",
        }
        assert len(api_v2.config) == 3

    @pytest.mark.parametrize("openapi_version", ["2.0", "3.0.2"])
    def test_api_serializes_doc_with_flask_json(self, app, openapi_version):
        """Check that app.json, not standard json, is used to serialize API doc"""

        class CustomType:
            """Custom type"""

        class CustomJSONEncoder(json.JSONEncoder):
            def default(self, object):
                if isinstance(object, CustomType):
                    return 42
                return super().default(object)

        class CustomJsonProvider(DefaultJSONProvider):
            def dumps(self, obj, **kwargs):
                return json.dumps(obj, **kwargs, cls=CustomJSONEncoder)

        class CustomSchema(ma.Schema):
            custom_field = ma.fields.Field(load_default=CustomType())

        app.config["OPENAPI_VERSION"] = openapi_version
        app.json = CustomJsonProvider(app)
        api = Api(app)
        blp = Blueprint("test", "test", url_prefix="/test")

        @blp.route("/")
        @blp.arguments(CustomSchema)
        def test(args):
            pass

        api.register_blueprint(blp)

        with app.app_context():
            spec_dict = api._openapi_json().json

        if openapi_version == "2.0":
            schema = spec_dict["definitions"]["Custom"]
        else:
            schema = spec_dict["components"]["schemas"]["Custom"]

        assert schema["properties"]["custom_field"]["default"] == 42
