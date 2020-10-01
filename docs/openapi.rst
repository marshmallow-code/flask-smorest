.. _openapi:
.. currentmodule:: flask_smorest

OpenAPI
=======

`flask-smorest` automatically generates an OpenAPI documentation (formerly
known as Swagger) for the API.

That documentation can be made accessible as a JSON file, along with a nice web
interface such as `ReDoc`_ or `Swagger UI`_.

API parameters
--------------

The following API and OpenAPI parameters must be passed either as application
configuration parameter or at initialization. If both are used, the application
configuration parameter takes precedence.

.. describe:: API_TITLE

   Title of the API. Human friendly string describing the API.

   API title must be passed either as application parameter or as `title`
   at :class:`Api <Api>` initialization in ``spec_kwargs`` parameters.

.. describe:: API_VERSION

   Version of the API. It is copied verbatim in the documentation. It should be
   a string, even if the version is a number.

   API version must be passed either as application parameter or as `version`
   at :class:`Api <Api>` initialization in ``spec_kwargs`` parameters.

.. describe:: OPENAPI_VERSION

   Version of the OpenAPI standard used to describe the API. It should be
   provided as a string.

   OpenAPI version must be passed either as application parameter or as
   `openapi_version` at :class:`Api <Api>` initialization in ``spec_kwargs``
   parameters.



Add Documentation Information to Resources
------------------------------------------

Add Summary and Description
^^^^^^^^^^^^^^^^^^^^^^^^^^^

`flask-smorest` uses view functions docstrings to fill the `summary` and
`description` attributes of an `operation object`.

.. code-block:: python

    def get(...):
        """Find pets by ID

        Return pets based on ID.
        ---
        Internal comment not meant to be exposed.
        """

The part of the docstring following the ``'---'`` line is ignored.

The part before the ``'---'`` line is used as `summary` and `description`. The
first lines are used as `summary`. If an empty line is met, all following lines
are used as `description`.

The example above produces the following documentation attributes:

.. code-block:: python

    {
        'get': {
            'summary': 'Find pets by ID',
            'description': 'Return pets based on ID',
        }
    }

The delimiter line is the line starting with the delimiter string defined in
``Blueprint.DOCSTRING_INFO_DELIMITER``. This string defaults to ``"---"`` and
can be customized in a subclass. ``None`` means "no delimiter": the whole
docstring is included in the docs.

Document Operations Parameters and Responses
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Schemas passed in :meth:`Blueprint.arguments <Blueprint.arguments>` to
deserialize arguments are parsed automatically to generate corresponding
documentation. Additional ``example`` and ``examples`` parameters can be used
to provide examples (those are only valid for OpenAPI v3).

Likewise, schemas passed in :meth:`Blueprint.response <Blueprint.response>` to
serialize responses are parsed automatically to generate corresponding
documentation. Additional ``example`` and ``examples`` parameters can be used
to provide examples (``examples`` is only valid for OpenAPI v3). Additional
``headers`` parameters can be used to document response headers.

Document Path Parameters
^^^^^^^^^^^^^^^^^^^^^^^^

Path parameters are automatically documented. The type in the documentation
is inferred from the path parameter converter used in the URL rule. Custom path
parameters should be registered for their type to be correctly determined (see
below).

The :meth:`Blueprint.route <Blueprint.route>` method takes a ``parameters``
argument to pass documentation for parameters that are shared by all operations
of a path. It can be used to pass extra documentation, such as examples, for
path parameters.

Pass Extra Documentation Information
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

`flask-smorest` tries to document the API as automatically as possible and to
provide explicit means to pass extra-information that can't be inferred from
the code, such as descriptions, examples, etc.

The :meth:`Blueprint.doc <Blueprint.doc>` decorator provides a means to pass
extra documentation information. It comes in handy if an OpenAPI feature is not
supported, but it suffers from a few limitations, and it should be considered
a last resort solution until `flask-smorest` is improved to fit the need.

Known issues and alternatives are discussed in issue :issue:`71`.

Populate the Root Document Object
---------------------------------

Additional root document attributes can be passed either in the code, in
:class:`Api <Api>` parameter ``spec_kwargs``, or as Flask app configuration
parameters.

.. code-block:: python

    app.config['API_SPEC_OPTIONS'] = {'x-internal-id': '2'}

    api = Api(app, spec_kwargs={'host': 'example.com', 'x-internal-id': '1'})

Note that ``app.config`` overrides ``spec_kwargs``. The example above produces

.. code-block:: python

    {'host': 'example.com', 'x-internal-id': '2', ...}

.. note:: Again, flask-smorest tries to provide as much information as
   possible, but some values can only by provided by the user.

   When using OpenAPI v2, `basePath` is automatically set from the value of the
   flask parameter `APPLICATION_ROOT`. In OpenAPI v3, `basePath` is removed,
   and the `servers` attribute can only be set by the user.

Document Top-level Components
-----------------------------

Documentation components can be passed by accessing the internal apispec
:class:`Components <apispec.core.Components>` object.

.. code-block:: python

    api = Api(app)
    api.spec.components.parameter(
      'Pet name',
      'query',
      {'description': 'Item ID', 'required': True}
   )

Register Custom Fields
----------------------

Standard marshmallow :class:`Field <marshmallow.fields.Field>` classes are
documented with the correct type and format.

When using custom fields, the type and format must be passed, either explicitly
or by specifying a parent field class, using :meth:`Api.register_field`:

.. code-block:: python

    # Map to ('string', 'ObjectId') passing type and format
    api.register_field(ObjectId, 'string', 'ObjectId')

    # Map to ('string', ) passing type
    api.register_field(CustomString, 'string', None)

    # Map to ('string, 'date-time') passing a marshmallow Field
    api.register_field(CustomDateTime, ma.fields.DateTime)

