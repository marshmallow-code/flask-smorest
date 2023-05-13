import pytest

from flask_smorest import Api
from flask_smorest.blueprint import Blueprint
from flask_smorest.plugin.built_in import APIKeySecurityPlugin


class TestSecurityPlugin:
    @pytest.fixture
    def security_plugin(self):
        return APIKeySecurityPlugin("testApiKey", "X-API-Key")

    @pytest.mark.parametrize("openapi_version", ("2.0", "3.0.2"))
    def test_spec_contains_security_requirement(
        self, app, security_plugin, openapi_version
    ):
        app.config["OPENAPI_VERSION"] = openapi_version
        api = Api(app)

        blp = Blueprint(
            "test", __name__, url_prefix="/test", smore_plugins=[security_plugin]
        )

        @blp.route("/")
        @security_plugin.security(["testApiKey"])
        def func():
            """Dummy view func"""

        api.register_blueprint(blp)

        spec = api.spec.to_dict()
        assert spec["paths"]["/test/"]["get"]["security"] == [{"testApiKey": []}]
        if openapi_version == "3.0.2":
            security_schemes = spec["components"]["securitySchemes"]
        else:  # Version 2.0
            security_schemes = spec["securityDefinitions"]
        assert security_schemes == {
            "testApiKey": {"type": "apiKey", "in": "header", "name": "X-API-Key"}
        }
