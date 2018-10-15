Changelog
---------

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
- *Backwards-incompatible*: Drop Flask 0.x support. Flask>=1.0 is now required.
- Default error handler is registered for generic ``HTTPException``. Other
  extensions may register other handlers for specific exceptions or codes
  (:pr:`12`).

0.8.1 (2018-09-24)
++++++++++++++++++

Features:

- Add `page` (page number) to pagination metadata.
- Set `produces` and `consumes` root document attributes when using OpenAPI v2.

Bug fixes:

- Document body parameter correctly when using OpenAPI 3.

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

- App leading and trailing ``/`` to OPENAPI_URL_PREFIX if missing.
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
