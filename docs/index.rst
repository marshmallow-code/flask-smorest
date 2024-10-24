flask-smorest: Flask/Marshmallow-based REST API framework
=========================================================

Release v\ |version|. (:ref:`Changelog <changelog>`)

.. admonition:: Sponsor Message

    Input an OpenAPI spec to generate API docs that look as good as Stripe's. `Request a preview <https://form.typeform.com/to/uc55zY0F>`_ of your docs on Fern.

    .. image:: https://github.com/user-attachments/assets/69916225-0d61-4bd7-b3b9-e378557673cb
        :target: https://form.typeform.com/to/uc55zY0F
        :align: center
        :alt: Fern logo

**flask-smorest** (formerly known as flask-rest-api) is a database-agnostic
framework library for creating REST APIs.

It uses Flask as a webserver, and marshmallow_ to serialize and deserialize data.
It relies extensively on the marshmallow ecosystem, using webargs_ to get arguments
from requests, and apispec_ to generate an OpenAPI_ specification file as
automatically as possible.


Install
=======

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
    advanced


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
