.. _arguments:
.. module:: flask_rest_api

Arguments
=========

To inject arguments into a view function, use the :meth:`Blueprint.arguments
<Blueprint.arguments>` decorator.

This method takes a :class:`Schema <marshmallow.Schema>` to deserialize and
validate the parameters.

By default, the parameters are expected to be passed as JSON in request body.
The location can be specified with the ``location`` parameter.

Available locations are:

- ``'querystring'`` or ``'query'``
- ``'json'``
- ``'form'``
- ``'headers'``
- ``'cookies'``
- ``'files'``

Unlike webargs's :meth:`use_args <webargs.core.Parser.use_args>` decorator,
:meth:`Blueprint.arguments <Blueprint.arguments>` only accepts a single location.

The input data is deserialized, validated, and injected in the view function as
a dict.


.. code-block:: python
    :emphasize-lines: 4,9

    @blp.route('/')
    class Pets(MethodView):

        @blp.arguments(PetQueryArgsSchema, location='query')
        @blp.response(PetSchema(many=True))
        def get(self, args):
            return Pet.get(filters=args)

        @blp.arguments(PetSchema)
        @blp.response(PetSchema, code=201)
        def post(self, new_data):
            return Pet.create(**new_data)


Keyword arguments provided to :meth:`Blueprint.arguments <Blueprint.arguments>`
are passed to webargs's :meth:`use_args <webargs.core.Parser.use_args>`, which
is called internally.

If ``as_kwargs=True`` is passed, the decorator passes deserialized input data
as keyword arguments rather than as a single positional ``dict`` argument.

.. code-block:: python
    :emphasize-lines: 4,6,7

    @blp.route('/')
    class Pets(MethodView):

        @blp.arguments(PetQueryArgsSchema, location='query', as_kwargs=True)
        @blp.response(PetSchema(many=True))
        def get(self, **kwargs):
            return Pet.get(filters=**kwargs)