Register Custom Path Parameter Converters
-----------------------------------------

Likewise, standard types used as path parameter converters in the flask routes
are correctly documented, but custom path converters must be registered.

The :meth:`Api.register_converter` allows to register a converter in the
``Api`` object to generate an accurate documentation.

.. code-block:: python

   # Register MongoDB's ObjectId converter in Flask application
   app.url_map.converters['objectid'] = ObjectIdConverter

   # Define custom converter to schema function
   def objectidconverter2paramschema(converter):
       return {'type': 'string', 'format': 'ObjectID'}

   # Register converter in Api
   api.register_converter(
       ObjectIdConverter,
       objectidconverter2paramschema
   )

   @blp.route('/pets/{objectid:pet_id}')
       ...


Enforce Order in OpenAPI Specification File
-------------------------------------------

When a :class:`Blueprint <Blueprint>` is registered, a `tag` is created with
the ``Blueprint`` name. The display order in the interface is the ``Blueprint``
registration order. And the display order inside a `tag` is the order in which
the resources are defined in the ``Blueprint``.

In the OpenAPI specification file, the fields of a ``Schema`` are documented as
schema `properties`. Although objects are not ordered in JSON, OpenAPI
graphical interfaces tend to respect the order in which the `properties` are
defined in the ``properties`` object in the specification file.

When using an ordererd ``Schema``, the fields definition order is preserved
when generating the specification file and the `properties` are displayed in
that order.

This is typically done in a base class:

.. code-block:: python
    :emphasize-lines: 2,3

    class MyBaseSchema(ma.Schema):
        class Meta:
            ordered = True

    class User(MyBaseSchema):
        name = ma.fields.String()
        surname = ma.fields.String()

Passing ``ordered`` Meta attribute is not necessary when using a Python version
for which dictionaries are always ordered (>= 3.7 or CPython 3.6).

Serve the OpenAPI Documentation
-------------------------------

Now that that the documentation is generated, it should be made available to
the clients. `flask-smorest` can define routes to provide both the
documentation as a JSON file and a nice web interface to browse it
interactively. This feature is accessible through Flask app parameters.

.. describe:: OPENAPI_URL_PREFIX

   Defines the base path for both the JSON file and the UI. If ``None``, the
   documentation is not served and the following parameters are ignored.

   Default: ``None``

.. describe:: OPENAPI_JSON_PATH

   Path to the JSON file, relative to the base path.

   Default: ``openapi.json``

Both `ReDoc`_ and `Swagger UI`_ interfaces are available to present the API.

Their configuration logics are similar. If an application path and a script URL
are set, then `flask-smorest` adds a route at that path to serve the interface
page using the JS script from the script URL.

.. describe:: OPENAPI_REDOC_PATH

   Path to the ReDoc page, relative to the base path.

   Default: ``None``

.. describe:: OPENAPI_REDOC_URL

   URL to the ReDoc script.

   Examples:
       * https://rebilly.github.io/ReDoc/releases/v1.x.x/redoc.min.js
       * https://rebilly.github.io/ReDoc/releases/v1.22.3/redoc.min.js
       * https://rebilly.github.io/ReDoc/releases/latest/redoc.min.js
       * https://cdn.jsdelivr.net/npm/redoc@2.0.0-alpha.17/bundles/redoc.standalone.js
       * https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js

   Default: ``None``

.. describe:: OPENAPI_SWAGGER_UI_PATH

   Path to the Swagger UI page, relative to the base path.

   Default: ``None``

.. describe:: OPENAPI_SWAGGER_UI_URL

   URL to the Swagger UI script. Versions prior to 3.x are not supported.

   Examples:
      * https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/3.24.2/
      * https://cdn.jsdelivr.net/npm/swagger-ui-dist@3.25.0/
      * https://cdn.jsdelivr.net/npm/swagger-ui-dist@3.25.x/
      * https://cdn.jsdelivr.net/npm/swagger-ui-dist/

   Default: ``None``

.. describe:: OPENAPI_SWAGGER_UI_CONFIG

   Dictionary representing Swagger UI configuration options.  See `Swagger UI Configuration`_ for available options.
   All JSON serializable options are supported.

   Examples:
      * ``{'deepLinking': True, 'supportedSubmitMethods': ['get', 'post']}``

   Default: ``{}``

Here's an example application configuration using both ReDoc and Swagger UI:

.. code-block:: python

   class Config:
       OPENAPI_VERSION = "3.0.2"
       OPENAPI_JSON_PATH = "api-spec.json"
       OPENAPI_URL_PREFIX = "/"
       OPENAPI_REDOC_PATH = "/redoc"
       OPENAPI_REDOC_URL = "https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js"
       OPENAPI_SWAGGER_UI_PATH = "/swagger-ui"
       OPENAPI_SWAGGER_UI_URL = "https://cdn.jsdelivr.net/npm/swagger-ui-dist/"

.. _ReDoc: https://github.com/Rebilly/ReDoc
.. _Swagger UI: https://swagger.io/tools/swagger-ui/
.. _Swagger UI Configuration: https://swagger.io/docs/open-source-tools/swagger-ui/usage/configuration/

Write OpenAPI Documentation File
--------------------------------

flask-smorest provides flask commands to print the OpenAPI file to the standard
output,

.. code-block:: none

    flask openapi print

or write it to a file.

.. code-block:: none

    flask openapi write openapi.json

A typical use case is to write the OpenAPI documentation to a file in a
deployment script to host it on a separate server rather than serving it from
the application.
