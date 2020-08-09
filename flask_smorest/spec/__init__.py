"""API specification using OpenAPI"""
import json
import http

import flask
from flask import current_app
import click
import apispec
from apispec.ext.marshmallow import MarshmallowPlugin

from flask_smorest.exceptions import MissingAPIParameterError
from flask_smorest.utils import prepare_response
from .plugins import FlaskPlugin
from .field_converters import uploadfield2properties


def _add_leading_slash(string):
    """Add leading slash to a string if there is None"""
    return string if string.startswith('/') else '/' + string


DEFAULT_REQUEST_BODY_CONTENT_TYPE = 'application/json'
DEFAULT_RESPONSE_CONTENT_TYPE = 'application/json'


class DocBlueprintMixin:
    """Extend Api to serve the spec in a dedicated blueprint."""

    def _register_doc_blueprint(self):
        """Register a blueprint in the application to expose the spec

        Doc Blueprint contains routes to
        - json spec file
        - spec UI (ReDoc, Swagger UI).
        """
        api_url = self._app.config.get('OPENAPI_URL_PREFIX', None)
        if api_url is not None:
            blueprint = flask.Blueprint(
                'api-docs',
                __name__,
                url_prefix=_add_leading_slash(api_url),
                template_folder='./templates',
            )
            # Serve json spec at 'url_prefix/openapi.json' by default
            json_path = self._app.config.get(
                'OPENAPI_JSON_PATH', 'openapi.json')
            blueprint.add_url_rule(
                _add_leading_slash(json_path),
                endpoint='openapi_json',
                view_func=self._openapi_json)
            self._register_redoc_rule(blueprint)
            self._register_swagger_ui_rule(blueprint)
            self._app.register_blueprint(blueprint)

    def _register_redoc_rule(self, blueprint):
        """Register ReDoc rule

        The ReDoc script URL should be specified as OPENAPI_REDOC_URL.
        """
        redoc_path = self._app.config.get('OPENAPI_REDOC_PATH')
        if redoc_path is not None:
            redoc_url = self._app.config.get('OPENAPI_REDOC_URL')
            if redoc_url is not None:
                self._redoc_url = redoc_url
                blueprint.add_url_rule(
                    _add_leading_slash(redoc_path),
                    endpoint='openapi_redoc',
                    view_func=self._openapi_redoc)

    def _register_swagger_ui_rule(self, blueprint):
        """Register Swagger UI rule

        The Swagger UI scripts base URL should be specified as
        OPENAPI_SWAGGER_UI_URL.
        """
        swagger_ui_path = self._app.config.get('OPENAPI_SWAGGER_UI_PATH')
        if swagger_ui_path is not None:
            swagger_ui_url = self._app.config.get('OPENAPI_SWAGGER_UI_URL')
            if swagger_ui_url is not None:
                self._swagger_ui_url = swagger_ui_url
                blueprint.add_url_rule(
                    _add_leading_slash(swagger_ui_path),
                    endpoint='openapi_swagger_ui',
                    view_func=self._openapi_swagger_ui)

    def _openapi_json(self):
        """Serve JSON spec file"""
        # We don't use Flask.jsonify here as it would sort the keys
        # alphabetically while we want to preserve the order.
        return current_app.response_class(
            json.dumps(self.spec.to_dict(), indent=2),
            mimetype='application/json')

    def _openapi_redoc(self):
        """Expose OpenAPI spec with ReDoc"""
        return flask.render_template(
            'redoc.html', title=self.spec.title, redoc_url=self._redoc_url)

    def _openapi_swagger_ui(self):
        """Expose OpenAPI spec with Swagger UI"""
        return flask.render_template(
            'swagger_ui.html',
            title=self.spec.title,
            swagger_ui_url=self._swagger_ui_url,
            swagger_ui_config=self._app.config.get(
                'OPENAPI_SWAGGER_UI_CONFIG', {})
        )


