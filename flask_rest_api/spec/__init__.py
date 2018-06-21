"""API specification using Open API"""

import json

import flask
from flask import current_app
import apispec
from apispec.ext.marshmallow.swagger import map_to_swagger_type

from .plugin import CONVERTER_MAPPING


PLUGINS = (
    'flask_rest_api.spec.plugin',
    # XXX: Ideally, we shouldn't register schema_path_helper but it's
    # hard to extract only what we want from apispec.ext.marshmallow
    'apispec.ext.marshmallow',
)


def _add_leading_slash(string):
    """Add leading slash to a string if there is None"""
    return string if string[0] == '/' else '/' + string


class APISpec(apispec.APISpec):
    """API specification class

    :param Flask app: Flask application
    """
    def __init__(self, app):
        super().__init__(
            title=app.name,
            version=app.config.get('API_VERSION', '1'),
            plugins=PLUGINS,
            openapi_version=app.config.get('OPENAPI_VERSION', '2.0')
        )
        self._app = app

        # Add routes to json spec file and spec UI (ReDoc)
        api_url = app.config.get('OPENAPI_URL_PREFIX', None)
        if api_url:
            # TODO: Remove this when dropping Flask < 1.0 compatibility
            # Strip single trailing slash (flask.Blueprint does it from v1.0)
            if api_url and api_url[-1] == '/':
                api_url = api_url[:-1]
            blueprint = flask.Blueprint(
                'api-docs',
                __name__,
                url_prefix=_add_leading_slash(api_url),
                template_folder='./templates',
            )
            # Serve json spec at 'url_prefix/openapi.json' by default
            json_path = app.config.get('OPENAPI_JSON_PATH', '/openapi.json')
            blueprint.add_url_rule(
                _add_leading_slash(json_path),
                endpoint='openapi_json',
                view_func=self._openapi_json)
            # Serve ReDoc only if path specified
            redoc_path = app.config.get('OPENAPI_REDOC_PATH', None)
            if redoc_path:
                blueprint.add_url_rule(
                    _add_leading_slash(redoc_path),
                    endpoint='openapi_redoc',
                    view_func=self._openapi_redoc)
            # Serve Swagger UI only if path and version specified
            swagger_ui_path = app.config.get('OPENAPI_SWAGGER_UI_PATH', None)
            swagger_ui_version = app.config.get(
                'OPENAPI_SWAGGER_UI_VERSION', None)
            if swagger_ui_path and swagger_ui_version:
                blueprint.add_url_rule(
                    _add_leading_slash(swagger_ui_path),
                    endpoint='openapi_swagger_ui',
                    view_func=self._openapi_swagger_ui)
            app.register_blueprint(blueprint)

    def _openapi_json(self):
        """Serve JSON spec file"""
        # We don't use Flask.jsonify here as it would sort the keys
        # alphabetically while we want to preserve the order.
        return current_app.response_class(
            json.dumps(self.to_dict(), indent=2),
            mimetype='application/json')

    def _openapi_redoc(self):
        """Expose OpenAPI spec with ReDoc

        The ReDoc script URL can be specified as OPENAPI_REDOC_URL.

        Otherwise, a CDN script is used based on the ReDoc version. The
        version can - and should - be specified as OPENAPI_REDOC_VERSION,
        otherwise, 'latest' is used.

        When using 1.x branch (i.e. when OPENAPI_REDOC_VERSION is "latest" or
        begins with "v1"), GitHub CDN is used.

        When using 2.x branch (i.e. when OPENAPI_REDOC_VERSION is "next" or
        begins with "2" or "v2"), unpkg nmp CDN is used.

        OPENAPI_REDOC_VERSION is ignored when OPENAPI_REDOC_URL is passed.
        """
        redoc_url = self._app.config.get('OPENAPI_REDOC_URL', None)
        if redoc_url is None:
            # TODO: default to 'next' when ReDoc 2.0.0 is released.
            redoc_version = self._app.config.get(
                'OPENAPI_REDOC_VERSION', 'latest')
            # latest or v1.x -> Redoc GitHub CDN
            if redoc_version == 'latest' or redoc_version.startswith('v1'):
                redoc_url = (
                    'https://rebilly.github.io/ReDoc/releases/'
                    '{}/redoc.min.js'.format(redoc_version))
            # next or 2.x -> unpkg npm CDN
            else:
                redoc_url = (
                    'https://cdn.jsdelivr.net/npm/redoc@'
                    '{}/bundles/redoc.standalone.js'.format(redoc_version))
        return flask.render_template(
            'redoc.html', title=self._app.name, redoc_url=redoc_url)

    def _openapi_swagger_ui(self):
        """Expose OpenAPI spec with Swagger UI

        The Swagger UI scripts base URL can be specified as
        OPENAPI_SWAGGER_UI_URL.

        Otherwise, cdnjs is used. In this case, the Swagger UI version must be
        specified as OPENAPI_SWAGGER_UI_VERSION. Versions older than 3.x branch
        are not supported.

        OPENAPI_SWAGGER_UI_VERSION is ignored when OPENAPI_SWAGGER_UI_URL is
        passed.

        OPENAPI_SWAGGER_UI_SUPPORTED_SUBMIT_METHODS specifes the methods for
        which the 'Try it out!' feature is enabled.
        """
        swagger_ui_url = self._app.config.get('OPENAPI_REDOC_URL', None)
        if swagger_ui_url is None:
            swagger_ui_version = self._app.config.get(
                'OPENAPI_SWAGGER_UI_VERSION', None)
            if swagger_ui_version is not None:
                swagger_ui_url = (
                    'https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/'
                    '{}/'.format(swagger_ui_version))
        swagger_ui_supported_submit_methods = self._app.config.get(
            'OPENAPI_SWAGGER_UI_SUPPORTED_SUBMIT_METHODS', [])
        return flask.render_template(
            'swagger_ui.html', title=self._app.name,
            swagger_ui_url=swagger_ui_url,
            swagger_ui_supported_submit_methods=(
                swagger_ui_supported_submit_methods)
        )

    @staticmethod
    def register_converter(converter, conv_type, conv_format=None):
        """Register custom path parameter converter

        :param BaseConverter converter: Converter.
            Subclass of werkzeug's BaseConverter
        :param str conv_type: Parameter type
        :param str conv_format: Parameter format (optional)

        Example: ::

            app.url_map.converters['uuid'] = UUIDConverter
            api.spec.register_converter(UUIDConverter, 'string', 'UUID')

            @blp.route('/pets/{uuid:pet_id}')
            ...

            api.register_blueprint(blp)

        Once the converter is registered, all paths using it will have their
        path parameter documented with the right type and format.
        """
        CONVERTER_MAPPING[converter] = (conv_type, conv_format)

    @staticmethod
    def register_field(field, *args):
        """Register custom Marshmallow field

        Registering the Field class allows the Schema parser to set the proper
        type and format when documenting parameters from Schema fields.

        :param Field field: Marshmallow Field class

        ``*args`` can be:

        - a pair of the form ``(type, format)`` to map to
        - a core marshmallow field type (then that type's mapping is used)

        Examples: ::

            # Map to ('string, 'UUID')
            api.spec.register_field(UUIDField, 'string', 'UUID')

            # Map to ('integer, 'int32')
            api.spec.register_field(CustomIntegerField, ma.fields.Integer)

        In the first case, if the second element of the tuple is None, it does
        not appear in the spec.
        """
        map_to_swagger_type(*args)(field)
