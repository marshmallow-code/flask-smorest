.. _arguments:
.. module:: flask_rest_api

Arguments
=========

To inject arguments into a view function, use the :meth:`Blueprint.arguments
<Blueprint.arguments>` decorator. It allows to specify a :class:`Schema
<marshmallow.Schema>` to deserialize and validate the parameters.

It uses webargs's :meth:`use_args <webargs.core.Parser.use_args>` decorator
internally.

When processing a request, the input data is deserialized, validated, and
injected in the view function.

.. code-block:: python
    :emphasize-lines: 4,6,9,11

    @blp.route('/')
    class Pets(MethodView):

        @blp.arguments(PetQueryArgsSchema, location='query')
        @blp.response(PetSchema(many=True))
        def get(self, args):
            return Pet.get(filters=args)

        @blp.arguments(PetSchema)
        @blp.response(PetSchema, code=201)
        def post(self, pet_data):
            return Pet.create(**pet_data)

Arguments Location
------------------

The list of available locations is available in `webargs documentation 
<https://webargs.readthedocs.io/en/latest/quickstart.html#request-locations>`_.
The location defaults to ``'json'``, which means `body` parameter.

.. note:: Unlike webargs's :meth:`use_args <webargs.core.Parser.use_args>`
   decorator, :meth:`Blueprint.arguments <Blueprint.arguments>` only accepts a
   single location.

Arguments injection
-------------------

By default, arguments are passed as a single positional ``dict`` argument.
If ``as_kwargs=True`` is passed, the decorator passes deserialized input data
as keyword arguments instead.

.. code-block:: python
    :emphasize-lines: 4,6

    @blp.route('/')
    class Pets(MethodView):

        @blp.arguments(PetQueryArgsSchema, location='query', as_kwargs=True)
        @blp.response(PetSchema(many=True))
        def get(self, **kwargs):
            return Pet.get(filters=**kwargs)

This decorator can be called several times on a resource function, for instance
to accept both `body` and `query` parameters. The order of the decorator calls
matters as it determines the order in which the parameters are passed to the
view function.

.. code-block:: python
    :emphasize-lines: 4,5,6

    @blp.route('/')
    class Pets(MethodView):

        @blp.arguments(PetSchema)
        @blp.arguments(QueryArgsSchema, location='query')
        def post(pet_data, query_args):
            return Pet.create(pet_data, **query_args)
