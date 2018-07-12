.. _quickstart:
.. module:: flask_rest_api

Quickstart
==========

``flask-rest-api`` makes a few assumptions about how the code should be structured.

The application should be split in :class:`Blueprint <Blueprint>`.
It is possible to use basic Flask view functions but it is generally a good idea
to use Flask :class:`MethodView <flask.views.MethodView>` classes instead.

Marshmallow :class:`Schema <marshmallow.Schema>` are used to serialize parameters
and responses. It may look overkill for a method with a single parameter, but it
makes the code consistent and it is easier to support.

Here is a basic "Petstore example", where The ``Pet`` class is an imaginary ORM.

First instantiate an :class:`Api <Api>` with a :class:`Flask <flask.Flask>` application.


.. code-block:: python

    from flask import Flask
    from flask.views import MethodView
    import marshmallow as ma
    from flask_rest_api import Api, Blueprint

    from .model import Pet

    app = Flask('My API')
    api = Api(app)

Define a marshmallow :class:`Schema <marshmallow.Schema>` to expose the model.

.. code-block:: python

    @api.definition('Pet')
    class PetSchema(ma.Schema):

        class Meta:
            strict = True
            ordered = True

        id = ma.fields.Int(dump_only=True)
        name = ma.fields.String()


Define a marshmallow :class:`Schema <marshmallow.Schema>` to validate the
query arguments.

.. code-block:: python

    class PetQueryArgsSchema(ma.Schema):

        class Meta:
            strict = True
            ordered = True

        name = ma.fields.String()


Instantiate a :class:`Blueprint <Blueprint>`.

.. code-block:: python

    blp = Blueprint(
        'pets', 'pets', url_prefix='/pets',
        description='Operations on pets'
    )

:class:`MethodView <flask.views.MethodView>` classes come in handy when dealing
with REST APIs.

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
            item = Pet.get_by_id(pet_id)
            return item

        @blp.arguments(PetSchema)
        @blp.response(PetSchema)
        def put(self, update_data, pet_id):
            """Update existing pet"""
            item = Pet.get_by_id(pet_id)
            item.update(update_data)
            return item

        @blp.response(code=204)
        def delete(self, pet_id):
            """Delete pet"""
            Pet.delete(pet_id)


Finally, register the :class:`Blueprint <Blueprint>` in the :class:`Api <Api>`.

.. code-block:: python

    api.register_blueprint(blp)
