.. _openapi:
.. module:: flask_rest_api

OpenAPI
=======

`flask-rest-api` automatically generates an OpenAPI documentation (formerly
known as Swagger) for the API. It does so by inspecting
the :class:`Schema <marshmallow.Schema>` used to deserialiaze the parameters
and deserialize the responses. A few manual steps are required to complete the
generated documentation.

The documentation can be made accessible as a JSON file, along with a nice web
interface such as ReDoc_ or `Swagger UI`_.

Specify Versions
----------------

The version of the API and the version of the OpenAPI specification can be
specified as Flask application parameters:

.. describe:: API_VERSION

   Version of the API. It is copied verbatim in the documentation. It should be
   a string, even it the version is a number.

   Default: ``'1'``

.. describe:: OPENAPI_VERSION

   Version of the OpenAPI standard used to describe the API. It should be
   provided as a string.

   The OpenAPI version must be passed either as application parameter or at
   :class:`Api <Api>` initialization in ``spec_kwargs`` parameters.

Add Documentation Information to the View Functions
---------------------------------------------------

`flask-rest-api` uses view functions docstrings to fill the `summary` and
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

Any description attribute for a view function can be passed to the docs with
the :meth:`Blueprint.doc <Blueprint.doc>` decorator. The following example
illustrates how to pass `summary` and `description` using that decorator.

.. code-block:: python

    @blp.doc(description='Return pets based on ID',
             summary='Find pets by ID')
    def get(...):
        """This method is used to find pets by ID"""
        ...

`summary` and `description` passed using the
:meth:`Blueprint.doc <Blueprint.doc>` decorator override the ones from the
docstring.

`flask-rest-api` aims at providing all useful attributes automatically, so
this decorator should not need to be used for general use cases. However, it
comes in handy if an OpenAPI feature is not supported.

Populating the root document object
-----------------------------------

Additional root document attributes can be passed either in the code, in
:class:`Api <Api>` parameter ``spec_kwargs``, or as Flask app configuration
parameters.

.. code-block:: python

    app.config['API_SPEC_OPTIONS'] = {'x-internal-id': '2'}

    api = Api(app, spec_kwargs={'host': 'example.com', 'x-internal-id': '1'})

Note that ``app.config`` overrides ``spec_kwargs``. The example above produces

.. code-block:: python

    {'host': 'example.com', 'x-internal-id': '2', ...}

.. note:: Again, flask-rest-api tries to provide as much information as
   possible, but some values can only by provided by the user.

   When using OpenAPI v2, `basePath` is automatically set from the value of the
   flask parameter `APPLICATION_ROOT`. In OpenAPI v3, `basePath` is removed,
   and the `servers` attribute can only be set by the user.

Register Definitions
--------------------

When a schema is used multiple times throughout the spec, it is better to
add it to the spec's schema components so as to reference it rather than
duplicate its content.

To register a schema, use the :meth:`Api.schema` decorator:

.. code-block:: python

    api = Api()

    @api.schema('Pet')
    class Pet(Schema):
        ...

Register Custom Fields
----------------------

Standard marshmallow :class:`Field <marshmallow.fields.Field>` classes are
documented with the correct type and format.

When using custom fields, the type and format must be passed, either explicitly
or by specifying a parent field class, using :meth:`Api.register_field`:

.. code-block:: python

    # Map to ('string', 'ObjectId') passing type and format
    api.register_field(ObjectId, 'string', 'ObjectId')

    # Map to ('string') passing type
    api.register_field(CustomString, 'string', None)

    # Map to ('integer, 'int32') passing a code marshmallow field
    api.register_field(CustomInteger, ma.fields.Integer)

Register Custom Path Parameter Converters
-----------------------------------------

Likewise, standard types used as path parameter converters in the flask routes
are correctly documented, but custom path converters must be registered.

The :meth:`Api.register_converter` allows to register a converter in the
``Api`` object to generate an accurate documentation.

.. code-block:: python

    # Register MongoDB's ObjectId converter in Flask application
    app.url_map.converters['objectid'] = ObjectIdConverter

    # Register converter in Api
    api.register_converter(ObjectIdConverter, 'string', 'ObjectID')

    @blp.route('/pets/{objectid:pet_id}')
        ...

Serve the OpenAPI Documentation
-------------------------------

Now that that the documentation is generated, it should be made available to
the clients. `flask-rest-api` can define routes to provide both the
documentation as a JSON file and a nice web interface to browse it
interactively. This feature is accessible through Flask app parameters.

.. describe:: OPENAPI_URL_PREFIX

   Defines the base path for both the JSON file and the UI. If ``None``, the
   documentation is not served and the following parameters are ignored.

   Default: ``None``

.. describe:: OPENAPI_JSON_PATH

   Path to the JSON file, relative to the base path.

   Default: ``openapi.json``

Both ReDoc_ and `Swagger UI`_ interfaces are available to present the API.

Their configuration logics are similar. If a path is set, then `flask-rest-api`
creates a route in the application to serve the interface page, using the JS
script from a user defined URL, if any, or from a CDN URL built with the version
number.

.. describe:: OPENAPI_REDOC_PATH

   If not ``None``, path to the ReDoc page, relative to the base path.

   Default: ``None``

.. describe:: OPENAPI_REDOC_URL

   URL to the ReDoc script. If ``None``, a CDN version is used.

   Default: ``None``

.. describe:: OPENAPI_REDOC_VERSION

   ReDoc version as string. Should be an existing version number, ``latest``
   (latest 1.x verison) or ``next`` (latest 2.x version).

   This is used to build the CDN URL if ``OPENAPI_REDOC_URL`` is ``None``.

   On a production instance, it is recommended to specify a fixed version
   number.

   Default: ``'latest'``

.. describe:: OPENAPI_SWAGGER_UI_PATH

   If not ``None``, path to the Swagger UI page, relative to the base path.

   Default: ``None``

.. describe:: OPENAPI_SWAGGER_UI_URL

   URL to the Swagger UI script. If ``None``, a CDN version is used.

   Default: ``None``

.. describe:: OPENAPI_SWAGGER_UI_VERSION

   Swagger UI version as string. Contrary to ReDoc, there is no default value
   pointing to the latest version, so it must be specified.

   This is used to build the CDN URL if ``OPENAPI_SWAGGER_UI_URL`` is ``None``.

   Default: ``None``

.. describe:: OPENAPI_SWAGGER_UI_SUPPORTED_SUBMIT_METHODS

   List of methods for which the '*Try it out!*' feature is enabled. Should be a
   list of lowercase HTTP methods.

   Passing an empty list disables the feature globally.

   Default: ``['get', 'put', 'post', 'delete', 'options', 'head', 'patch', 'trace']``

.. warning:: The version strings are not checked by `flask-rest-api`. They are
   used as is to build the URL pointing to the UI script. Typos won't be caught.

.. _ReDoc: https://github.com/Rebilly/ReDoc
.. _Swagger UI: https://swagger.io/tools/swagger-ui/
