flask-smorest: Flask/Marshmallow-based REST API framework
=========================================================

Release v\ |version|. (:ref:`Changelog <changelog>`)

**flask-smorest** (formerly known as flask-rest-api) is a database-agnostic
framework library for creating REST APIs.

It uses Flask as a webserver, and marshmallow_ to serialize and deserialize data.
It relies extensively on the marshmallow ecosystem, using webargs_ to get arguments
from requests, and apispec_ to generate an OpenAPI_ specification file as
automatically as possible.


Install
=======

flask-smorest requires Python >= 3.6.

.. code-block:: bash

    $ pip install flask-smorest


Guide
=====

.. toctree::
    :maxdepth: 1

    quickstart
    arguments 
    response
    pagination
    etag
    openapi


API Reference
=============

.. toctree::
    :maxdepth: 2

    api_reference

Project Info
============

.. toctree::
    :maxdepth: 1

    changelog
    license
    authors



.. _marshmallow: https://marshmallow.readthedocs.io/
.. _webargs: https://webargs.readthedocs.io/
.. _apispec: https://apispec.readthedocs.io/
.. _OpenAPI: https://www.openapis.org/
