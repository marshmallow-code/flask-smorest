"""ETag feature"""

import hashlib

from flask import request, current_app, json

from .exceptions import PreconditionRequired, PreconditionFailed, NotModified
from .utils import get_appcontext
from .compat import MARSHMALLOW_VERSION_MAJOR


METHODS_NEEDING_CHECK_ETAG = ['PUT', 'PATCH', 'DELETE']
METHODS_ALLOWING_SET_ETAG = ['GET', 'HEAD', 'POST', 'PUT', 'PATCH']

# Can be mutated to specify which headers to use for ETag computation
INCLUDE_HEADERS = ['X-Pagination']


def is_etag_enabled(app):
    """Return True if ETag feature enabled application-wise"""
    return app.config.get('ETAG_ENABLED', False)


def _get_etag_ctx():
    """Get ETag section of AppContext"""
    return get_appcontext()['etag']


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


def _generate_etag(etag_data, etag_schema=None, extra_data=None):
    """Generate an ETag from data

    etag_data: Data to use to compute ETag
    etag_schema: Schema to dump data with before hashing
    extra_data: Extra data to add before hashing

    Typically, extra_data is used to add pagination metadata to the hash. It is
    not dumped through the Schema.
    """
    if etag_schema is None:
        raw_data = etag_data
    else:
        if isinstance(etag_schema, type):
            etag_schema = etag_schema()
        raw_data = etag_schema.dump(etag_data)
        if MARSHMALLOW_VERSION_MAJOR < 3:
            raw_data = raw_data[0]
    if extra_data:
        raw_data = (raw_data, extra_data)
    # flask's json.dumps is needed here
    # as vanilla json.dumps chokes on lazy_strings
    data = json.dumps(raw_data, sort_keys=True)
    return hashlib.sha1(bytes(data, 'utf-8')).hexdigest()


def check_precondition():
    """Check If-Match header is there

    Raise 428 if If-Match header missing

    Called automatically for PUT, PATCH and DELETE methods
    """
    # TODO: other methods?
    # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/If-Match
    if (is_etag_enabled_for_request() and
            request.method in METHODS_NEEDING_CHECK_ETAG and
            not request.if_match):
        raise PreconditionRequired


def check_etag(etag_data, etag_schema=None):
    """Compare If-Match header with computed ETag

    Raise 412 if If-Match-Header does not match.

    Must be called from resource code to check ETag.

    Unfortunately, there is no way to call it automatically. It is the
    developer's responsability to do it. However, a warning is logged at
    runtime if this function was not called.
    """
    if is_etag_enabled_for_request():
        etag_schema = etag_schema or _get_etag_schema()
        new_etag = _generate_etag(etag_data, etag_schema)
        _get_etag_ctx()['etag_checked'] = True
        if new_etag not in request.if_match:
            raise PreconditionFailed


def verify_check_etag():
    """Verify check_etag was called in resource code

    Log a warning if ETag is enabled but check_etag was not called in
    resource code in a PUT, PATCH or DELETE method.

    This is called automatically. It is meant to warn the developer about an
    issue in his ETag management.
    """
    if (is_etag_enabled_for_request() and
            request.method in METHODS_NEEDING_CHECK_ETAG):
        if not _get_etag_ctx().get('etag_checked'):
            current_app.logger.warning(
                'ETag enabled but not checked in endpoint {} on {} request.'
                .format(request.endpoint, request.method))


def set_etag(etag_data, etag_schema=None):
    """Set ETag for this response

    Raise 304 if ETag identical to If-None-Match header

    Can be called from resource code. If not called, ETag will be computed by
    default from response data before sending response.

    Logs a warning if called in a method other than GET, HEAD, POST, PUT, PATCH
    """
    if request.method not in METHODS_ALLOWING_SET_ETAG:
        current_app.logger.warning(
            'ETag cannot be set on {} request.'.format(request.method))
    if is_etag_enabled_for_request():
        etag_schema = etag_schema or _get_etag_schema()
        new_etag = _generate_etag(etag_data, etag_schema)
        if new_etag in request.if_none_match:
            raise NotModified
        # Store ETag in AppContext to add it the the response headers later on
        _get_etag_ctx()['etag'] = new_etag


def set_etag_in_response(response, etag_data, etag_schema):
    """Set ETag in response object

    Called automatically.

    If no ETag data was computed using set_etag, it is computed here from
    response data.
    """
    if (is_etag_enabled_for_request() and
            request.method in METHODS_ALLOWING_SET_ETAG):
        new_etag = _get_etag_ctx().get('etag')
        # If no ETag data was manually provided, use response content
        if new_etag is None:
            headers = (response.headers.get(h) for h in INCLUDE_HEADERS)
            extra_data = tuple(h for h in headers if h is not None)
            new_etag = _generate_etag(etag_data, etag_schema, extra_data)
            if new_etag in request.if_none_match:
                raise NotModified
        response.set_etag(new_etag)
