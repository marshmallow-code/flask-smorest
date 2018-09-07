Changelog
---------

0.8.0 (unreleased)
++++++++++++++++++

Features:

- *Backwards-incompatible*: Get `summary` and `description` from docstrings
  (:pr:`5`).

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
- *Backwards-incompatible*: Drop officiel support for Python 3.4.

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