class APISpecMixin(DocBlueprintMixin):
    """Add APISpec related features to Api class"""

    def _init_spec(
            self, *,
            flask_plugin=None, marshmallow_plugin=None, extra_plugins=None,
            title=None, version=None, openapi_version=None,
            **options
    ):
        # Plugins
        self.flask_plugin = flask_plugin or FlaskPlugin()
        self.ma_plugin = marshmallow_plugin or MarshmallowPlugin()
        plugins = [self.flask_plugin, self.ma_plugin]
        plugins.extend(extra_plugins or ())

        # APISpec options
        title = self._app.config.get('API_TITLE', title)
        if title is None:
            raise MissingAPIParameterError(
                'API title must be specified either as "API_TITLE" '
                'app parameter or as "title" spec kwarg.'
            )
        version = self._app.config.get('API_VERSION', version)
        if version is None:
            raise MissingAPIParameterError(
                'API version must be specified either as "API_VERSION" '
                'app parameter or as "version" spec kwarg.'
            )
        openapi_version = self._app.config.get(
            'OPENAPI_VERSION', openapi_version)
        if openapi_version is None:
            raise MissingAPIParameterError(
                'OpenAPI version must be specified either as "OPENAPI_VERSION '
                'app parameter or as "openapi_version" spec kwarg.'
            )
        openapi_major_version = int(openapi_version.split('.')[0])
        if openapi_major_version < 3:
            base_path = self._app.config.get('APPLICATION_ROOT')
            options.setdefault('basePath', base_path)
            options.setdefault(
                'produces', [DEFAULT_RESPONSE_CONTENT_TYPE, ])
            options.setdefault(
                'consumes', [DEFAULT_REQUEST_BODY_CONTENT_TYPE, ])
        options.update(self._app.config.get('API_SPEC_OPTIONS', {}))

        # Instantiate spec
        self.spec = apispec.APISpec(
            title, version, openapi_version, plugins, **options,
        )

        # Register custom fields in spec
        for args in self._fields:
            self._register_field(*args)
        # Register custom converters in spec
        for args in self._converters:
            self._register_converter(*args)
        # Register Upload field properties function
        self.ma_plugin.converter.add_attribute_function(uploadfield2properties)

        # Register OpenAPI command group
        self._app.cli.add_command(openapi_cli)

    def register_converter(self, converter, func):
        """Register custom path parameter converter

        :param BaseConverter converter: Converter
            Subclass of werkzeug's BaseConverter
        :param callable func: Function returning a parameter schema from
            a converter intance

        Example: ::

            # Register MongoDB's ObjectId converter in Flask application
            app.url_map.converters['objectid'] = ObjectIdConverter

            # Define custom converter to schema function
            def objectidconverter2paramschema(converter):
                return {'type': 'string', 'format': 'ObjectID'}

            # Register converter in Api
            api.register_converter(
                ObjectIdConverter,
                objectidconverter2paramschema
            )

            @blp.route('/pets/{objectid:pet_id}')
                ...

            api.register_blueprint(blp)

        Once the converter is registered, all paths using it will have
        corresponding path parameter documented with the right schema.

        Should be called before registering paths with
        :meth:`Blueprint.route <Blueprint.route>`.
        """
        self._converters.append((converter, func))
        # Register converter in spec if app is already initialized
        if self.spec is not None:
            self._register_converter(converter, func)

    def _register_converter(self, converter, func):
        self.flask_plugin.register_converter(converter, func)

    def register_field(self, field, *args):
        """Register custom Marshmallow field

        Registering the Field class allows the Schema parser to set the proper
        type and format when documenting parameters from Schema fields.

        :param Field field: Marshmallow Field class

        ``*args`` can be:

        - a pair of the form ``(type, format)`` to map to
        - a core marshmallow field type (then that type's mapping is used)

        Examples: ::

            # Map to ('string', 'ObjectId') passing type and format
            api.register_field(ObjectId, 'string', 'ObjectId')

            # Map to ('string', ) passing type
            api.register_field(CustomString, 'string', None)

            # Map to ('string, 'date-time') passing a marshmallow Field
            api.register_field(CustomDateTime, ma.fields.DateTime)

        Should be called before registering schemas with
        :meth:`schema <Api.schema>`.
        """
        self._fields.append((field, *args))
        # Register field in spec if app is already initialized
        if self.spec is not None:
            self._register_field(field, *args)

    def _register_field(self, field, *args):
        self.ma_plugin.map_to_openapi_type(*args)(field)

    def _register_responses(self):
        """Register default responses for all status codes"""
        # Register a response for each status code
        for status in http.HTTPStatus:
            response = {
                'description': status.phrase,
                'schema': self.ERROR_SCHEMA,
            }
            prepare_response(
                response, self.spec, DEFAULT_RESPONSE_CONTENT_TYPE)
            self.spec.components.response(status.name, response)

        # Also register a default error response
        response = {
            'description': 'Default error response',
            'schema': self.ERROR_SCHEMA,
        }
        prepare_response(response, self.spec, DEFAULT_RESPONSE_CONTENT_TYPE)
        self.spec.components.response('DEFAULT_ERROR', response)


openapi_cli = flask.cli.AppGroup('openapi', help='OpenAPI commands.')


@openapi_cli.command('print')
def print_openapi_doc():
    """Print OpenAPI document."""
    api = current_app.extensions['flask-smorest']['ext_obj']
    print(json.dumps(api.spec.to_dict(), indent=2))


@openapi_cli.command('write')
@click.argument('output_file', type=click.File(mode='w'))
def write_openapi_doc(output_file):
    """Write OpenAPI document to a file."""
    api = current_app.extensions['flask-smorest']['ext_obj']
    output_file.write(json.dumps(api.spec.to_dict(), indent=2))
