==============
flask-rest-api
==============

.. image:: https://img.shields.io/pypi/v/flask-rest-api.svg
    :target: https://pypi.org/project/flask-rest-api/
    :alt: Latest version

.. image:: https://img.shields.io/pypi/pyversions/flask-rest-api.svg
    :target: https://pypi.org/project/flask-rest-api/
    :alt: Python versions

.. image:: https://img.shields.io/badge/marshmallow-2%20|%203-blue.svg
    :target: https://marshmallow.readthedocs.io/en/latest/upgrading.html
    :alt: marshmallow 2/3 compatible

.. image:: https://img.shields.io/badge/OAS-2%20|%203-green.svg
    :target: https://github.com/OAI/OpenAPI-Specification
    :alt: OpenAPI Specification 2/3 compatible

.. image:: https://img.shields.io/pypi/l/flask-rest-api.svg
    :target: https://flask-rest-api.readthedocs.io/en/latest/license.html
    :alt: License

.. image:: https://img.shields.io/travis/Nobatek/flask-rest-api/master.svg
    :target: https://travis-ci.org/Nobatek/flask-rest-api
    :alt: Build status

.. image:: https://coveralls.io/repos/github/Nobatek/flask-rest-api/badge.svg?branch=master
    :target: https://coveralls.io/github/Nobatek/flask-rest-api/?branch=master
    :alt: Code coverage

.. image:: https://api.codacy.com/project/badge/Grade/463485aeeac048f08cb4f40ebeb61160
    :target: https://www.codacy.com/app/lafrech/flask-rest-api
    :alt: Code health

.. image:: https://readthedocs.org/projects/flask-rest-api/badge/
    :target: http://flask-rest-api.readthedocs.io/
    :alt: Documentation

Build a REST API with Flask and marshmallow.

**flask-rest-api** relies on `marshmallow <https://github.com/marshmallow-code/marshmallow>`_, `webargs <https://github.com/sloria/webargs>`_ and `apispec <https://github.com/marshmallow-code/apispec/>`_ to provide a complete REST API framework.

Features
========

- Serialization, deserialization and validation using marshmallow ``Schema``.
- OpenAPI (Swagger) specification automatically generated, and exposed with `ReDoc <https://github.com/Rebilly/ReDoc>`_ or `Swagger UI <https://swagger.io/tools/swagger-ui/>`_.
- Pagination.
- ETag.

Install
=======

::

    pip install flask-rest-api

flask-rest-api supports Python >= 3.5.

Documentation
=============

Full documentation is available at http://flask-rest-api.readthedocs.io/.

Support flask-rest-api
======================

flask-rest-api is built on marshmallow, webargs and apispec.

If you'd like to support the future of the project, please consider
contributing to marshmallow's Open Collective:

.. image:: https://opencollective.com/marshmallow/donate/button.png
    :target: https://opencollective.com/marshmallow
    :width: 200
    :alt: Donate to our collective

License
=======

MIT licensed. See the `LICENSE <https://github.com/Nobatek/flask-rest-api/blob/master/LICENSE>`_ file for more details.
