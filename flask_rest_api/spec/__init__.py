"""API specification using Open API"""

import flask
from apispec import APISpec

from .plugin import CONVERTER_MAPPING
from apispec.ext.marshmallow.swagger import FIELD_MAPPING


def make_apispec():
    return APISpec(
        title='OpenAPI spec',
        version='v1.0.0',
        plugins=[
            'flask_rest_api.spec.plugin',
            # XXX: Ideally, we shouldn't register schema_path_helper but it's
            # hard to extract only what we want from apispec.ext.marshmallow
            'apispec.ext.marshmallow',
        ]
    )


class ApiSpec:
    """API specification class

    :param Flask app: Flask application
    """

    def __init__(self, app=None):
        self.spec = make_apispec()
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """Initialize ApiSpec with application"""

        self.app = app

        # API info from app
        self.set_title(app.name)
        self.set_version(app.config.get('API_VERSION', 'v1.0.0'))

        # Add routes to json spec file and spec UI (ReDoc)
        api_url = app.config.get('OPENAPI_URL_PREFIX', None)
        if api_url:
            blueprint = flask.Blueprint(
                'api-docs',
                __name__,
                url_prefix=api_url,
                template_folder='./templates',
            )
            # Serve json spec at 'url_prefix/api-docs.json' by default
            json_url = app.config.get('OPENAPI_JSON_PATH', 'api-docs.json')
            blueprint.add_url_rule(
                json_url, view_func=self.openapi_json)
            # Serve ReDoc only if path specified
            redoc_url = app.config.get('OPENAPI_REDOC_PATH', None)
            if redoc_url:
                blueprint.add_url_rule(
                    redoc_url, view_func=self.openapi_redoc)
            app.register_blueprint(blueprint)

    def set_title(self, title):
        self.spec.info['title'] = title

    def set_version(self, version):
        self.spec.info['version'] = version

    def openapi_json(self):
        """Serve JSON spec file"""
        return flask.jsonify(self.spec.to_dict())

    def openapi_redoc(self):
        """Expose OpenAPI spec with ReDoc

        The Redoc script URL can be specified using OPENAPI_REDOC_URL.
        By default, a CDN script is used. When using a CDN script, the
        version can (and should) be specified using OPENAPI_REDOC_VERSION,
        otherwise, 'latest' is used.
        OPENAPI_REDOC_VERSION is ignored when OPENAPI_REDOC_URL is passed.
        """
        redoc_url = self.app.config.get('OPENAPI_REDOC_URL', None)
        if redoc_url is None:
            redoc_version = self.app.config.get(
                'OPENAPI_REDOC_VERSION', 'latest')
            redoc_url = ('https://rebilly.github.io/ReDoc/releases/'
                         '{}/redoc.min.js'.format(redoc_version))
        return flask.render_template(
            'redoc.html', title=self.app.name, redoc_url=redoc_url)

    def register_converter(self, converter, conv_type, conv_format):
        CONVERTER_MAPPING[converter] = (conv_type, conv_format)

    def register_field(self, field, field_type, field_format):
        FIELD_MAPPING[field] = (field_type, field_format)

    def register_spec_plugin(self, plugin):
        self.spec.setup_plugin(plugin)
