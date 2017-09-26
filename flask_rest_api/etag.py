"""ETag feature"""

import hashlib

from flask import request, current_app, json

from .exceptions import PreconditionRequired, PreconditionFailed, NotModified
from .utils import get_appcontext


def is_etag_enabled(app):
    """Return True if ETag feature enabled application-wise"""
    return app.config.get('ETAG_ENABLED', False)


def _get_etag_ctx():
    """Get ETag section of AppContext"""
    return get_appcontext().setdefault('etag', {})


def disable_etag_for_request():
    _get_etag_ctx()['disabled'] = True


def is_etag_enabled_for_request():
    """Return True if ETag feature enabled for this request

    It is enabled if
    - the feature is enabled application-wise and
    - it is not disabled for this route
    """
    return (is_etag_enabled(current_app) and
            not _get_etag_ctx().get('disabled', False))


def set_etag_schema(etag_schema):
    _get_etag_ctx()['etag_schema'] = etag_schema


def _get_etag_schema():
    return _get_etag_ctx().get('etag_schema')


def _generate_etag(data, etag_schema=None, *, extra_data=None):
    """Generate an etag from data

    etag_schema: Schema to dump data with before hashing
    extra_data: Extra data to add before hashing

    Typically, extra_data is used to add pagination metadata to the hash
    """
    # flask's json.dumps is needed here
    # as vanilla json.dumps chokes on lazy_strings
    if etag_schema is None:
        raw_data = data
    else:
        if isinstance(etag_schema, type):
            etag_schema = etag_schema()
        raw_data = etag_schema.dump(data)[0]
    if extra_data is not None:
        raw_data = (raw_data, extra_data)
    etag_data = json.dumps(raw_data, sort_keys=True)
    return hashlib.sha1(bytes(etag_data, 'utf-8')).hexdigest()


def check_precondition():
    """Check If-Match header is there

    Raise 428 if If-Match header missing

    Called automatically for PUT and DELETE methods
    """
    # TODO: other methods?
    # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/If-Match
    if (is_etag_enabled_for_request() and
            request.method in ['PUT', 'DELETE'] and
            not request.if_match):
        raise PreconditionRequired


# TODO: log a warning if ETag enabled and this is not called in PUT/DELETE?
def check_etag(etag_data, etag_schema=None):
    """Compare If-Match header with computed ETag

    Raise 412 if If-Match-Header does not match

    Must be called from resource code to check ETag
    """
    if is_etag_enabled_for_request():
        if etag_schema is None:
            etag_schema = _get_etag_schema()
        new_etag = _generate_etag(etag_data, etag_schema)
        if new_etag not in request.if_match:
            raise PreconditionFailed


def set_etag(etag_data, etag_schema=None):
    """Set ETag for this response

    Raise 304 if ETag identical to If-None-Match header

    Can be called from resource code. If not called, ETag will be computed by
    default from response data before sending response.
    """
    if is_etag_enabled_for_request():
        if etag_schema is None:
            etag_schema = _get_etag_schema()
        new_etag = _generate_etag(etag_data, etag_schema)
        if new_etag in request.if_none_match:
            raise NotModified
        # Store ETag in AppContext to add it the the response headers later on
        _get_etag_ctx()['etag'] = new_etag


def set_etag_in_response(
        response, result_raw, etag_schema, *, extra_data=None):
    """Set ETag in response object

    Called automatically.

    If no ETag data was computed using set_etag, it is computed here from
    response data.
    """
    if is_etag_enabled_for_request():
        new_etag = _get_etag_ctx().get('etag')
        # If no ETag data was manually provided, use response content
        if new_etag is None:
            new_etag = _generate_etag(
                result_raw, etag_schema, extra_data=extra_data)
            if new_etag in request.if_none_match:
                raise NotModified
        response.set_etag(new_etag)
