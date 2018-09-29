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

    .. automethod:: arguments
    .. automethod:: response
    .. automethod:: paginate

Pagination
==========

.. autoclass:: flask_rest_api.Page
    :members:
.. autoclass:: flask_rest_api.pagination.PaginationParameters
    :members:

ETag
====

.. autofunction:: flask_rest_api.etag.is_etag_enabled
.. autofunction:: flask_rest_api.etag.is_etag_enabled_for_request
.. autofunction:: flask_rest_api.etag.check_etag
.. autofunction:: flask_rest_api.etag.set_etag
