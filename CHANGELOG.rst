Changelog
---------

0.3.0 (unreleased)
++++++++++++++++++

- *Backwards-incompatible*: ``Blueprint.route(self, rule, **options)`` matches ``flask``'s ``Blueprint`` signature

0.2.0 (2018-03-02)
++++++++++++++++++

Features:

- ``format`` parameter in ``register_converter`` and ``register_field`` is now optional and defaults to ``None``.
- APISpec inherits from original apispec.APISpec.
- *Backwards-incompatible*: The internal ``APISpec`` instance is now exposed as public attribute ``spec`` of ``Api``. ``register_converter`` and ``register_field`` are not proxied anymore by ``Api`` and must be called on ``spec``.
- *Backwards-incompatible*: ``Api.register_converter`` takes a ``name`` parameter and registers a converter in the ``Flask`` application as well as in its internal ``APISpec`` instance.
- *Backwards-incompatible*: ``Api.register_spec_plugin`` is removed. ``api.register_spec_plugin(...)`` shall be replaced with ``api.spec.setup_plugin(...)``

0.1.1 (2018-02-16)
++++++++++++++++++

Bug fixes:

- Fix version number.

Support:

- Add dev-requirements.txt

0.1.0 (2018-02-16)
++++++++++++++++++

First release.
