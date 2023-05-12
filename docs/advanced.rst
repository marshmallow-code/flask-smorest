.. _advanced:
.. currentmodule:: flask_smorest

Advanced Usage
==============

This section includes guides for advanced usage patterns.

Multiple APIs in a single application
-------------------------------------

It is possible to expose multiple APIs from a single application. When doing so,
the application parameters for each :class:`Api <Api>` instance must be prefixed
with a distinct string that is passed to ``Api`` at init.

.. code-block:: python

   api_1 = Api(config_prefix="V1_")


   class Config:
       V1_OPENAPI_VERSION = "3.0.2"
       V1_OPENAPI_URL_PREFIX = "/v1/"


.. note:: The default prefix is an empty string, so that no prefix is needed
   in the single API case.
