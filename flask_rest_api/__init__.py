"""Api extension initialization"""

from webargs.flaskparser import abort  # noqa

from .spec import APISpec, DocBlueprintMixin
from .blueprint import Blueprint  # noqa
from .pagination import Page  # noqa
from .error_handler import ErrorHandlerMixin
from .compat import APISPEC_VERSION_MAJOR

__version__ = '0.11.1'


class Api(DocBlueprintMixin, ErrorHandlerMixin):
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
        spec_kwargs = spec_kwargs or {}
        openapi_version = app.config.get('OPENAPI_VERSION', '2.0')
        openapi_major_version = int(openapi_version.split('.')[0])
        if openapi_major_version < 3:
            base_path = app.config.get('APPLICATION_ROOT')
            # Don't pass basePath if '/' to avoid a bug in apispec
            # https://github.com/marshmallow-code/apispec/issues/78#issuecomment-431854606
            # TODO: Remove this condition when the bug is fixed
            if base_path != '/':
                spec_kwargs.setdefault('basePath', base_path)
        spec_kwargs.update(app.config.get('API_SPEC_OPTIONS', {}))
        self.spec = APISpec(
            app.name,
            app.config.get('API_VERSION', '1'),
            openapi_version=openapi_version,
            **spec_kwargs,
        )
        # Initialize blueprint serving spec
        self._register_doc_blueprint()

        # Register error handlers
        self._register_error_handlers()

    def register_blueprint(self, blp, **options):
        """Register a blueprint in the application

        Also registers documentation for the blueprint/resource

        :param Blueprint blp: Blueprint to register
        :param dict options: Keyword arguments overriding Blueprint defaults
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
            if APISPEC_VERSION_MAJOR < 1:
                self.spec.definition(name, schema=schema_cls, **kwargs)
            else:
                self.spec.components.schema(name, schema=schema_cls, **kwargs)
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
