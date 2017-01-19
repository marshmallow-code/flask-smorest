from flask import jsonify, current_app
from werkzeug import Headers
from werkzeug.exceptions import HTTPException, InternalServerError


def _handle_http_exception(error):
    """Return error description and details in response body"""

    # TODO: use an error Schema

    # If error is not a HTTPException, it is an unhandled exception
    # Flask redirects unhandled exceptions to error 500 handler
    # Return a 500 (InternalServerError)
    if not isinstance(error, HTTPException):
        error = InternalServerError()

    data_error = {'error': {
        'status_code': error.code,
        'status': str(error),
        'status_description': error.description,
    }}

    headers = Headers()

    # Look for details in data attribute
    data = getattr(error, 'data', None)
    if data:
        if 'messages' in data:
            data_error['error']['details'] = data['messages']
        if 'comment' in data:
            data_error['error']['message'] = data['comment']
        if 'headers' in data:
            for k, v in data['headers'].items():
                headers.add(k, v)

    # TODO: set level according to error type?
    current_app.logger.error(data_error)

    return jsonify(data_error), error.code, headers
