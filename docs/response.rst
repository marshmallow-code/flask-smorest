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
    :emphasize-lines: 3,8

    @blp.route("/<pet_id>")
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
    :emphasize-lines: 3

    @blp.route("/<pet_id>")
    class PetsById(MethodView):
        @blp.response(204)
        def delete(self, pet_id):
            Pet.delete(pet_id)

If a view function returns a list of objects, the :class:`Schema
<marshmallow.Schema>` must be instanciated with ``many=True``.

.. code-block:: python
    :emphasize-lines: 3

    @blp.route("/")
    class Pets(MethodView):
        @blp.response(200, PetSchema(many=True))
        def get(self, args):
            return Pet.get()

.. note:: If a view function returns a :class:`werkzeug.BaseResponse`, that
   response object is returned unchanged: it is not dumped by the schema and
   the status code is not applied.

.. note:: If a view function returns a tuple containing a status code, this
   status code is used in place of the one specified as ``response`` parameter.
   Doing this is generally a bad idea because the response status code won't
   match the code in the API documentation.

.. _document-alternative-responses:

Documenting Alternative Responses
---------------------------------

The :meth:`Blueprint.response <Blueprint.response>` decorator is meant to
generate and document the response corresponding to the "normal" flow of the
function. There can be alternative flows, if the function raises an exception,
which results in a ``HTTPException``, or if it returns a ``Response`` object
which is returned as is.

Those alternative responses can be documented using the
:meth:`Blueprint.alt_response <Blueprint.alt_response>` decorator. This method
can be passed a reference to a registered response component
(see :ref:`document-top-level-components`) or elements to build the response
documentation like :meth:`Blueprint.response <Blueprint.response>` does.

The ``success`` argument (default: ``False``) indicates whether the response is
part of the normal flow of the program or an aborted response. In the former
case, processing from other decorators such as pagination or ETag apply and are
documented for the status code of the response. The default case is typically
used for error conditions that trigger an exception aborting the function.

A view function may only be decorated once with ``response`` but can be
decorated multiple times with nested ``alt_response``.

Content Type
------------

The content type of all responses is documented by default as ``application/json``.

This value can be overridden in each resource by passing another content type
as ``content_type`` argument in :meth:`Blueprint.response <Blueprint.response>`
and :meth:`Blueprint.response <Blueprint.alt_response>`.

.. note:: The content type is only used for documentation purpose and has no
   impact on response serialization.

File Response
-------------

A file response can be documented by passing the documentation schema in its
dict representation to :meth:`Blueprint.response <Blueprint.response>`:

.. code-block:: python

    @blp.route("/")
    @blp.response(
        200, {"format": "binary", "type": "string"}, content_type="application/csv"
    )
    def func():
        csv_str = ...
        response = Response(csv_str, mimetype="text/csv")
        response.headers.set("Content-Disposition", "attachment", filename="file.csv")
        return response
