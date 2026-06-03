=============
flask-smorest 
=============

|pypi| |python-versions| |build-status| |pre-commit| |docs| |coverage|

.. |pypi| image:: https://badgen.net/pypi/v/flask-smorest
    :target: https://pypi.org/project/flask-smorest/
    :alt: Latest version

.. |python-versions| image:: https://img.shields.io/pypi/pyversions/flask-smorest.svg
    :target: https://pypi.org/project/flask-smorest/
    :alt: Python versions

.. |build-status| image:: https://github.com/marshmallow-code/flask-smorest/actions/workflows/build-release.yml/badge.svg
    :target: https://github.com/marshmallow-code/flask-smorest/actions/workflows/build-release.yml
    :alt: Build status

.. |pre-commit| image:: https://results.pre-commit.ci/badge/github/marshmallow-code/flask-smorest/dev.svg
   :target: https://results.pre-commit.ci/latest/github/marshmallow-code/flask-smorest/dev
   :alt: pre-commit.ci status

.. |docs| image:: https://readthedocs.org/projects/flask-smorest/badge/
   :target: https://flask-smorest.readthedocs.io/
   :alt: Documentation

.. |coverage| image:: https://codecov.io/gh/marshmallow-code/flask-smorest/branch/main/graph/badge.svg?token=F676tOSaLF
    :target: https://codecov.io/gh/marshmallow-code/flask-smorest
    :alt: Code coverage

'cause everybody wants s'more
=============================

**flask-smorest** is a REST API framework built upon `Flask <https://palletsprojects.com/p/flask/>`_ and
`marshmallow <https://github.com/marshmallow-code/marshmallow>`_.

Features
========

- Serialization, deserialization and validation using marshmallow ``Schema``
- Explicit validation error messages returned in response
- Database-agnostic
- OpenAPI (Swagger) specification automatically generated and exposed with
  `ReDoc <https://github.com/Rebilly/ReDoc>`_,
  `Swagger UI <https://swagger.io/tools/swagger-ui/>`_ or
  `RapiDoc <https://mrin9.github.io/RapiDoc/>`_
- Pagination
- ETag

Install
=======

::

    pip install flask-smorest

Documentation
=============

Full documentation is available at http://flask-smorest.readthedocs.io/.

Contributing
============

Check out the
`Contributing Guidelines <https://github.com/marshmallow-code/.github/blob/main/CONTRIBUTING.md>`_
to see how you can help.

Please also check out our
`Code of Conduct <https://github.com/marshmallow-code/.github/blob/main/CODE_OF_CONDUCT.md>`_.

Support flask-smorest
=====================

If you'd like to support the future of the project, please consider
contributing to marshmallow's Open Collective:

.. image:: https://opencollective.com/marshmallow/donate/button.png
    :target: https://opencollective.com/marshmallow
    :width: 200
    :alt: Donate to our collective

License
=======

MIT licensed. See the `LICENSE <https://github.com/marshmallow-code/flask-smorest/blob/main/LICENSE>`_ file for more details.
