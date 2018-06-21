"""Api extension initialization"""

from werkzeug.exceptions import default_exceptions

from .spec import APISpec
from .blueprint import Blueprint  # noqa
from .args_parser import abort  # noqa
from .etag import is_etag_enabled, check_etag, set_etag  # noqa
from .pagination import Page, set_item_count  # noqa
from .error_handler import handle_http_exception


__version__ = '0.5.2'


class Api:
    """Main class

    Provides helpers to build a REST API using Flask.

    :param Flask app: Flask application
    """

    def __init__(self, app=None):
        self._app = app
        self.spec = None
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
        self.spec = APISpec(app)

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
        blp.register_views_in_doc(self._app, self.spec)

        # Add tag relative to this resource to the global tag list
        self.spec.add_tag({
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
        def decorator(schema_cls, **kwargs):
            self.spec.definition(name, schema=schema_cls, **kwargs)
            return schema_cls
        return decorator

    def register_converter(self, name, converter, conv_type, conv_format=None):
        """Register custom path parameter converter

        :param str name: Name of the converter, used in route declarations
        :param BaseConverter converter: Converter
            Subclass of werkzeug's BaseConverter
        :param str conv_type: Parameter type
        :param str conv_format: Parameter format (optional)

            Example: ::

                api.register_converter('uuid', UUIDConverter, 'string', 'UUID')

                @blp.route('/pets/{uuid:pet_id}')
                ...

                api.register_blueprint(blp)

        This registers the converter in the Flask app and in the internal
        APISpec instance. The call in the example above is equivalent to ::

            app.url_map.converters['uuid'] = UUIDConverter
            api.spec.register_converter(UUIDConverter, 'string', 'UUID')

        Call api.spec.register_converter() directly if the converter is
        already registered in the app, for instance if it comes from a Flask
        extension that already registers it in the app.
        """
        self._app.url_map.converters[name] = converter
        self.spec.register_converter(converter, conv_type, conv_format)
