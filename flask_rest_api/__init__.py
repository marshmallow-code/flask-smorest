"""Api extension initialization"""

from webargs.flaskparser import abort  # noqa

from .spec import APISpecMixin
from .blueprint import Blueprint  # noqa
from .pagination import Page  # noqa
from .error_handler import ErrorHandlerMixin
from .compat import APISPEC_VERSION_MAJOR

__version__ = '0.12.0'


class Api(APISpecMixin, ErrorHandlerMixin):
    """Main class

    Provides helpers to build a REST API using Flask.

    :param Flask app: Flask application
    :param dict spec_kwargs: kwargs to pass to APISpec

    The spec_kwargs dictionary is passed as kwargs to the internal APISpec
    instance. See :class:`apispec.APISpec <apispec.APISpec>` documentation for
    the list of available parameters. If ``plugins`` are passed, they are
    appended to the default plugins: ``[FlaskPlugin(), MarshmallowPlugin()]``.
    `title`, `version` and `openapi_version` can't be passed here, they are set
    according to the app configuration.
    """
    def __init__(self, app=None, *, spec_kwargs=None):
        self._app = app
        self.spec = None
        # Use lists to enforce order
        self._definitions = []
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
        tag = {'name': blp.name, 'description': blp.description}
        if APISPEC_VERSION_MAJOR < 1:
            self.spec.add_tag(tag)
        else:
            self.spec.tag(tag)
