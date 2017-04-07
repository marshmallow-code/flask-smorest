"""Database and Application mocks"""

from marshmallow import Schema, fields

from flask import Flask, abort
from flask.views import MethodView

from flask_rest_api import Api, Blueprint

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


def create_app_mock(config_cls=None, as_method_view=True):
    """Return a basic API sample

    Generates a simple interface to a mocked database.
    """

    collection = DatabaseMock()

    blp = Blueprint('test', __name__, url_prefix='/test')

    class DocSchema(Schema):
        class Meta:
            strict = True
        item_id = fields.Int(dump_only=True)
        field = fields.Int()

    class DocEtagSchema(Schema):
        class Meta:
            strict = True
        field = fields.Int()

    if as_method_view:
        @blp.route('/')
        class Resource(MethodView):

            @blp.use_args(DocSchema, location='query')
            @blp.marshal_with(
                DocSchema, paginate_with=Page, etag_schema=DocEtagSchema)
            def get(self, args):
                return collection.items

            @blp.use_args(DocSchema)
            @blp.marshal_with(DocSchema, code=201, etag_schema=DocEtagSchema)
            def post(self, new_item):
                return collection.post(new_item)

        @blp.route('/<int:item_id>')
        class ResourceById(MethodView):

            def _get_item(self, item_id):
                try:
                    return collection.get_by_id(item_id)
                except ItemNotFound:
                    abort(404)

            @blp.marshal_with(DocSchema, etag_schema=DocEtagSchema)
            def get(self, item_id):
                return self._get_item(item_id)

            @blp.use_args(DocSchema)
            @blp.marshal_with(DocSchema, etag_schema=DocEtagSchema)
            def put(self, new_item, item_id):
                return collection.put(item_id, new_item)

            @blp.marshal_with(code=204, etag_schema=DocEtagSchema)
            def delete(self, item_id):
                item = self._get_item(item_id)
                del collection.items[collection.items.index(item)]

    else:
        @blp.route('/')
        @blp.use_args(DocSchema, location='query')
        @blp.marshal_with(
            DocSchema, paginate_with=Page, etag_schema=DocEtagSchema)
        def get_resources(args):
            return collection.items

        @blp.route('/', methods=('POST',))
        @blp.use_args(DocSchema)
        @blp.marshal_with(DocSchema, code=201, etag_schema=DocEtagSchema)
        def post_resource(new_item):
            return collection.post(new_item)

        def _get_item(item_id):
            try:
                return collection.get_by_id(item_id)
            except ItemNotFound:
                abort(404)

        @blp.route('/<int:item_id>')
        @blp.marshal_with(
            DocSchema, etag_schema=DocEtagSchema, etag_item_func=_get_item)
        def get_resource(item_id):
            return _get_item(item_id)

        @blp.route('/<int:item_id>', methods=('PUT',))
        @blp.use_args(DocSchema)
        @blp.marshal_with(
            DocSchema, etag_schema=DocEtagSchema, etag_item_func=_get_item)
        def put_resource(new_item, item_id):
            return collection.put(item_id, new_item)

        @blp.route('/<int:item_id>', methods=('DELETE',))
        @blp.marshal_with(
            code=204, etag_schema=DocEtagSchema, etag_item_func=_get_item)
        def delete_resource(item_id):
            item = _get_item(item_id)
            del collection.items[collection.items.index(item)]

    app = Flask('API Test')
    app.response_class = JSONResponse
    if config_cls:
        app.config.from_object(config_cls)
    api = Api(app)
    api.register_blueprint(blp)

    return app, api
