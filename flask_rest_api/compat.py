"""Stuff needed to support several versions of dependencies."""

import marshmallow
import apispec


MARSHMALLOW_VERSION_MAJOR = int(marshmallow.__version__.split('.')[0])
APISPEC_VERSION_MAJOR = int(apispec.__version__.split('.')[0])
