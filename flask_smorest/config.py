class APIConfigMixin:
    """Add config related features to Api class"""

    config = {}
    """ A dict of Api config

    See :meth:`APIConfigMixin.get_default_config` for all config keys
    """

    def get_default_config(self):
        """Get a default config dict

        :return: a dict. Dict's keys are all keys used to configure Api instances.
            Dict's values are default values in case Flask config misses them.

        In ``Api.init_app`` it will go through all of them and will copy values
        from Flask config.

        Do not forget that you need to add a prefix if ``Api`` has non-empty
        ``config_prefix``.

        .. code-block:: python
            api = Api(config_prefix="")


            class Config:
                API_TITLE = "T"


            api_v1 = Api(config_prefix="V1_")
            api_v2 = Api(config_prefix="V2_")


            class Config:
                V1_API_TITLE = "T1"
                V2_API_TITLE = "T2"

        Example: you are overriding `Api` and want to add more config keys.

        .. code-block:: python

            class MyApi(Api):
                def get_default_config(self):
                    result = super().get_default_config()
                    result["MY_KEY"] = 42
                    return result
        """
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
        """Get API config value potentially affected by config_prefix

        :param str key: config key
        :param default: return this value if ``key`` does not exist
        :return: an API config value or ``default``.
        """
        return self.config.get(key, default)

    def _init_config(self, app):
        self.config = {}
        for key, default_val in self.get_default_config().items():
            app_config_key = self.config_prefix + key
            value = app.config.get(app_config_key, default_val)
            if value is not None:
                self.config[key] = value
