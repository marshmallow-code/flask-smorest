"""Api extension initialization"""

from webargs.flaskparser import abort  # noqa
from flask import request
from flask.globals import request_ctx

from .spec import APISpecMixin
from .blueprint import Blueprint  # noqa
from .pagination import Page  # noqa
from .error_handler import ErrorHandlerMixin
from .utils import normalize_config_prefix
from .config import APIConfigMixin
from .globals import current_api  # noqa

__version__ = "0.40.0"


class Api(APISpecMixin, ErrorHandlerMixin, APIConfigMixin):
    """Main class

    Provides helpers to build a REST API using Flask.

    :param Flask app: Flask application
    :param spec_kwargs: kwargs to pass to internal APISpec instance
    :param str config_prefix: Should be used if the user is planning to use
        multiple `Api`'s in a single app. If it is not empty then
        all application parameters will be prefixed with it. For example:
        if ``config_prefix`` is ``V1_`` then ``V1_API_TITLE`` is going to
        be used instead of ``API_TITLE``.

    The ``spec_kwargs`` dictionary is passed as kwargs to the internal APISpec
    instance. **flask-smorest** adds a few parameters to the original
    parameters documented in :class:`apispec.APISpec <apispec.APISpec>`:

    :param apispec.BasePlugin flask_plugin: Flask plugin
    :param apispec.BasePlugin marshmallow_plugin: Marshmallow plugin
    :param list|tuple extra_plugins: List of additional ``BasePlugin``
        instances
    :param str title: API title. Can also be passed as
        application parameter `API_TITLE`.
    :param str version: API version. Can also be passed as
        application parameter `API_VERSION`.
    :param str openapi_version: OpenAPI version. Can also be passed as
        application parameter `OPENAPI_VERSION`.

    This allows the user to override default Flask and marshmallow plugins.

    For more flexibility, additional spec kwargs can also be passed as app
    parameter `API_SPEC_OPTIONS`.
    """

    def __init__(self, app=None, *, spec_kwargs=None, config_prefix=""):
        self._app = app
        self._spec_kwargs = spec_kwargs or {}
        self.config_prefix = normalize_config_prefix(config_prefix)
        self.spec = None
        # Use lists to enforce order
        self._fields = []
        self._converters = []
        if app is not None:
            self.init_app(app)

        # TODO: better name and comment with an explanation
        self._blp_names = set()

    def init_app(self, app, *, spec_kwargs=None):
        """Initialize Api with application

        :param spec_kwargs: kwargs to pass to internal APISpec instance.
            Updates ``spec_kwargs`` passed in ``Api`` init.
        """
        self._app = app

        # Register flask-smorest in app extensions
        app.extensions = getattr(app, "extensions", {})
        ext = app.extensions.setdefault("flask-smorest", {"apis": {}})
        ext["apis"][self.config_prefix] = {"ext_obj": self}

        # Update config
        self._init_config(app)

        # Initialize spec
        self._init_spec(**{**self._spec_kwargs, **(spec_kwargs or {})})

        # Initialize blueprint serving spec
        self._register_doc_blueprint()

        # Register error handlers
        self._register_error_handlers()

        # register request handlers to assign self as `current_api` if needed
        app.before_request(self._add_self_as_current_api)
        app.teardown_request(self._remove_self_as_current_api)

    def register_blueprint(self, blp, *, parameters=None, **options):
        """Register a blueprint in the application

        Also registers documentation for the blueprint/resource

        :param Blueprint blp: Blueprint to register
        :param list parameters: List of parameter descriptions for the path parameters
            in the ``url_prefix`` of the Blueprint. Only used to document the resource.
        :param options: Keyword arguments overriding
            :class:`Blueprint <flask.Blueprint>` defaults

        Must be called after app is initialized.
        """
        blp_name = options.get("name", blp.name)
        self._blp_names.add(blp_name)

        self._app.register_blueprint(blp, **options)

        # Register views in API documentation for this resource
        blp.register_views_in_doc(
            self,
            self._app,
            self.spec,
            name=blp_name,
            parameters=parameters,
        )

        # Add tag relative to this resource to the global tag list
        self.spec.tag({"name": blp_name, "description": blp.description})

    def _add_self_as_current_api(self):  # TODO: rename
        for blp_name in request.blueprints:
            if blp_name in self._blp_names:
                request_ctx.api = self
                break

    def _remove_self_as_current_api(self, response):  # TODO: rename
        if hasattr(request_ctx, "api"):
            for blp_name in request.blueprints:
                if blp_name in self._blp_names:
                    delattr(request_ctx, "api")
                    break

        return response
