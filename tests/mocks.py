"""Database and Application mocks"""

from marshmallow import Schema, fields

from flask import Flask, abort
from flask.views import MethodView

from flask_rest_api import Api, Blueprint
from flask_rest_api.etag import conditional

# TODO: create a Page mock to remove this dependency?
from paginate import Page

from .utils import JSONResponse


class ItemNotFound(Exception):
    """Item not found"""


class DatabaseMock():
    """Database mock

    Stores data in a list and provides data management methods
    """

    def __init__(self):
        self.items = []
        self.max_id = 0

    def _get_next_id(self):
        self.max_id += 1
        return self.max_id

    def _get_item_index(self, item):
        try:
            return self.items.index(item)
        except ValueError:
            raise ItemNotFound

    def get_by_id(self, item_id):
        try:
            return next(
                i for i in self.items if i['item_id'] == item_id)
        except StopIteration:
            raise ItemNotFound

    def post(self, new_item):
        new_item['item_id'] = self._get_next_id()
        self.items.append(new_item)
        return new_item

    def put(self, item_id, new_item):
        item = self.get_by_id(item_id)
        new_item['item_id'] = item_id
        self.items[self.items.index(item)] = new_item
        return new_item

    def delete(self, item_id):
        item = self.get_by_id(item_id)
        index = self._get_item_index(item)
        del self.items[index]


class AppConfig():
    """Base application configuration class
    
    Overload this to add config parameters
    """


def create_app_mock(config_cls=None):
    """Return a basic API sample
    
    Generates a simple interface to a mocked database.
    """

    collection = DatabaseMock()

    blp = Blueprint('test', __name__, url_prefix='/test')

    class DocSchema(Schema):
        item_id = fields.Int(dump_only=True)
        field = fields.Int()

        class Meta:
            strict = True

    @blp.route('/')
    class Resource(MethodView):

        @conditional
        @blp.use_args(DocSchema, location='query')
        @blp.marshal_with(DocSchema, paginate_with=Page)
        def get(self, args):
            return collection.items

        @blp.use_args(DocSchema)
        @blp.marshal_with(DocSchema, code=201)
        def post(self, new_item):
            return collection.post(new_item)

    @blp.route('/<int:item_id>')
    class ResourceById(MethodView):

        def _getter(self, item_id):
            try:
                return collection.get_by_id(item_id)
            except ItemNotFound:
                abort(404)

        @conditional
        @blp.marshal_with(DocSchema)
        def get(self, item_id):
            return self._getter(item_id)

        @conditional
        @blp.use_args(DocSchema)
        @blp.marshal_with(DocSchema)
        def put(self, new_item, item_id):
            return collection.put(item_id, new_item)

        @conditional
        @blp.marshal_with(DocSchema, code=204)
        def delete(self, item_id):
            item = self._getter(item_id)
            del collection.items[collection.items.index(item)]

    app = Flask('API Test')
    app.response_class = JSONResponse
    if config_cls:
        app.config.from_object(config_cls)
    api = Api(app)
    api.register_blueprint(blp)

    return app
