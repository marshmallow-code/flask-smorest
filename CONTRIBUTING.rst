Contributing Guidelines
=======================

Contributing Code
-----------------

Setting Up for Local Development
++++++++++++++++++++++++++++++++

1. Fork flask-smorest_ on Github.

::

    $ git clone https://github.com/marshmallow-code/flask-smorest.git
    $ cd flask-smorest

2. Install development requirements.
   **It is highly recommended that you use a virtualenv.**
   Use the following command to install an editable version of
   flask-smorest along with its development requirements.

::

    # After activating your virtualenv
    $ pip install -e '.[dev]'

3. Install the pre-commit hooks, which will format and lint your git staged files.

::

    # The pre-commit CLI was installed above
    $ pre-commit install

Git Branch Structure
++++++++++++++++++++

**Always make a new branch for your work**, no matter how small.
Also, **do not put unrelated changes in the same branch or pull request**.
This makes it more difficult to merge your changes.

Pull Requests
++++++++++++++

1. Create a new local branch.

::

    # For a new feature or bugfix
    $ git checkout -b name-of-feature-or-bugfix dev

2. Commit your changes.

Write `good commit messages <https://tbaggery.com/2008/04/19/a-note-about-git-commit-messages.html>`_.

::

    $ git commit -m "Detailed commit message"
    $ git push origin name-of-feature-or-bugfix

3. Before submitting a pull request, check the following:

- If the pull request adds functionality, it is tested and the docs are updated.
- You've added yourself to ``AUTHORS.rst``.

4. Submit a pull request to ``marshmallow-code:master``.

The CI build must be passing before your pull request is merged.

Running tests
+++++++++++++

To run all tests: ::

    $ pytest

To run formatting and syntax checks: ::

    $ pre-commit run --all-files

.. _flask-smorest: https://github.com/marshmallow-code/flask-smorest
