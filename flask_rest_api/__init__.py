"""Api extension initialization"""

from webargs.flaskparser import abort  # noqa

from .spec import APISpecMixin
from .blueprint import Blueprint  # noqa
from .pagination import Page  # noqa
from .error_handler import ErrorHandlerMixin

__version__ = '0.14.0'


class Api(APISpecMixin, ErrorHandlerMixin):
    """Main class

    Provides helpers to build a REST API using Flask.

    :param Flask app: Flask application
    :param dict spec_kwargs: kwargs to pass to internal APISpec instance

    The ``spec_kwargs`` dictionary is passed as kwargs to the internal APISpec
    instance. **flask-rest-api** adds a few parameters to the original
    parameters documented in :class:`apispec.APISpec <apispec.APISpec>`:

    :param apispec.BasePlugin flask_plugin: Flask plugin
    :param apispec.BasePlugin marshmallow_plugin: Marshmallow plugin
    :param list|tuple extra_plugins: List of additional ``BasePlugin``
        instances
    :param str openapi_version: OpenAPI version. Can also be passed as
        application parameter `OPENAPI_VERSION`.

    This allows the user to override default Flask and marshmallow plugins.

    `title` and `version` APISpec parameters can't be passed here, they are set
    according to the app configuration.

    For more flexibility, additional spec kwargs can also be passed as app
    parameter `API_SPEC_OPTIONS`.
    """
    def __init__(self, app=None, *, spec_kwargs=None):
        self._app = app
        self.spec = None
        # Use lists to enforce order
        self._schemas = []
        self._fields = []
        self._converters = []
        if app is not None:
            self.init_app(app, spec_kwargs=spec_kwargs)

    def init_app(self, app, *, spec_kwargs=None):
        """Initialize Api with application"""

        self._app = app

        # Register flask-rest-api in app extensions
        app.extensions = getattr(app, 'extensions', {})
        ext = app.extensions.setdefault('flask-rest-api', {})
        ext['ext_obj'] = self

        # Initialize spec
        self._init_spec(**(spec_kwargs or {}))

        # Initialize blueprint serving spec
        self._register_doc_blueprint()

        # Register error handlers
        self._register_error_handlers()

    def register_blueprint(self, blp, **options):
        """Register a blueprint in the application

        Also registers documentation for the blueprint/resource

        :param Blueprint blp: Blueprint to register
        :param dict options: Keyword arguments overriding Blueprint defaults

        Must be called after app is initialized.
        """

        self._app.register_blueprint(blp, **options)

        # Register views in API documentation for this resource
        blp.register_views_in_doc(self._app, self.spec)

        # Add tag relative to this resource to the global tag list
        self.spec.tag({'name': blp.name, 'description': blp.description})
