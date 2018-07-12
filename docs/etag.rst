.. _etag:
.. module:: flask_rest_api

ETag
====

ETag is a web cache validation mechanism. It allows an API client to make
conditional requests, such as

- GET a resource unless it is the same as the version in cache.
- PUT/PATCH/DELETE a resource unless the version in cache is outdated.

The first case is mostly useful to limit the bandwidth usage, the latter
addresses the case where two clients update a resource at the same time (known
as the "*lost update problem*").

The ETag featured is enabled with the `ETAG_ENABLED` application parameter. It
can be disabled function-wise by passing `disable_etag=False` to the
:meth:`Blueprint.response <Blueprint.response>` decorator.

`flask-rest-api` provides helpers to compute ETag, but ultimately, only the
developer knows what data is relevant to use as ETag source, so there can be
manual work involved.

ETag Computed with API Response Data
------------------------------------

The simplest case is when the ETag is computed using returned data, using the
:class:`Schema <marshmallow.Schema>` that serializes the data.

In this case, almost eveything is automatic. Only the call to
:meth:`check_etag <etag.check_etag>` is manual.

The :class:`Schema <marshmallow.Schema>` must be provided explicitly, even
though it is the same as the response schema.

.. code-block:: python
    :emphasize-lines: 27,35

    from flask_rest_api import check_etag

    @blp.route('/')
    class Pet(MethodView):

        @blp.response(PetSchema(many=True))
        def get(self):
            return Pet.get()

        @blp.arguments(PetSchema)
        @blp.response(PetSchema)
        def post(self, new_data):
            return Pet.create(**new_data)

    @blp.route('/<pet_id>')
    class PetById(MethodView):

        @blp.response(PetSchema)
        def get(self, pet_id):
            return Pet.get_by_id(pet_id)

        @blp.arguments(PetSchema)
        @blp.response(PetSchema)
        def put(self, update_data, pet_id):
            pet = Pet.get_by_id(pet_id)
            # Check ETag is a manual action and schema must be provided
            check_etag(pet, PetSchema)
            pet.update(update_data)
            return pet

        @blp.response(code=204)
        def delete(self, pet_id):
            pet = Pet.get_by_id(pet_id)
            # Check ETag is a manual action and schema must be provided
            check_etag(pet, PetSchema)
            Pet.delete(pet_id)

ETag Computed with API Response Data Using Another Schema
---------------------------------------------------------

Sometimes, it is not possible to use the data returned by the view function as
ETag data because it contains extra information that is irrelevant, like
HATEOAS information, for instance.

In this case, a specific ETag schema can be provided as ``etag_schema`` keyword
argument to :meth:`Blueprint.response <Blueprint.response>`. Then, it does not
need to be passed to :meth:`check_etag <etag.check_etag>`.

.. code-block:: python
    :emphasize-lines: 7,12,19,24,28,32,36

    from flask_rest_api import check_etag

    @blp.route('/')
    class Pet(MethodView):

        @blp.response(
            PetSchema(many=True), etag_schema=PetEtagSchema(many=True))
        def get(self):
            return Pet.get()

        @blp.arguments(PetSchema)
        @blp.response(PetSchema, etag_schema=PetEtagSchema)
        def post(self, new_pet):
            return Pet.create(**new_data)

    @blp.route('/<int:pet_id>')
    class PetById(MethodView):

        @blp.response(PetSchema, etag_schema=PetEtagSchema)
        def get(self, pet_id):
            return Pet.get_by_id(pet_id)

        @blp.arguments(PetSchema)
        @blp.response(PetSchema, etag_schema=PetEtagSchema)
        def put(self, new_pet, pet_id):
            pet = Pet.get_by_id(pet_id)
            # Check ETag is a manual action and schema must be provided
            check_etag(pet)
            pet.update(update_data)
            return pet

        @blp.response(code=204, etag_schema=PetEtagSchema)
        def delete(self, pet_id):
            pet = self._get_pet(pet_id)
            # Check ETag is a manual action, ETag schema is used
            check_etag(pet)
            Pet.delete(pet_id)

ETag Computed on Arbitrary Data
-------------------------------

The ETag can also be computed from arbitrary data by calling
:meth:`set_etag <etag.set_etag>` manually.

The example below illustrates this with no ETag schema, but it is also possible
to pass an ETag schema to :meth:`set_etag <etag.set_etag>` and
:meth:`check_etag <etag.check_etag>` or equivalently to
:meth:`Blueprint.response <Blueprint.response>`.

.. code-block:: python
    :emphasize-lines: 10,17,26,34,37,44

    from flask_rest_api import check_etag, set_etag

    @blp.route('/')
    class Pet(MethodView):

        @blp.response(PetSchema(many=True))
        def get(self):
            pets = Pet.get()
            # Compute ETag using arbitrary data
            set_etag([pet.update_time for pet in pets])
            return pets

        @blp.arguments(PetSchema)
        @blp.response(PetSchema)
        def post(self, new_data):
            # Compute ETag using arbitrary data
            set_etag(new_data['update_time'])
            return Pet.create(**new_data)

    @blp.route('/<pet_id>')
    class PetById(MethodView):

        @blp.response(PetSchema)
        def get(self, pet_id):
            # Compute ETag using arbitrary data
            set_etag(new_data['update_time'])
            return Pet.get_by_id(pet_id)

        @blp.arguments(PetSchema)
        @blp.response(PetSchema)
        def put(self, update_data, pet_id):
            pet = Pet.get_by_id(pet_id)
            # Check ETag is a manual action
            check_etag(pet, ['update_time'])
            pet.update(update_data)
            # Compute ETag using arbitrary data
            set_etag(new_data['update_time'])
            return pet

        @blp.response(code=204)
        def delete(self, pet_id):
            pet = Pet.get_by_id(pet_id)
            # Check ETag is a manual action
            check_etag(pet, ['update_time'])
            Pet.delete(pet_id)

Include Headers Content in ETag
-------------------------------

When ETag is computed with response data, that data may contain headers. It is
up to the developer to decide whether this data should be part of the ETag.

By default, only pagination data is included in the ETag computation. The list
of headers to include is defined as:

.. code-block:: python

    INCLUDE_HEADERS = ['X-Pagination']

It can be changed globally by mutating ``flask_rest_api.etag.INCLUDE_HEADERS``.
