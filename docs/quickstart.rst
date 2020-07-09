.. _quickstart:
.. currentmodule:: flask_smorest

Quickstart
==========

Introduction
------------

``flask-smorest`` makes a few assumptions about how the code should be structured.

The application should be split in :class:`Blueprint <Blueprint>`.
It is possible to use basic Flask view functions but it is generally a good idea
to use Flask :class:`MethodView <flask.views.MethodView>` classes instead.

Marshmallow :class:`Schema <marshmallow.Schema>` are used to serialize parameters
and responses.

Request and response bodies are serialized as `JSON`.

A view function only has one successful response type and status code. All other
possible responses are errors.


Simple Example
--------------

Here is a basic "Petstore example", where The ``Pet`` class is an imaginary ORM.

First instantiate an :class:`Api <Api>` with a :class:`Flask <flask.Flask>` application.


.. code-block:: python

    from flask import Flask
    from flask.views import MethodView
    import marshmallow as ma
    from flask_smorest import Api, Blueprint, abort

    from .model import Pet

    app = Flask(__name__)
    app.config['API_TITLE'] = 'My API'
    app.config['API_VERSION'] = 'v1'
    app.config['OPENAPI_VERSION'] = '3.0.2'
    api = Api(app)

Define a marshmallow :class:`Schema <marshmallow.Schema>` to expose the model.

.. code-block:: python

    class PetSchema(ma.Schema):
        id = ma.fields.Int(dump_only=True)
        name = ma.fields.String()


Define a marshmallow :class:`Schema <marshmallow.Schema>` to validate the
query arguments.

.. code-block:: python

    class PetQueryArgsSchema(ma.Schema):
        name = ma.fields.String()


Instantiate a :class:`Blueprint <Blueprint>`.

.. code-block:: python

    blp = Blueprint(
        'pets', 'pets', url_prefix='/pets',
        description='Operations on pets'
    )

Use :class:`MethodView <flask.views.MethodView>` classes to organize resources,
and decorate view methods with :meth:`Blueprint.arguments <Blueprint.arguments>`
and :meth:`Blueprint.response <Blueprint.response>` to specify request
deserialization and response serialization respectively.

Use :func:`abort <abort>` to return errors, passing kwargs used by the error
handler (:meth:`handle_http_exception <Api.handle_http_exception>`) to build
the error response.

.. code-block:: python

    @blp.route('/')
    class Pets(MethodView):

        @blp.arguments(PetQueryArgsSchema, location='query')
        @blp.response(PetSchema(many=True))
        def get(self, args):
            """List pets"""
            return Pet.get(filters=args)

        @blp.arguments(PetSchema)
        @blp.response(PetSchema, code=201)
        def post(self, new_data):
            """Add a new pet"""
            item = Pet.create(**new_data)
            return item


    @blp.route('/<pet_id>')
    class PetsById(MethodView):

        @blp.response(PetSchema)
        def get(self, pet_id):
            """Get pet by ID"""
            try:
                item = Pet.get_by_id(pet_id)
            except ItemNotFoundError:
                abort(404, message='Item not found.')
            return item

        @blp.arguments(PetSchema)
        @blp.response(PetSchema)
        def put(self, update_data, pet_id):
            """Update existing pet"""
            try:
                item = Pet.get_by_id(pet_id)
            except ItemNotFoundError:
                abort(404, message='Item not found.')
            item.update(update_data)
            item.commit()
            return item

        @blp.response(code=204)
        def delete(self, pet_id):
            """Delete pet"""
            try:
                Pet.delete(pet_id)
            except ItemNotFoundError:
                abort(404, message='Item not found.')


Finally, register the :class:`Blueprint <Blueprint>` in the :class:`Api <Api>`.

.. code-block:: python

    api.register_blueprint(blp)
