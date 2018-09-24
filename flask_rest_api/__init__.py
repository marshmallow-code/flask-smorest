"""Api extension initialization"""

from werkzeug.exceptions import default_exceptions

from .spec import APISpec, DocBlueprintMixin
from .blueprint import Blueprint  # noqa
from .args_parser import abort  # noqa
from .etag import is_etag_enabled, check_etag, set_etag  # noqa
from .pagination import Page, set_item_count  # noqa
from .error_handler import handle_http_exception


__version__ = '0.8.1'


class Api(DocBlueprintMixin):
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
        self.spec = APISpec(
            app.name,
            app.config.get('API_VERSION', '1'),
            openapi_version=app.config.get('OPENAPI_VERSION', '2.0'),
            **{
                **(spec_kwargs or {}),
                **app.config.get('API_SPEC_OPTIONS', {})
            },
        )
        # Initialize blueprint serving spec
        self.register_doc_blueprint()

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

    def register_converter(self, converter, conv_type, conv_format=None,
                           *, name=None):
        """Register custom path parameter converter

        :param BaseConverter converter: Converter
            Subclass of werkzeug's BaseConverter
        :param str conv_type: Parameter type
        :param str conv_format: Parameter format (optional)
        :param str name: Name of the converter. If not None, this name is used
            to register the converter in the Flask app.

            Example: ::

                api.register_converter(
                    UUIDConverter, 'string', 'UUID', name='uuid')

                @blp.route('/pets/{uuid:pet_id}')
                    ...

                api.register_blueprint(blp)

        This registers the converter in the Flask app and in the internal
        APISpec instance.

        Once the converter is registered, all paths using it will have
        corresponding path parameter documented with the right type and format.

        The `name` parameter need not be passed if the converter is already
        registered in the app, for instance if it belongs to a Flask extension
        that already registers it in the app.
        """
        if name:
            self._app.url_map.converters[name] = converter
        self.spec.register_converter(converter, conv_type, conv_format)

    def register_field(self, field, *args):
        """Register custom Marshmallow field

        Registering the Field class allows the Schema parser to set the proper
        type and format when documenting parameters from Schema fields.

        :param Field field: Marshmallow Field class

        ``*args`` can be:

        - a pair of the form ``(type, format)`` to map to
        - a core marshmallow field type (then that type's mapping is used)

        Examples: ::

            # Map to ('string', 'UUID')
            api.register_field(UUIDField, 'string', 'UUID')

            # Map to ('string')
            api.register_field(URLField, 'string', None)

            # Map to ('integer, 'int32')
            api.register_field(CustomIntegerField, ma.fields.Integer)
        """
        self.spec.register_field(field, *args)
