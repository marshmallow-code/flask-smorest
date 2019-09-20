==============
flask-smorest
==============

.. image:: https://img.shields.io/pypi/v/flask-smorest.svg
    :target: https://pypi.org/project/flask-smorest/
    :alt: Latest version

.. image:: https://img.shields.io/pypi/pyversions/flask-smorest.svg
    :target: https://pypi.org/project/flask-smorest/
    :alt: Python versions

.. image:: https://img.shields.io/badge/marshmallow-2%20|%203-blue.svg
    :target: https://marshmallow.readthedocs.io/en/latest/upgrading.html
    :alt: marshmallow 2/3 compatible

.. image:: https://img.shields.io/badge/OAS-2%20|%203-green.svg
    :target: https://github.com/OAI/OpenAPI-Specification
    :alt: OpenAPI Specification 2/3 compatible

.. image:: https://img.shields.io/pypi/l/flask-smorest.svg
    :target: https://flask-smorest.readthedocs.io/en/latest/license.html
    :alt: License

.. image:: https://img.shields.io/travis/marshmallow-code/flask-smorest/master.svg
    :target: https://travis-ci.org/marshmallow-code/flask-smorest
    :alt: Build status

.. image:: https://coveralls.io/repos/github/marshmallow-code/flask-smorest/badge.svg?branch=master
    :target: https://coveralls.io/github/marshmallow-code/flask-smorest/?branch=master
    :alt: Code coverage

.. image:: https://readthedocs.org/projects/flask-smorest/badge/
    :target: http://flask-smorest.readthedocs.io/
    :alt: Documentation

Build a REST API with Flask and marshmallow.

**flask-smorest** relies on `marshmallow <https://github.com/marshmallow-code/marshmallow>`_, `webargs <https://github.com/sloria/webargs>`_ and `apispec <https://github.com/marshmallow-code/apispec/>`_ to provide a complete REST API framework.

Features
========

- Serialization, deserialization and validation using marshmallow ``Schema``.
- OpenAPI (Swagger) specification automatically generated, and exposed with `ReDoc <https://github.com/Rebilly/ReDoc>`_ or `Swagger UI <https://swagger.io/tools/swagger-ui/>`_.
- Pagination.
- ETag.

Install
=======

::

    pip install flask-smorest

flask-smorest supports Python >= 3.5.

Documentation
=============

Full documentation is available at http://flask-smorest.readthedocs.io/.

Support flask-smorest
======================

flask-smorest is built on marshmallow, webargs and apispec.

If you'd like to support the future of the project, please consider
contributing to marshmallow's Open Collective:

.. image:: https://opencollective.com/marshmallow/donate/button.png
    :target: https://opencollective.com/marshmallow
    :width: 200
    :alt: Donate to our collective

License
=======

MIT licensed. See the `LICENSE <https://github.com/marshmallow-code/flask-smorest/blob/master/LICENSE>`_ file for more details.
