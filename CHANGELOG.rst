Changelog
---------

0.26.0 (2020-12-17)
+++++++++++++++++++

Features:

- *Backwards-incompatible*: Use warnings.warn rather than log warnings in
  application log (:pr:`194`).

Other changes:

- *Backwards-incompatible*: Support webargs 6. Drop support for webargs 7.
  The main change is about management of unknown fields in requests. Users
  should refer to webargs documentation, sections
  `Upgrading to 7.0 <https://webargs.readthedocs.io/en/latest/upgrading.html#upgrading-to-7-0>`_
  and
  `Setting unknown <https://webargs.readthedocs.io/en/latest/advanced.html#advanced-setting-unknown>`_.
  (:pr:`203`)

0.25.1 (2020-12-17)
+++++++++++++++++++

Features:

- Official Python 3.9 support (:pr:`195`).

Other changes:

- Bound dependencies versions in setup.py (:pr:`202`).

0.25.0 (2020-10-02)
+++++++++++++++++++

Features:

- *Backwards-incompatible*: Rework Werkzeug converters documentation to make
  it more extensible and document converter parameters (:pr:`182`).
- *Backwards-incompatible*: Don't document ``int`` format as ``"int32"`` and
  ``float`` format as ``"float"``, as those are platform-dependent (:pr:`188`).
- Document Werkzeug's ``AnyConverter`` (:pr:`191`).

Other changes:

- *Backwards-incompatible*: Drop support for marshmallow 2.
- *Backwards-incompatible*: Drop support for apispec 3.

0.24.1 (2020-08-10)
+++++++++++++++++++

Bug fixes:

- Fix bug introduced in 0.24.0 preventing setting a status code or header when
  returning a ``Response`` object. (:pr:`178`).
  Thanks :user:`@marksantcroos` for reporting.

0.24.0 (2020-07-17)
+++++++++++++++++++

Features:

- *Backwards-incompatible*: Add ``OPENAPI_SWAGGER_UI_CONFIG`` to allow passing
  a dict of Swagger UI configuration parameters. Remove
  ``OPENAPI_SWAGGER_UI_SUPPORTED_SUBMIT_METHODS``: the same can be achieved by
  passing ``supportedSubmitMethods`` in ``OPENAPI_SWAGGER_UI_CONFIG``. Remove
  ``layout`` and ``deepLinking`` default overrides. Those can be passed in
  ``OPENAPI_SWAGGER_UI_CONFIG`` as well. (:pr:`171`).
  Thanks :user:`joshua-harrison-2011` for the pull-request.

0.23.0 (2020-07-08)
+++++++++++++++++++

Features:

- *Backwards-incompatible*: Make API title and version mandatory parameters.
  Before this change, the version would default to ``"1"`` and the title would
  be ``app.name``. Those two parameters can be passed at init or as application
  configuration parameters ``TITLE`` and ``API_VERSION``. Also rename
  ``OpenAPIVersionNotSpecified`` as ``MissingAPIParameterError``. (:pr:`169`).
  Thanks :user:`playpauseandstop` for the help on this.

- *Backwards-incompatible*: Rework pagination documentation to allow more
  customization. This change will break code overriding
  ``PAGINATION_HEADER_DOC``, ``_make_pagination_header`` or
  ``_prepare_pagination_doc`` (:pr:`153`).

0.22.0 (2020-06-19)
+++++++++++++++++++

Features:

- Add ``flask openapi print`` and ``flask openapi write`` commands (:pr:`154`).

Other changes:

- *Backwards-incompatible*: Drop support for Python 3.5.

0.21.2 (2020-06-09)
+++++++++++++++++++

Bug fixes:

- Use HTTPStatus ``phrase``, not ``name``, in response description (:pr:`158`).

0.21.1 (2020-05-29)
+++++++++++++++++++

Bug fixes:

- Deep-copy the documentation information for each method of a resource. This
  fixes a crash when a view function serves several methods, due to apispec
  mutating doc info dict. (:pr:`147`)
  Thanks :user:`DrChrisLevy` for reporting.

0.21.0 (2020-03-24)
+++++++++++++++++++

Features:

- Support webargs 6.0.0 (:pr:`132`).

Other changes:

