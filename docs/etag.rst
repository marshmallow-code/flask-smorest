.. _etag:
.. currentmodule:: flask_smorest

ETag
====

ETag is a web cache validation mechanism. It allows an API client to make
conditional requests, such as

- GET a resource unless it is the same as the version in cache.
- PUT/PATCH/DELETE a resource unless the version in cache is outdated.

The first case is mostly useful to limit the bandwidth usage, the latter
addresses the case where two clients update a resource at the same time (known
as the "*lost update problem*").

The ETag featured is available through the
:meth:`Blueprint.etag <Blueprint.etag>` decorator. It can be disabled globally
with the `ETAG_DISABLED` application parameter.

`flask-smorest` provides helpers to compute ETag, but ultimately, only the
developer knows what data is relevant to use as ETag source, so there can be
manual work involved.

ETag Computed with API Response Data
------------------------------------

The simplest case is when the ETag is computed using returned data, using the
:class:`Schema <marshmallow.Schema>` that serializes the data.

In this case, almost eveything is automatic. Only the call to
:meth:`Blueprint.check_etag <Blueprint.check_etag>` is manual.

The :class:`Schema <marshmallow.Schema>` must be provided explicitly, even
though it is the same as the response schema.

.. code-block:: python
    :emphasize-lines: 29,38

    @blp.route('/')
    class Pet(MethodView):

        @blp.etag
        @blp.response(PetSchema(many=True))
        def get(self):
            return Pet.get()

        @blp.etag
        @blp.arguments(PetSchema)
        @blp.response(PetSchema)
        def post(self, new_data):
            return Pet.create(**new_data)

    @blp.route('/<pet_id>')
    class PetById(MethodView):

        @blp.etag
        @blp.response(PetSchema)
        def get(self, pet_id):
            return Pet.get_by_id(pet_id)

        @blp.etag
        @blp.arguments(PetSchema)
        @blp.response(PetSchema)
        def put(self, update_data, pet_id):
            pet = Pet.get_by_id(pet_id)
            # Check ETag is a manual action and schema must be provided
            blp.check_etag(pet, PetSchema)
            pet.update(update_data)
            return pet

        @blp.etag
        @blp.response(code=204)
        def delete(self, pet_id):
            pet = Pet.get_by_id(pet_id)
            # Check ETag is a manual action and schema must be provided
            blp.check_etag(pet, PetSchema)
            Pet.delete(pet_id)

ETag Computed with API Response Data Using Another Schema
---------------------------------------------------------

Sometimes, it is not possible to use the data returned by the view function as
ETag data because it contains extra information that is irrelevant, like
HATEOAS information, for instance.

In this case, a specific ETag schema should be provided to
:meth:`Blueprint.etag <Blueprint.etag>`. Then, it does not need to be passed to
:meth:`check_etag <Blueprint.check_etag>`.

.. code-block:: python
    :emphasize-lines: 4,9,18,23,29,33,38

    @blp.route('/')
    class Pet(MethodView):

        @blp.etag(PetEtagSchema(many=True))
        @blp.response(PetSchema(many=True))
        def get(self):
            return Pet.get()

        @blp.etag(PetEtagSchema)
        @blp.arguments(PetSchema)
        @blp.response(PetSchema)
        def post(self, new_pet):
            return Pet.create(**new_data)

    @blp.route('/<int:pet_id>')
    class PetById(MethodView):

        @blp.etag(PetEtagSchema)
        @blp.response(PetSchema)
        def get(self, pet_id):
            return Pet.get_by_id(pet_id)

        @blp.etag(PetEtagSchema)
        @blp.arguments(PetSchema)
        @blp.response(PetSchema)
        def put(self, new_pet, pet_id):
            pet = Pet.get_by_id(pet_id)
            # Check ETag is a manual action and schema must be provided
            blp.check_etag(pet)
            pet.update(update_data)
            return pet

        @blp.etag(PetEtagSchema)
        @blp.response(code=204)
        def delete(self, pet_id):
            pet = self._get_pet(pet_id)
            # Check ETag is a manual action, ETag schema is used
            blp.check_etag(pet)
            Pet.delete(pet_id)

ETag Computed on Arbitrary Data
-------------------------------

The ETag can also be computed from arbitrary data by calling
:meth:`Blueprint.set_etag <Blueprint.set_etag>` manually.

The example below illustrates this with no ETag schema, but it is also possible
to pass an ETag schema to :meth:`set_etag <Blueprint.set_etag>` and
:meth:`check_etag <Blueprint.check_etag>` or equivalently to
:meth:`Blueprint.etag <Blueprint.etag>`.

.. code-block:: python
    :emphasize-lines: 4,9,12,17,23,27,30,36,39,42,47

    @blp.route('/')
    class Pet(MethodView):

        @blp.etag
        @blp.response(PetSchema(many=True))
        def get(self):
            pets = Pet.get()
            # Compute ETag using arbitrary data
            blp.set_etag([pet.update_time for pet in pets])
            return pets

        @blp.etag
        @blp.arguments(PetSchema)
        @blp.response(PetSchema)
        def post(self, new_data):
            # Compute ETag using arbitrary data
            blp.set_etag(new_data['update_time'])
            return Pet.create(**new_data)

    @blp.route('/<pet_id>')
    class PetById(MethodView):

        @blp.etag
        @blp.response(PetSchema)
        def get(self, pet_id):
            # Compute ETag using arbitrary data
            blp.set_etag(new_data['update_time'])
            return Pet.get_by_id(pet_id)

        @blp.etag
        @blp.arguments(PetSchema)
        @blp.response(PetSchema)
        def put(self, update_data, pet_id):
            pet = Pet.get_by_id(pet_id)
            # Check ETag is a manual action
            blp.check_etag(pet, ['update_time'])
            pet.update(update_data)
            # Compute ETag using arbitrary data
            blp.set_etag(new_data['update_time'])
            return pet

        @blp.etag
        @blp.response(code=204)
        def delete(self, pet_id):
            pet = Pet.get_by_id(pet_id)
            # Check ETag is a manual action
            blp.check_etag(pet, ['update_time'])
            Pet.delete(pet_id)

ETag Not Checked Warning
------------------------

It is up to the developer to call
:meth:`Blueprint.check_etag <Blueprint.check_etag>` in the view function. It
can't be automatic.

If ETag is enabled and :meth:`check_etag <Blueprint.check_etag>` is not called,
a warning is logged at runtime. When in `DEBUG` or `TESTING` mode, an exception
is raised.

Include Headers Content in ETag
-------------------------------

When ETag is computed with response data, that data may contain headers. It is
up to the developer to decide whether this data should be part of the ETag.

By default, only pagination header is included in the ETag computation. This
can be changed by customizing `Blueprint.ETAG_INCLUDE_HEADERS`.
