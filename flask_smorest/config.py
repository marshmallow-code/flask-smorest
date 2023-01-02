class APIConfigMixin:
    config = {}

    def get_default_config(self):
        return {
            "API_SPEC_OPTIONS": {},
            "API_TITLE": None,
            "API_VERSION": None,
            "ETAG_DISABLED": False,
            "OPENAPI_JSON_PATH": "openapi.json",
            "OPENAPI_RAPIDOC_CONFIG": {},
            "OPENAPI_RAPIDOC_PATH": None,
            "OPENAPI_RAPIDOC_URL": None,
            "OPENAPI_REDOC_PATH": None,
            "OPENAPI_REDOC_URL": None,
            "OPENAPI_SWAGGER_UI_CONFIG": {},
            "OPENAPI_SWAGGER_UI_PATH": None,
            "OPENAPI_SWAGGER_UI_URL": None,
            "OPENAPI_URL_PREFIX": None,
            "OPENAPI_VERSION": None,
        }

    def get_config_value(self, key, default=None):
        return self.config.get(key, default)

    def _init_config(self, app):
        self.config = {}
        for key, default_val in self.get_default_config().items():
            app_config_key = self.config_prefix + key
            value = app.config.get(app_config_key, default_val)
            if value is not None:
                self.config[key] = value
