"""Api extension initialization"""

from werkzeug.exceptions import default_exceptions

from .spec import APISpec
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
        self._apispec = APISpec()
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """Initialize Api with application"""

        self._app = app

        # Register flask-rest-api in app extensions
        app.extensions = getattr(app, 'extensions', {})
        ext = app.extensions.setdefault('flask-rest-api', {})
        ext['ext_obj'] = self

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
        blp.register_views_in_doc(self._app, self._apispec)

        # Add tag relative to this resource to the global tag list
        self._apispec.add_tag({
            'name': blp.name,
            'description': blp.description,
        })

    def definition(self, name):
        """Decorator to register a Schema in the doc

        This allows a schema to be defined once in the `definitions`
        section of the spec and be referenced throughtout the spec.

        :param str name: Name of the definition in the spec

            Example: ::

                @api.definition('Pet')
                class PetSchema(Schema):
                    ...
        """
        def wrapper(cls, **kwargs):
            self._apispec.definition(name, schema=cls, **kwargs)
            return cls
        return wrapper

    def register_converter(self, converter, conv_type, conv_format=None):
        """Register custom path parameter converter

        :param BaseConverter converter: Converter.
            Subclass of werkzeug's BaseConverter
        :param str conv_type: Parameter type
        :param str conv_format: Parameter format (optional)

            Example: ::

                app.url_map.converters['uuid'] = UUIDConverter
                api.register_converter(UUIDConverter, 'string', 'UUID')

                @blp.route('/pets/{uuid:pet_id}')
                ...

                api.register_blueprint(blp)

        Once the converter is registered, all paths using it will have their
        path parameter documented with the right type and format.

        Note: This method does not register the converter in the Flask app
        but only in the spec.
        """
        self._apispec.register_converter(converter, conv_type, conv_format)

    def register_field(self, field, field_type, field_format=None):
        """Register custom Marshmallow field

        :param Field field: Marshmallow Field class
        :param str field_type: Parameter type
        :param str field_format: Parameter format (optional)

            Example: ::

                api.register_field(UUIDField, 'string', 'UUID')

        Registering the Field class allows the Schema parser to set the proper
        type and format when documenting parameters from Schema fields.
        """
        self._apispec.register_field(field, field_type, field_format)

    def register_spec_plugin(self, plugin_path):
        """Register apispec plugin

        :param str plugin_path: Import path to plugin

        This allows the application to define custom apispec helpers.
        """
        self._apispec.setup_plugin(plugin_path)
