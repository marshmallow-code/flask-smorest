# -*- coding: utf-8 -*-
"""
Conditional request execution using the If-Match and If-None-Match headers
 with a monkeypatched Werkzeug method (set_etag from ETagResponseMixin),
 triggered by a decorator in Flask.

Inspired by flask snippet: http://flask.pocoo.org/snippets/95/
"""

from functools import wraps
import hashlib
import json

from flask import g, request, current_app
from werkzeug import ETagResponseMixin
from webargs.flaskparser import abort

from .exceptions import PreconditionRequired, NotModified


def is_etag_enabled(app):
    return not app.config.get('ETAG_DISABLED', False)


def generate_etag(data=None):
    """Generates an etag based on data."""
    etag_data = json.dumps(data, sort_keys=True)
    etag = hashlib.sha1(bytes(etag_data, 'utf-8')).hexdigest()

    return etag


def conditional(func):
    """Start conditional method execution for this resource."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if is_etag_enabled(current_app):
            g.condtnl_etags_start = True
        return func(*args, **kwargs)
    return wrapper


_old_set_etag = ETagResponseMixin.set_etag


@wraps(ETagResponseMixin.set_etag)
def _new_set_etag(self, etag, weak=False):
    # only check the first time through; when called twice we're modifying
    if hasattr(g, 'condtnl_etags_start') and g.condtnl_etags_start:
        if request.method in ('PUT', 'DELETE', 'PATCH'):
            if not request.if_match:
                raise PreconditionRequired
            if etag not in request.if_match:
                abort(412)
        elif (request.method == 'GET'):
            if (request.if_none_match and etag in request.if_none_match):
                raise NotModified
        g.condtnl_etags_start = False
    _old_set_etag(self, etag, weak)

ETagResponseMixin.set_etag = _new_set_etag
