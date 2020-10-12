.. _response:
.. currentmodule:: flask_smorest

Response
========

Use :meth:`Blueprint.response <Blueprint.response>` to specify a status code
and a :class:`Schema <marshmallow.Schema>` class or instance to serialize the
response.

In the following examples, the ``GET`` and ``PUT`` methods return an instance
of ``Pet`` serialized with ``PetSchema``:

.. code-block:: python
    :emphasize-lines: 4,9

    @blp.route('/<pet_id>')
    class PetsById(MethodView):

        @blp.response(200, PetSchema)
        def get(self, pet_id):
            return Pet.get_by_id(pet_id)

        @blp.arguments(PetSchema)
        @blp.response(200, PetSchema)
        def put(self, update_data, pet_id):
            pet = Pet.get_by_id(pet_id)
            pet.update(update_data)
            return pet

Here, the ``DELETE`` returns an empty response so no schema is specified.

.. code-block:: python
    :emphasize-lines: 4

    @blp.route('/<pet_id>')
    class PetsById(MethodView):

        @blp.response(204)
        def delete(self, pet_id):
            Pet.delete(pet_id)

If a view function returns a list of objects, the :class:`Schema
<marshmallow.Schema>` must be instanciated with ``many=True``.

.. code-block:: python
    :emphasize-lines: 4

    @blp.route('/')
    class Pets(MethodView):

        @blp.response(200, PetSchema(many=True))
        def get(self, args):
            return Pet.get()
