"""Stuff needed to support several versions of dependencies."""

import marshmallow


MARSHMALLOW_VERSION_MAJOR = int(marshmallow.__version__.split('.')[0])