- *Backwards-incompatible*: Drop support for webargs < 6.0.0. Marshmallow 3
  code with stacked ``@arguments`` using the same location must ensure the
  arguments schema have ``Meta.unknown=EXCLUDE``. This also applies to
  ``@arguments`` with ``query`` location stacked with ``@paginate``. Also,
  validation error messages are namespaced under the location. See the
  upgrading guide in webargs documentation for more details and a comprehensive
  list of changes. (:pr:`132`)

0.20.0 (2020-03-20)
+++++++++++++++++++

Bug fixes:

- *Backwards-incompatible*: Use ``HTTPStatus`` ``name`` rather than ``phrase``
  to name error components. This fixes an issue due to ``phrase`` containing
  spaces not being URL-encoded. Also change ``DefaultError`` into
  ``DEFAULT_ERROR`` for consistency. This change will break code referencing
  one of those errors. (:issue:`136`).
  Thanks :user:`michelle-avery` for reporting.

Other changes:

- *Backwards-incompatible*: Remove ``OPENAPI_REDOC_VERSION`` and
  ``OPENAPI_SWAGGER_UI_VERSION``. Remove hardcoded CDNs. Users should modify
  their code to use ``OPENAPI_REDOC_URL`` and ``OPENAPI_SWAGGER_UI_URL``
  instead. The docs provide examples of CDN URLs. (:issue:`134`).

0.19.2 (2020-02-20)
+++++++++++++++++++

Bug fixes:

- Fix ``utils.deepupdate`` for the case where the original value is a string or
  integer and the updated value is a ``dict`` (:issue:`129`).
  Thanks :user:`maj-skymedia` for reporting.

0.19.1 (2020-02-20)
+++++++++++++++++++

Bug fixes:

- Fix a regression introduced in 0.19.0. With marshmallow 2, the response would
  contain two ``'X-Pagination'`` headers: the correct header and an empty one.
  (:pr:`128`)

0.19.0 (2020-02-19)
+++++++++++++++++++

Features:

