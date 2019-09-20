.. _api:

*************
API Reference
*************

.. module:: flask_smorest
.. autofunction:: flask_smorest.abort


Api
===


.. autoclass:: flask_smorest.Api
    :members:

    .. automethod:: register_converter
    .. automethod:: register_field
    .. automethod:: handle_http_exception

Blueprint
=========

.. autoclass:: flask_smorest.Blueprint
    :members:

    .. automethod:: arguments
    .. automethod:: response
    .. automethod:: paginate
    .. automethod:: etag
    .. automethod:: check_etag
    .. automethod:: set_etag

Pagination
==========

.. autoclass:: flask_smorest.Page
    :members:
.. autoclass:: flask_smorest.pagination.PaginationParameters
    :members:


Fields
======

.. automodule:: flask_smorest.fields
     :members:
