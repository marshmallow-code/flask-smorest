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
        @blp.response(200, PetSchema(many=True))
        def get(self, args):
            return Pet.get(filters=args)

        @blp.arguments(PetSchema)
        @blp.response(201, PetSchema)
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
        @blp.response(200, PetSchema(many=True))
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

Dealing With Unknown Arguments
------------------------------

When input data contains unknown fields, a marshmallow ``Schema`` may raise a
``ValidationError`` (default), exclude those fields, or include them without
validation. This can be controlled by the ``unknown`` Meta attribute of the
``Schema``, which can be set to ``RAISE``, ``EXCLUDE`` or ``INCLUDE``.

Webargs, used internally by the ``arguments`` decorator, sets this parameter
depending on the location of the argument. ``EXCLUDE`` is used for all
locations except ``json``, ``form``, ``json_or_form``, or ``path``, where
``RAISE`` is used.

This can be customized in the ``FlaskParser`` imported from webargs. The
easiest way is to mutate ``DEFAULT_UNKNOWN_BY_LOCATION`` in the parser class:

.. code-block:: python

    import marshmallow as ma
    from webargs.flaskparser import FlaskParser

    FlaskParser.DEFAULT_UNKNOWN_BY_LOCATION["json"] = ma.EXCLUDE

It can also be achieved by subclassing the parser and set the child class in a
base :class:`Blueprint` class:

.. code-block:: python

    import marshmallow as ma
    from webargs.flaskparser import FlaskParser
    from flask_smorest import Blueprint

    MyFlaskParser(FlaskParser):
        DEFAULT_UNKNOWN_BY_LOCATION = {
            "query": ma.RAISE,
            "json": ma.RAISE,
            # ...
        }

    MyBlueprint(Blueprint):
        ARGUMENTS_PARSER = MyFlaskParser()

This latter method is recommended if several parsers are instantiated with
different ``unknown`` values, for instance to get a different behaviour in
different ``Blueprint``s.

Setting `None` as `DEFAULT_UNKNOWN_BY_LOCATION` instead of a location/value
mapping disables the feature to fall back to the `Schema`'s ``unknown`` value
and marshmallow default (``RAISE``).

.. note:: The pagination feature in flask-smorest uses its own ``FlaskParser``
   instance to parse pagination parameters from query arguments. It is affected
   by mutations of ``FlaskParser.DEFAULT_UNKNOWN_BY_LOCATION`` setting a value
   other than ``EXCLUDE`` for ``query``.

.. note:: More default about customizing ``unknown`` can be found in `webargs
   documentation
   <https://webargs.readthedocs.io/en/latest/advanced.html#setting-unknown>`_.

.. note:: The unknown value passed by webargs only applies to first level
   fields, not to nested fields. To set ``EXCLUDE`` for ``json`` locations
   using ``Schema``s with ``Nested`` fields, one must set ``EXCLUDE`` in the
   parser but also set ``unkown=EXCLUDE`` as Meta attribute in nested schemas.
   In practice, this is easily achieved using a base schema class. This should
   be improved in the future, as discussed in `webargs issue #580
   <https://github.com/marshmallow-code/webargs/issues/580>`_.

Multiple Arguments Schemas
--------------------------

Calls to ``arguments`` decorator can be stacked, for instance to define
arguments from multiple locations:

.. code-block:: python
    :emphasize-lines: 4,5

    @blp.route('/')
    class Pets(MethodView):

        @blp.arguments(PetSchema)
        @blp.arguments(QueryArgsSchema, location="query")
        @blp.response(201, PetSchema)
        def post(self, pet_data, query_args):
            pet = Pet.create(**pet_data)
            # Use query args
            ...
            return pet

It can also be done to define multiple arguments for the same location. Of
course, this only makes sense for locations where ``unknown`` is set to
``EXCLUDE``.

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
    @blp.response(201)
    def func(files):
        base_dir = '/path/to/storage/dir/'
        file_1 = files['file_1']
        file_1.save(os.path.join(base_dir, secure_filename(file_1.filename)))
