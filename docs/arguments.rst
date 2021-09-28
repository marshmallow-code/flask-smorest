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

    @blp.route("/")
    class Pets(MethodView):
        @blp.arguments(PetQueryArgsSchema, location="query")
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

    @blp.route("/")
    class Pets(MethodView):
        @blp.arguments(PetQueryArgsSchema, location="query", as_kwargs=True)
        @blp.response(200, PetSchema(many=True))
        def get(self, **kwargs):
            return Pet.get(filters=kwargs)

This decorator can be called several times on a resource function, for instance
to accept both `body` and `query` parameters. The order of the decorator calls
matters as it determines the order in which the parameters are passed to the
view function.

.. code-block:: python
    :emphasize-lines: 4,5,6

    @blp.route("/")
    class Pets(MethodView):
        @blp.arguments(PetSchema)
        @blp.arguments(QueryArgsSchema, location="query")
        def post(pet_data, query_args):
            return Pet.create(pet_data, **query_args)

Dealing With Unknown Arguments
------------------------------

When input data contains unknown fields, a marshmallow ``Schema`` may raise a
``ValidationError`` (default), exclude those fields, or include them without
validation. This can be controlled by the ``unknown`` Meta attribute of the
``Schema``, which can be set to ``RAISE``, ``EXCLUDE`` or ``INCLUDE``.

Marshmallow also allows to pass an ``unknown`` argument to change this on the
fly on each load. This parameter, if not ``None``, overrides the Meta
attribute. But it does not propagate to nested ``Schema`` s.

``json``, ``form`` or ``json_or_form`` locations may contain nested schemas, so
the only way to change behaviour about ``unknown`` (for instance to set it to
``EXCLUDE``), is to set it in a Meta attribute. This can be done conveniently
in a base ``Schema`` class.

For locations that typically don't use nested ``Schema`` s (``query_string``,
``headers``, ``cookies`` and ``files``), ``unknown=EXCLUDE`` is passed, as it
is considered a more sensible default.

The ``unknown`` argument passed to the ``Schema`` for each location can be
customized in the ``FlaskParser`` imported from webargs.

The easiest way is to mutate ``DEFAULT_UNKNOWN_BY_LOCATION`` in the parser
class:

.. code-block:: python

    import marshmallow as ma
    from webargs.flaskparser import FlaskParser

    # Don't do that when using the pagination feature. See below.
    FlaskParser.DEFAULT_UNKNOWN_BY_LOCATION["query"] = ma.RAISE

It can also be achieved by subclassing the parser and setting
``ARGUMENTS_PARSER`` in a base :class:`Blueprint` class:

.. code-block:: python

    import marshmallow as ma
    from webargs.flaskparser import FlaskParser
    from flask_smorest import Blueprint


    class MyFlaskParser(FlaskParser):
        DEFAULT_UNKNOWN_BY_LOCATION = {
            "query": ma.RAISE,
            # ...
        }


    class MyBlueprint(Blueprint):
        ARGUMENTS_PARSER = MyFlaskParser()

This latter method is recommended if several parsers are instantiated with
different ``unknown`` values, for instance to get different behaviours in
different ``Blueprint`` s.

For the reason stated above, setting a value there for locations containing
nested ``Schema`` s is not recommended because that value would only apply to
the first level and would not propagate to nested ``Schema`` s.

Setting ``None`` for a location disables the feature for that location: no
``unknown`` argument is passed and marshmallow uses the ``Schema``'s
``unknown`` Meta attribute or falls back to marshmallow default (``RAISE``).

Setting ``None`` as ``DEFAULT_UNKNOWN_BY_LOCATION`` instead of a location/value
mapping disables the feature for all locations.

.. note:: The pagination feature in flask-smorest uses its own ``FlaskParser``
   instance to parse pagination parameters from query arguments. It is affected
   by mutations of ``FlaskParser.DEFAULT_UNKNOWN_BY_LOCATION`` setting a value
   other than ``EXCLUDE`` for ``query``.

.. note:: More info about customizing ``unknown`` can be found in `webargs
   documentation
   <https://webargs.readthedocs.io/en/latest/advanced.html#setting-unknown>`_.

Multiple Arguments Schemas
--------------------------

Calls to ``arguments`` decorator can be stacked, for instance to define
arguments from multiple locations:

.. code-block:: python
    :emphasize-lines: 4,5

    @blp.route("/")
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
    }

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


    @blp.route("/", methods=["POST"])
    @blp.arguments(MultipartFileSchema, location="files")
    @blp.response(201)
    def func(files):
        base_dir = "/path/to/storage/dir/"
        file_1 = files["file_1"]
        file_1.save(os.path.join(base_dir, secure_filename(file_1.filename)))
