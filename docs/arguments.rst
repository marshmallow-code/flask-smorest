.. _arguments:
.. currentmodule:: flask_smorest

Arguments
=========

To inject arguments into a view function, use the :meth:`Blueprint.arguments
<Blueprint.arguments>` decorator. It allows to specify a :class:`Schema
<marshmallow.Schema>` to deserialize and validate the parameters.

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

The following locations are allowed:

    - ``"json"``
    - ``"query"`` (or ``"querystring"``)
    - ``"path"``
    - ``"form"``
    - ``"headers"``
    - ``"cookies"``
    - ``"files"``

The location defaults to ``"json"``, which means `body` parameter.

Arguments Injection
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

Multiple Arguments Schemas
--------------------------

To define arguments from multiple locations, calls to ``arguments`` decorator
can be stacked:

.. code-block:: python
    :emphasize-lines: 4,5

    @blp.route('/')
    class Pets(MethodView):

        @blp.arguments(PetSchema)
        @blp.arguments(QueryArgsSchema, location="query")
        @blp.response(PetSchema, code=201)
        def post(self, pet_data, query_args):
            pet = Pet.create(**pet_data)
            # Use query args
            ...
            return pet

It is possible to define multiple arguments for the same location. However,
with marshmallow 3, schemas raise by default on unknown fields, so they should
be tweaked to define ``unknown`` meta attribute as ``EXCLUDE``.

.. code-block:: python
    :emphasize-lines: 5,12

    # With marshmallow 3, define unknown=EXCLUDE
    class QueryArgsSchema1(ma.Schema):
        class Meta:
            ordered = True
            unknown = ma.EXCLUDE
        arg1 = ma.fields.String()
        arg2 = ma.fields.Integer()

    class QueryArgsSchema2(ma.Schema):
        class Meta:
            ordered = True
            unknown = ma.EXCLUDE
        arg3 = ma.fields.String()
        arg4 = ma.fields.Integer()

    @blp.route('/')
    class Pets(MethodView):

        @blp.arguments(QueryArgsSchema1, location="query")
        @blp.arguments(QueryArgsSchema2, location="query")
        @blp.response(PetSchema, code=201)
        def get(self, query_args_1, query_args_2):
            query = {}
            query.update(query_args_1)
            query.update(query_args_2)
            return Pet.get(**query)

This also applies when using both query arguments and ``pagination`` decorator,
as the pagination feature uses query arguments for pagination parameters.

Content Type
------------

When using body arguments, a default content type is assumed depending on the
location. The location / content type mapping can be customized by modifying
``Blueprint.DEFAULT_LOCATION_CONTENT_TYPE_MAPPING``.

.. code-block:: python

    DEFAULT_LOCATION_CONTENT_TYPE_MAPPING = {
        "json": "application/json",
        "form": "application/x-www-form-urlencoded",
        "files": "multipart/form-data",

It is also possible to override those defaults in a single resource by passing
a string as ``content_type`` argument to :meth:`Blueprint.arguments
<Blueprint.arguments>`.

.. note:: The content type is only used for documentation purpose and has no
   impact on request parsing.

.. note:: Multipart requests with mixed types (file, form, etc.) are not
   supported. They can be achieved but the documentation is not correctly
   generated. ``arguments`` decorator can be called multiple times on the same
   view function but it should not be called with more that one request body
   location. This limitation is discussed in :issue:`46`.

File Upload
-----------

File uploads as `multipart/form-data` are supported for both
`OpenAPI 3 <https://swagger.io/docs/specification/describing-request-body/file-upload/>`_
and
`OpenAPI 2 <https://swagger.io/docs/specification/2-0/file-upload/>`_.

The arguments ``Schema`` should contain :class:`Upload <fields.Upload>`
fields. The files are injected in the view function as a ``dict`` of werkzeug
:class:`FileStorage <werkzeug.datastructures.FileStorage>` instances.

.. code-block:: python

    import os.path
    from werkzeug.utils import secure_filename
    from flask_smorest.fields import Upload

    class MultipartFileSchema(ma.Schema):
        file_1 = Upload()

    @blp.route('/', methods=['POST'])
    @blp.arguments(MultipartFileSchema, location='files')
    @blp.response(code=201)
    def func(files):
        base_dir = '/path/to/storage/dir/'
        file_1 = files['file_1']
        file_1.save(os.path.join(base_dir, secure_filename(file_1.filename)))
