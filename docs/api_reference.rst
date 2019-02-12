.. _api:

*************
API Reference
*************

.. module:: flask_rest_api
.. autofunction:: flask_rest_api.abort


Api
===


.. autoclass:: flask_rest_api.Api
    :members:

    .. automethod:: definition
    .. automethod:: register_converter
    .. automethod:: register_field
    .. automethod:: handle_http_exception

Blueprint
=========

.. autoclass:: flask_rest_api.Blueprint
    :members:

    .. automethod:: arguments
    .. automethod:: response
    .. automethod:: paginate
    .. automethod:: etag
    .. automethod:: check_etag
    .. automethod:: set_etag

Pagination
==========

.. autoclass:: flask_rest_api.Page
    :members:
.. autoclass:: flask_rest_api.pagination.PaginationParameters
    :members:
