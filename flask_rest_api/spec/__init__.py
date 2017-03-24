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


class ApiSpec(object):

    def __init__(self, app=None):

        self.spec = make_apispec()
        self.app = app

        if app is not None:
            self.init_app(app)

    def init_app(self, app):

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
        """Serve json spec file"""
        return flask.jsonify(self.spec.to_dict())

    def openapi_redoc(self):
        """Serve spec with ReDoc"""
        # TODO: allow local redoc script (currently using CDN)
        redoc_version = self.app.config.get('OPENAPI_REDOC_VERSION', 'latest')
        return flask.render_template('redoc.html', redoc_version=redoc_version)

    def register_converter(self, converter, conv_type, conv_format):
        CONVERTER_MAPPING[converter] = (conv_type, conv_format)

    def register_field(self, field, field_type, field_format):
        FIELD_MAPPING[field] = (field_type, field_format)

    def register_spec_plugin(self, plugin):
        self.spec.setup_plugin(plugin)
