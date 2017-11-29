"""Exception handler"""

from flask import jsonify
from werkzeug.exceptions import HTTPException, InternalServerError


def handle_http_exception(error):
    """Return error description and details in response body

    This function is registered at init to handle HTTPException.
    When abort is called in the code, this triggers a HTTPException, and Flask
    calls this handler to generate a better response.

    Also, when an Exception is not caught in a view, Flask automatically
    calls the 500 error handler.

    flask_rest_api republishes webarg's abort override. This abort allows the
    caller to pass kwargs and stores those kwargs in exception.data.

    This handlers uses this extra information to populate the response.

    Extra information considered by this handler:
    - message: a comment (string)
    - errors: a dict of errors, typically validation issues on a form
    - headers: a dict of additional headers
    """

    # TODO: manage case where messages/errors is a list?
    # TODO: use an error Schema
    # TODO: add logging?

    # Flask redirects unhandled exceptions to error 500 handler
    # If error is not a HTTPException, then it is an unhandled exception
    # Return a 500 (InternalServerError)
    if not isinstance(error, HTTPException):
        error = InternalServerError()

    headers = {}

    payload = {
        'status': str(error),
    }

    # Get additional info passed as kwargs when calling abort
    # data may not exist if HTTPException was raised not using webargs abort
    # or if not kwargs were passed (https://github.com/sloria/webargs/pull/184)
    data = getattr(error, 'data', None)
    if data:
        # If we passed a custom message
        if 'message' in data:
            payload['message'] = data['message']
        # If we passed "errors"
        if 'errors' in data:
            payload['errors'] = data['errors']
        # If webargs added validation errors as "messages"
        # (you should use 'errors' as it is more explicit)
        elif 'messages' in data:
            payload['errors'] = data['messages']
        # If we passed additional headers
        if 'headers' in data:
            headers = data['headers']

    return jsonify(payload), error.code, headers
