"""Custom exceptions"""

import werkzeug.exceptions as wexc


class FlaskRestApiError(Exception):
    """Generic flask-rest-api exception"""


class EndpointMethodDocAlreadyRegisted(FlaskRestApiError):
    """Documentation already registered for this endpoint/method couple"""


class InvalidLocation(FlaskRestApiError):
    """Parameter location is not a valid location"""


class PageOutOfRangeError(FlaskRestApiError):
    """Requested page number out of page range"""


class NotModified(wexc.HTTPException, FlaskRestApiError):
    """Resource was not modified (Etag is unchanged)

    Exception created to compensate for a lack in Werkzeug (and Flask)
    """
    code = 304
    description = 'Resource not modified since last request.'


class PreconditionRequired(wexc.PreconditionRequired, FlaskRestApiError):
    """Etag required but missing"""
    # Overriding description as we don't provide If-Unmodified-Since
    description = (
        'This request is required to be conditional; try using "If-Match".')


class PreconditionFailed(wexc.PreconditionFailed, FlaskRestApiError):
    """Etag required and wrong ETag provided"""
