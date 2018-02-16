"""Api extension initialization"""

from werkzeug.exceptions import default_exceptions

from .spec import ApiSpec
from .blueprint import Blueprint  # noqa
from .args_parser import abort  # noqa
from .etag import is_etag_enabled, check_etag, set_etag  # noqa
from .pagination import Page, set_item_count  # noqa
from .error_handler import handle_http_exception


__version__ = '0.1.1'


class Api:
    """Main class

    Provides helpers to build a REST API using Flask.

    :param Flask app: Flask application
    """

    def __init__(self, app=None):
        self._apispec = ApiSpec()
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """Initialize Api with application"""

        self._app = app

        # Register flask-rest-api in app extensions
        app.extensions = getattr(app, 'extensions', {})
        ext = app.extensions.setdefault('flask-rest-api', {})
        ext['ext_obj'] = self
        ext['spec'] = self._apispec.spec

        # Initialize spec
        self._apispec.init_app(app)

        # Can't register a handler for HTTPException, so let's register
        # default handler for each code explicitly.
        # https://github.com/pallets/flask/issues/941#issuecomment-118975275
        for code in default_exceptions:
            app.register_error_handler(code, handle_http_exception)

    def register_blueprint(self, blp):
        """Register a blueprint in the application

        Also registers documentation for the blueprint/resource
        """

        self._app.register_blueprint(blp)

        # Register views in API documentation for this resource
        blp.register_views_in_doc(self._app, self._apispec.spec)

        # Add tag relative to this resource to the global tag list
        self._apispec.spec.add_tag({
            'name': blp.name,
            'description': blp.description,
        })

    def definition(self, name):
        """Decorator to register a schema in the doc

        This allows a schema to be defined once in the `definitions`
        section of the spec and be referenced throughtout the spec.
        """
        def wrapper(cls, **kwargs):
            self._apispec.spec.definition(name, schema=cls, **kwargs)
            return cls
        return wrapper

    def register_converter(self, converter, conv_type, conv_format):
        """Register URL parameter converter in docs"""
        self._apispec.register_converter(converter, conv_type, conv_format)

    def register_field(self, field, field_type, field_format):
        """Register Marshmallow field in docs"""
        self._apispec.register_field(field, field_type, field_format)

    def register_spec_plugin(self, plugin):
        """Register apispec plugin"""
        self._apispec.register_spec_plugin(plugin)
