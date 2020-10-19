=============
flask-smorest 
=============

.. image:: https://img.shields.io/pypi/v/flask-smorest.svg
    :target: https://pypi.org/project/flask-smorest/
    :alt: Latest version

.. image:: https://img.shields.io/pypi/pyversions/flask-smorest.svg
    :target: https://pypi.org/project/flask-smorest/
    :alt: Python versions

.. image:: https://img.shields.io/badge/marshmallow-3-blue.svg
    :target: https://marshmallow.readthedocs.io/en/latest/upgrading.html
    :alt: marshmallow 3 only

.. image:: https://img.shields.io/badge/OAS-2%20|%203-green.svg
    :target: https://github.com/OAI/OpenAPI-Specification
    :alt: OpenAPI Specification 2/3 compatible

.. image:: https://img.shields.io/pypi/l/flask-smorest.svg
    :target: https://flask-smorest.readthedocs.io/en/latest/license.html
    :alt: License

.. image:: https://dev.azure.com/lafrech/flask-smorest/_apis/build/status/marshmallow-code.flask-smorest?branchName=master
    :target: https://dev.azure.com/lafrech/flask-smorest/_build/latest?definitionId=1&branchName=master
    :alt: Build status

.. image:: https://img.shields.io/azure-devops/coverage/lafrech/flask-smorest/1
    :target: https://dev.azure.com/lafrech/flask-smorest/_build/latest?definitionId=1&branchName=master
    :alt: Code coverage

.. image:: https://readthedocs.org/projects/flask-smorest/badge/
    :target: http://flask-smorest.readthedocs.io/
    :alt: Documentation

'cause everybody wants s'more
=============================

**flask-smorest** (formerly known as flask-rest-api) is a REST API framework
built upon `Flask <https://palletsprojects.com/p/flask/>`_ and
`marshmallow <https://github.com/marshmallow-code/marshmallow>`_.

- Serialization, deserialization and validation using marshmallow ``Schema``
- Explicit validation error messages returned in response
- Database-agnostic
- OpenAPI (Swagger) specification automatically generated and exposed with
  `ReDoc <https://github.com/Rebilly/ReDoc>`_ or
  `Swagger UI <https://swagger.io/tools/swagger-ui/>`_
- Pagination
- ETag

Install
=======

::

    pip install flask-smorest

flask-smorest supports Python >= 3.6.

Documentation
=============

Full documentation is available at http://flask-smorest.readthedocs.io/.

Support flask-smorest
======================

If you'd like to support the future of the project, please consider
contributing to marshmallow's Open Collective:

.. image:: https://opencollective.com/marshmallow/donate/button.png
    :target: https://opencollective.com/marshmallow
    :width: 200
    :alt: Donate to our collective

License
=======

MIT licensed. See the `LICENSE <https://github.com/marshmallow-code/flask-smorest/blob/master/LICENSE>`_ file for more details.