- *Backwards-incompatible*: Refactor automatic documentation generation. At
  import time, each decorator stores information under its own namespace in
  the view function's ``_apidoc`` attribute. Then at app init time, the
  information is used to generate the docs. This allows access to init time
  parameters, such as OpenAPI version or application parameters like feature
  toggle flags, when generating the doc. Custom decorators storing doc in
  ``_apidoc`` must adapt by storing doc under their own name (e.g.:
  ``_apidoc['custom']``), creating a doc preparation callback (e.g.:
  ``_prepare_custom_doc`` and appending this callback to
  ``Blueprint._prepare_doc_cbks``. (:pr:`123`).

- Define all possible HTTP responses as response components and automatically
  document "error" responses: ``"Default Error"`` when ``@response`` is used,
  response returned by ``@arguments`` on client input error, and responses for
  304, 412 and 428 when ``@etag`` is used. Also document pagination header.
  (:pr:`125`).

- Document error response in ``@paginate`` decorator (:pr:`126`).

Bug fixes:

- *Backwards-incompatible*: Ensure pagination arguments are in query string.
  ``'page'`` and ``'page_size'`` arguments passed in any other location are
  ignored by ``@paginate`` decorator. (:pr:`127`)

0.18.5 (2020-01-30)
+++++++++++++++++++

Other changes:

- Restrict webargs to <6.0.0 in setup.py due to breaking changes introduced in
  webargs 6 (:issue:`117`).

0.18.4 (2020-01-07)
+++++++++++++++++++

Features:

- ``check_etag`` logs a warning if method is not PUT, PATCH or DELETE
  (:pr:`116`).

Bug fixes:

- Only return 304 on GET and HEAD (:pr:`115`).

0.18.3 (2019-12-20)
+++++++++++++++++++

Features:

- Add default description to responses (:pr:`113`).
  Thanks :user:`nonnib` for the pull-request.

0.18.2 (2019-10-21)
+++++++++++++++++++

Features:

- Official Python 3.8 support (:pr:`108`).

0.18.1 (2019-10-07)
+++++++++++++++++++

Bug fixes:

- Fix passing ``spec_kwargs`` in ``Api.__init__`` and ``app`` in
  ``Api.init_app`` (:issue:`103`).

0.18.0 (2019-09-22)
+++++++++++++++++++

Rename to `flask-smorest` (:issue:`42`).

0.17.0 (2019-09-19)
+++++++++++++++++++

Features:

- *Backwards-incompatible*: Only return status code and short name in error
  handler (:pr:`84`).
- *Backwards-incompatible*: Remove logging from error handler. Logging can be
  achieved in application code by overriding ``handle_http_exception``.
  Remove ``_prepare_error_response_content``. Response payload is computed in
  ``handle_http_exception``. (:pr:`85`)
- *Backwards-incompatible*: Remove ``InvalidLocationError``. The mapping from
  webargs locations to OAS locations is done in apispec and no exception is
  raised if an invalid location is passed. (:pr:`81`)
- Add ``content_type`` argument to ``Blueprint.arguments`` and provide
  reasonable default content type for ``form`` and ``files`` (:pr:`83`).
- Add ``description`` parameter to ``Blueprint.arguments`` to pass description
  for ``requestBody`` (:pr:`93`).
- Allow customization of docstring delimiter string (:issue:`49`).
- Support file uploads as `multipart/form-data` (:pr:`97`).

Bug fixes:

- Fix documentation of ``form`` and ``files`` arguments: use ``requestBody``
  in OAS3, document content type (:pr:`83`).

Other changes:

- *Backwards-incompatible*: Don't republish ``NestedQueryArgsParser`` anymore.
  This belongs to user code and can be copied from webargs doc (:pr:`94`).
- *Backwards-incompatible*: Bump minimum apispec version to 3.0.0.

0.16.1 (2019-07-15)
+++++++++++++++++++

Bug fixes:

- Fix detection of unhandled exceptions in error handler for Flask=>1.1.0
  (:pr:`82`).

Other changes:

- Bump minimum Flask version to 1.1.0. From this version on, uncaught
  exceptions are passed to the error handler as ``InternalServerError`` with
  the exception attached as ``original_exception`` attribute. (:pr:`82`)

0.16.0 (2019-06-20)
+++++++++++++++++++

Features:

- Add ``parameters`` argument to ``Blueprint.route`` to pass documentation for
  parameters that are shared by all operations of a path (:pr:`78`).

Other changes:

- *Backwards-incompatible*: Bump minimum apispec version to 2.0.0.
- *Backwards-incompatible*: Path parameters documentation passed in
  ``Blueprint.doc`` is no longer merged with automatic documentation. It should
  be passed in ``Blueprint.route`` instead.
- *Backwards-incompatible*: Remove ``Api.schema`` and ``Api.definition``.
  Those methods are useless since ``Schema`` components are automatically
  registered by apispec. Manual component registration is still possible using
  the internal apispec ``Components`` object. (:pr:`75`)

0.15.1 (2019-06-18)
+++++++++++++++++++

Bug fixes:

- marshmallow 3.0.0rc7 compatibility (:pr:`77`).

0.15.0 (2019-05-09)
+++++++++++++++++++

Features:

- Add parameters to pass examples and headers in ``Blueprint.response``
  decorator (:pr:`63`).
- Add parameters to pass examples for ``requestBody`` in OpenAPI v3 in
  ``Blueprint.arguments`` decorator (:pr:`68`).
- Support status codes expressed as ``HTTPStatus`` in ``Blueprint.response``
  decorator (:issue:`60`).
  Thanks :user:`Regzand` for reporting.

Other changes:

- Bump minimum apispec version to 1.3.2.
- Bump minimum werkzeug version to 0.15. With 0.14.x versions, `412` responses
  are returned with no content.
- *Backwards-incompatible*: When using ``Blueprint.doc`` decorator to provide
  additional documentation to the response described in the
  ``Blueprint.response`` decorator, the user must use the same format (``str``,
  ``int`` or ``HTTPStatus``) to express the status code in both decorators.
  This is a side-effect of (:issue:`60`). Now that headers and examples can
  be described in ``Blueprint.response``, this should not be a common use case.

0.14.1 (2019-04-18)
+++++++++++++++++++

Features:

- Official Python 3.7 support (:pr:`45`).
- Rename ``Api.definition`` as ``Api.schema``. Keep ``Api.definition`` as an
  alias to ``Api.schema`` for backward compatibility (:pr:`53`).

Bug fixes:

- Fix passing route with path parameter default value (:pr:`58`).
  Thanks :user:`zedrdave` for reporting.
- When no descrition is provided to ``Blueprint.response``, don't add an empty
  string as description in the docs.
- Fix returning a ``tuple`` subclass from a view function. Only raw ``tuple``
  instances are considered as Flask's (return value, status, headers).
  ``tuple`` subclasses are treated as ``list`` and can be paginated/dumped.
  Raw ``tuple`` return values should be cast to another type (e.g. ``list``)
  to be distinguished from (return value, status, headers) tuple. (:issue:`52`)
  Thanks :user:`asyncee` for reporting.

0.14.0 (2019-03-08)
+++++++++++++++++++

Features:

- Allow view functions decorated with ``response`` to return a ``Response``
  object or a tuple with status and/or headers (:pr:`40`).
- Allow view functions decorated with ``paginate`` to return a tuple with
  status and/or headers (:pr:`40`). The pagination header is now passed
  in the response tuple. Users relying on undocumented
  ``get_context()['headers']`` as a workaround to pass headers must update
  their code to pass headers in the response tuple as well.

Bug fixes:

- Fix ETag computation when headers contain a duplicate key.

0.13.1 (2019-02-13)
+++++++++++++++++++

Features:

- Register Werkzeug's ``UUIDConverter`` in ``Api`` so that ``uuid`` path
  parameters are correctly documented.

0.13.0 (2019-02-12)
+++++++++++++++++++

Features:

- Add ``flask_plugin`` and ``marshmallow_plugin`` spec kwargs to allow
  overriding base plugins.
- *Backwards-incompatible*: Rename ``plugins`` spec kwarg into
  ``extra_plugins``.
- *Backwards-incompatible*: Don't default to OpenAPI version 2.0. The version
  must now be specified, either as ``OPENAPI_VERSION`` app parameter or as
  ``openapi_version`` spec kwarg.
- Support apispec 1.0.0.

Other changes:

- *Backwards-incompatible*: Drop support for apispec 0.x.

0.12.0 (2018-12-02)
+++++++++++++++++++

Features:

- *Backwards-incompatible*: ``Api.register_converter`` doesn't register
  converter in Flask app anymore. It should be registered manually using
  ``app.url_map.converters['converter_name'] = Converter``.
- ``Api.definition``, ``Api.register_field`` and ``Api.register_converter`` can
  be called before app initialization. The information is buffered and passed
  to the internal ``APISpec`` object when it is created, in ``Api.init_app``.

0.11.2 (2018-11-28)
+++++++++++++++++++

Bug fixes:

- Fix typo in ``ErrorHandlerMixin._prepare_error_response_content``.

0.11.1 (2018-11-20)
+++++++++++++++++++

Features:

- The ``HTTP_METHODS`` list that defines the order of the methods in the spec
  is now a class attribute of ``Blueprint``. It can be overridden to enforce
  another order.

Bug fixes:

- Import ``Mapping`` from ``collections.abc`` rather than ``collections``. The
  latter is deprecated in Python 3.7 and will be removed in 3.8.
- Merge manual doc added with ``Blueprint.doc`` with automatic documentation
  after auto doc is prepared (i.e. adapted to OpenAPI version) (:issue:`19`).
  Thanks :user:`fbergroth` for reporting.
- Merge automatic path parameter documentation with existing manual doc rather
  than append as duplicate parameter (:issue:`23`).
  Thanks :user:`congenica-andrew` for reporting.
- Fix path parameter documentation structure when using OpenAPI v3.
- Document http status codes as strings, not integers.
- Fix use of Swagger UI config parameter ``OPENAPI_SWAGGER_UI_URL``.


Other changes:

- 100% test coverage !


0.11.0 (2018-11-09)
+++++++++++++++++++

Features:

- *Backwards-incompatible*: Rework of the ETag feature. It is now accesible
  using dedicated ``Blueprint.etag`` decorator. ``check_etag`` and ``set_etag``
  are methods of ``Blueprint`` and ``etag.INCLUDE_HEADERS`` is replaced with
  ``Blueprint.ETAG_INCLUDE_HEADERS``. It is enabled by default (only on views
  decorated with ``Blueprint.etag``) and disabled with ``ETAG_DISABLED``
  application configuration parameter. ``is_etag_enabled`` is now private.
  (:pr:`21`)
- *Backwards-incompatible*: The ``response`` decorator returns a ``Response``
  object rather than a (``Response`` object, status code) tuple. The status
  code is set in the ``Response`` object.
- Support apispec 1.0.0b5.

0.10.0 (2018-10-24)
+++++++++++++++++++

Features:

- *Backwards-incompatible*: Don't prefix all routes in the spec with
  ``APPLICATION_ROOT``. If using OpenAPI v2, set ``APPLICATION_ROOT`` as
  ``basePath``. If using OpenAPI v3, the user should specify ``servers``
  manually.
- *Backwards-incompatible*: In testing and debug modes, ``verify_check_etag``
  not only logs a warning but also raises ``CheckEtagNotCalledError`` if
  ``check_etag`` is not called in a resource that needs it.

0.9.2 (2018-10-16)
++++++++++++++++++

Features:

- ``Api.register_blueprint`` passes ``**options`` keyword parameters to
  ``app.register_blueprint`` to override ``Blueprint`` defaults. Thanks
  :user:`dryobates` for the suggestion.

0.9.1 (2018-10-11)
++++++++++++++++++

Features:

- Support apispec 1.0.0b3.

Bug fixes:

- Fix crash when serving documentation at root of application. Thanks
  :user:`fbergroth` for the suggestion.

0.9.0 (2018-10-01)
++++++++++++++++++

Features:

- *Backwards-incompatible*: When pagination parameters are out of range, the
  API does not return a `404` error anymore. It returns a `200` code with an
  empty list and pagination metadata (:pr:`10`).
- *Backwards-incompatible*: Remove dependency on python-dateutil. This is an
  optional marshmallow dependency. Whether it is needed to deserialize date,
  time, or datetime strings depends on the application.
- Rework internal features by using mixin classes. This makes the code cleaner
  and adds customization possibilities (:issue:`9`).
- *Backwards-incompatible*: ``DEFAULT_PAGINATION_PARAMETERS`` is a class
  attribute of ``Blueprint``.
- *Backwards-incompatible*: When no ``Page`` class is passed to ``pagination``,
  (i.e. when doing pagination in view function), the pagination parameters are
  passed as a ``PaginationParameters`` object. The item count must be passed by
  setting it as ``item_count`` attribute of the ``PaginationParameters``
  object. The ``set_item_count`` function is removed.
- The pagination header name can be configured by overriding
  ``PAGINATION_HEADER_FIELD_NAME`` class attribute of ``Blueprint``. If set to
  ``None``, no pagination header is added to the response.
- *Backwards-incompatible*: The ``paginate`` decorator doesn't use
  ``NestedQueryFlaskParser`` by default. It is renamed as
  ``NestedQueryArgsParser`` and it can be used by overriding
  ``Blueprint.ARGUMENTS_PARSER``.
- Default error handler is registered for generic ``HTTPException``. Other
  extensions may register other handlers for specific exceptions or codes
  (:pr:`12`).

Other changes:

- *Backwards-incompatible*: Drop Flask 0.x support. Flask>=1.0 is now required.

0.8.1 (2018-09-24)
++++++++++++++++++

Features:

- Add `page` (page number) to pagination metadata.
- Set `produces` and `consumes` root document attributes when using OpenAPI v2.

Bug fixes:

- Document body parameter correctly when using OpenAPI v3.

0.8.0 (2018-09-20)
++++++++++++++++++

Features:

- Add ``API_SPEC_OPTIONS`` app config parameter. Thanks :user:`xalioth` for the
  suggestion.
- *Backwards-incompatible*: ``Api`` accepts a ``spec_kargs`` parameter, passed
  as kwargs to the internal ``APISpec`` instance. ``spec_plugins`` is removed,
  plugins shall be passed as ``spec_kwargs={'plugins': [...]}``.
- *Backwards-incompatible*: Get `summary` and `description` from docstrings
  (:pr:`5`).
- Add support for marshmallow 3.0.0b13. 2.x and 3b are now supported.
- Add support for apispec 1.0.0b2. 0.x and 1b are now supported.

Bug fixes:

- Document response schema correctly when using OpenAPI 3 (:issue:`8`). Thanks
  :user:`ffarella` for reporting.

0.7.0 (2018-07-19)
++++++++++++++++++

Other changes:

- *Backwards-incompatible*: Remove ``_wrapper_class`` from ``Page``. Creating a
  custom pager is easier by just overriding ``Page`` methods.
- *Backwards-incompatible*: Let ``OPENAPI_SWAGGER_UI_SUPPORTED_SUBMIT_METHODS``
  default to "all methods" list.

0.6.1 (2018-06-29)
++++++++++++++++++

Bug fixes:

- Swagger UI integration: respect ``OPENAPI_SWAGGER_UI_URL`` configuration paramater.
- ``Api.register_field``: use ``APISpec.register_field`` rather than access ``self.spec.ma_plugin`` directly.

0.6.0 (2018-06-29)
++++++++++++++++++

Features:

- *Backwards-incompatible*: Use apispec 0.39.0 plugin class interface.
- *Backwards-incompatible*: Expose APISpec's ``register_field`` and ``register_converter methods`` from ``Api`` object. ``Api.register_converter`` signature is modified to make ``name`` parameter optional.
- Pass extra apispec plugins to internal APISpec instance.

Other changes:

- *Backwards-incompatible*: Drop official support for Python 3.4.

0.5.2 (2018-06-21)
++++++++++++++++++

Features:

- Pass OpenAPI version as ``OPENAPI_VERSION`` app config parameter.
- Add Swagger UI (3.x) integration.

0.5.1 (2018-06-18)
++++++++++++++++++

Features:

- ReDoc: Use unpkg CDN for 2.x version.

0.5.0 (2018-06-05)
++++++++++++++++++

Features:

- *Backwards-incompatible*: In ``Blueprint.route``, the endpoint name defaults to the function name with the case unchanged. Before this change, the name was lowercased.
- *Backwards-incompatible*: Pagination is now managed by dedicated ``Blueprint.paginate`` decorator.
- Add ``etag.INCLUDE_HEADERS`` to specify which headers to use for ETag computation (defaults to ``['X-Pagination']``).
- In ``verify_check_etag``, endpoint name is added to the warning message.

0.4.2 (2018-04-27)
++++++++++++++++++

Bug fixes:

- Pagination: don't crash if ``item_count`` is not set, just log a warning and set no pagination header.
- API spec: Fix leading/trailing slash issues in api-docs Blueprint. Fixes compatibility with Flask 1.0.

0.4.1 (2018-04-17)
++++++++++++++++++

Features:

- Allow multiple calls to ``Blueprint.arguments`` on a view function.
- Enforce order of fields in ``PaginationParametersSchema`` and ``PaginationMetadataSchema``.
- Minor improvements in test_examples.py.

0.4.0 (2018-04-05)
++++++++++++++++++

Features:

- *Backwards-incompatible*: The case of a parameter both in URL and in arguments Schema is now unsupported.
- *Backwards-incompatible*: By default, Schema parameter passed in ``Blueprint.arguments`` is documented as `required`.
- *Backwards-incompatible*: ``APISpec.register_field`` now uses apispec API. It must be passed a  ``(type, format)`` couple or an already registered ``Field`` class (this includes base marshmallow ``Fields``. When using ``(type, format)``, ``format`` doesn't default to ``None`` anymore.
- Preserve order when serving the spec file:
  - Fields are printed in declaration order if Schema.Meta.ordered is True
  - Methods in a method view are printed in this order: ['OPTIONS', 'HEAD', 'GET', 'POST', 'PUT', 'PATCH', 'DELETE']
  - Paths are added in declaration order

Bug fixes:

- Document response as array when using paginate_with.

0.3.0 (2018-03-02)
++++++++++++++++++

Features:

- Add leading and trailing ``/`` to OPENAPI_URL_PREFIX if missing.
- *Backwards-incompatible*: Change default URL path for OpenAPI JSON to ``'openapi.json'``.

Bug fixes:

- Fix OpenAPI docs URL paths.
- *Backwards-incompatible*: ``Blueprint.route(self, rule, **options)`` matches ``flask``'s ``Blueprint`` signature.

0.2.0 (2018-03-02)
++++++++++++++++++

Features:

- ``format`` parameter in ``register_converter`` and ``register_field`` is now optional and defaults to ``None``.
- APISpec inherits from original apispec.APISpec.
- *Backwards-incompatible*: The internal ``APISpec`` instance is now exposed as public attribute ``spec`` of ``Api``. ``register_converter`` and ``register_field`` are not proxied anymore by ``Api`` and must be called on ``spec``.
- *Backwards-incompatible*: ``Api.register_converter`` takes a ``name`` parameter and registers a converter in the ``Flask`` application as well as in its internal ``APISpec`` instance.
- *Backwards-incompatible*: ``Api.register_spec_plugin`` is removed. ``api.register_spec_plugin(...)`` shall be replaced with ``api.spec.setup_plugin(...)``.

0.1.1 (2018-02-16)
++++++++++++++++++

Bug fixes:

- Fix version number.

Support:

- Add dev-requirements.txt.

0.1.0 (2018-02-16)
++++++++++++++++++

First release.
