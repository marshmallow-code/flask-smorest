"""Custom exceptions"""

import werkzeug.exceptions as wexc


class FlaskSmorestError(Exception):
    """Generic flask-smorest exception"""


# Non-API exceptions
class MissingAPIParameterError(FlaskSmorestError):
    """Missing API parameter"""


class CurrentApiNotAvailableError(FlaskSmorestError):
    """`current_api` not available"""


# API exceptions
class ApiException(wexc.HTTPException, FlaskSmorestError):
    """A generic API error."""

    @classmethod
    def get_exception_by_code(cls, code):
        for exception in cls.__subclasses__():
            if exception.code == code:
                return exception
        return InternalServerError


class BadRequest(wexc.BadRequest, ApiException):
    """Bad request"""


class Unauthorized(wexc.Unauthorized, ApiException):
    """Unauthorized access"""


class Forbidden(wexc.Forbidden, ApiException):
    """Forbidden access"""


class NotFound(wexc.NotFound, ApiException):
    """Resource not found"""


class MethodNotAllowed(wexc.MethodNotAllowed, ApiException):
    """Method not allowed"""


class NotAcceptable(wexc.NotAcceptable, ApiException):
    """Not acceptable"""


class RequestTimeout(wexc.RequestTimeout, ApiException):
    """Request timeout"""


class Conflict(wexc.Conflict, ApiException):
    """Conflict"""


class Gone(wexc.Gone, ApiException):
    """Resource gone"""


class LengthRequired(wexc.LengthRequired, ApiException):
    """Length required"""


class PreconditionFailed(wexc.PreconditionFailed, ApiException):
    """Etag required and wrong ETag provided"""


class RequestEntityTooLarge(wexc.RequestEntityTooLarge, ApiException):
    """Request entity too large"""


class RequestURITooLarge(wexc.RequestURITooLarge, ApiException):
    """Request URI too large"""


class UnsupportedMediaType(wexc.UnsupportedMediaType, ApiException):
    """Unsupported media type"""


class RequestedRangeNotSatisfiable(wexc.RequestedRangeNotSatisfiable, ApiException):
    """Requested range not satisfiable"""


class ExpectationFailed(wexc.ExpectationFailed, ApiException):
    """Expectation failed"""


class ImATeapot(wexc.ImATeapot, ApiException):
    """I'm a teapot"""


class UnprocessableEntity(wexc.UnprocessableEntity, ApiException):
    """Unprocessable entity"""


class Locked(wexc.Locked, ApiException):
    """Locked"""


class FailedDependency(wexc.FailedDependency, ApiException):
    """Failed dependency"""


class PreconditionRequired(wexc.PreconditionRequired, ApiException):
    """Etag required but missing"""

    # Overriding description as we don't provide If-Unmodified-Since
    description = 'This request is required to be conditional; try using "If-Match".'


class TooManyRequests(wexc.TooManyRequests, ApiException):
    """Too many requests"""


class RequestHeaderFieldsTooLarge(wexc.RequestHeaderFieldsTooLarge, ApiException):
    """Request header fields too large"""


class UnavailableForLegalReasons(wexc.UnavailableForLegalReasons, ApiException):
    """Unavailable for legal reasons"""


class InternalServerError(wexc.InternalServerError, ApiException):
    """Internal server error"""


class NotImplemented(wexc.NotImplemented, ApiException):
    """Not implemented"""


class BadGateway(wexc.BadGateway, ApiException):
    """Bad gateway"""


class ServiceUnavailable(wexc.ServiceUnavailable, ApiException):
    """Service unavailable"""


class GatewayTimeout(wexc.GatewayTimeout, ApiException):
    """Gateway timeout"""


class HTTPVersionNotSupported(wexc.HTTPVersionNotSupported, ApiException):
    """HTTP version not supported"""


class NotModified(ApiException):
    """Resource was not modified (Etag is unchanged)

    Exception created to compensate for a lack in Werkzeug (and Flask)
    """

    code = 304
    description = "Resource not modified since last request."


def abort(http_status_code, exc=None, **kwargs):
    try:
        raise ApiException.get_exception_by_code(http_status_code)
    except ApiException as err:
        err.data = kwargs
        err.exc = exc
        raise err
    except Exception as err:
        raise err
