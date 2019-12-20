"""Api extension initialization"""

import http

from webargs.flaskparser import abort  # noqa

from .spec import APISpecMixin, DEFAULT_RESPONSE_CONTENT_TYPE
from .blueprint import Blueprint  # noqa
from .pagination import Page  # noqa
from .error_handler import ErrorHandlerMixin

__version__ = '0.18.5'


class Api(APISpecMixin, ErrorHandlerMixin):
    """Main class

    Provides helpers to build a REST API using Flask.

    :param Flask app: Flask application
    :param dict spec_kwargs: kwargs to pass to internal APISpec instance

    The ``spec_kwargs`` dictionary is passed as kwargs to the internal APISpec
    instance. **flask-smorest** adds a few parameters to the original
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
        self._spec_kwargs = spec_kwargs or {}
        self.spec = None
        # Use lists to enforce order
        self._fields = []
        self._converters = []
        if app is not None:
            self.init_app(app)

    def init_app(self, app, *, spec_kwargs=None):
        """Initialize Api with application

        :param dict spec_kwargs: kwargs to pass to internal APISpec instance.
            Updates ``spec_kwargs`` passed in ``Api`` init.
        """
        self._app = app

        # Register flask-smorest in app extensions
        app.extensions = getattr(app, 'extensions', {})
        ext = app.extensions.setdefault('flask-smorest', {})
        ext['ext_obj'] = self

        # Initialize spec
        self._init_spec(**{**self._spec_kwargs, **(spec_kwargs or {})})

        # Initialize blueprint serving spec
        self._register_doc_blueprint()

        # Register error handlers
        self._register_error_handlers()

        # Resister error responses
        self._register_response(
            'Default Error',
            {
                'description': 'Default error response',
                'schema': self.ERROR_SCHEMA,
            }
        )
        self._register_default_response(422)
        if not app.config.get('ETAG_DISABLED', False):
            self._register_default_response(304)
            self._register_default_response(412)
            self._register_default_response(428)

    def _register_default_response(self, code):
        """Register a Response for a given status code

        :param int code: Status code
        """
        self._register_response(
            http.HTTPStatus(code).phrase,
            {
                'description': http.HTTPStatus(code).phrase,
                'schema': self.ERROR_SCHEMA,
            }
        )

    def _register_response(self, component_id, component):
        """Register a Response component

        Abstracts OpenAPI version and content type.
        """
        if self.spec.openapi_version.major >= 3:
            if 'schema' in component:
                component['content'] = {
                    DEFAULT_RESPONSE_CONTENT_TYPE: {
                        'schema': component.pop('schema')}}
        self.spec.components.response(component_id, component)

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
