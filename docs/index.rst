flask-smorest: Flask/Marshmallow-based REST API framework
=========================================================

Release v\ |version|. (:ref:`Changelog <changelog>`)

.. admonition:: Sponsor Message

    Input an OpenAPI spec to generate API docs that look as good as Stripe's. Request a preview of your docs on Fern `here <https://form.typeform.com/to/bShdJw7z>`_.

    .. image:: https://github.com/user-attachments/assets/551997da-6d0c-4d73-85f3-6fb1240e9635
        :target: https://form.typeform.com/to/bShdJw7z
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
