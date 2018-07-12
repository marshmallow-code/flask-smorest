.. _api:

*************
API Reference
*************

.. module:: flask_rest_api

Api
===


.. autoclass:: flask_rest_api.Api
    :members:

Blueprint
=========

.. autoclass:: flask_rest_api.Blueprint
    :members:

Pagination
==========

.. autoclass:: flask_rest_api.Page
    :members:
.. autofunction:: flask_rest_api.set_item_count

ETag
====

.. autofunction:: flask_rest_api.etag.is_etag_enabled
.. autofunction:: flask_rest_api.etag.is_etag_enabled_for_request
.. autofunction:: flask_rest_api.etag.check_etag
.. autofunction:: flask_rest_api.etag.set_etag
