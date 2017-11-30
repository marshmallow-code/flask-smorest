"""Exception handler"""

from flask import jsonify, current_app
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

    This handler uses this extra information to populate the response.

    Extra information considered by this handler:
    - message: a comment (string)
    - errors: a dict of errors, typically validation issues on a form
    - headers: a dict of additional headers

    When the error was triggered with 'abort', it is logged with INFO level.
    """

    # TODO: manage case where messages/errors is a list?
    # TODO: use an error Schema
    # TODO: make log optional?

    log_info = True

    # Flask redirects unhandled exceptions to error 500 handler
    # If error is not a HTTPException, then it is an unhandled exception
    # Return a 500 (InternalServerError)
    if not isinstance(error, HTTPException):
        error = InternalServerError()
        # Flask logs uncaught exceptions as ERROR already, no need to log here
        log_info = False

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

    # Log error as INFO, including payload content
    if log_info:
        log_string_content = [str(error.code), ]
        for key in ('message', 'errors'):
            if key in payload:
                log_string_content.append(str(payload[key]))
        current_app.logger.info(' '.join(log_string_content))

    return jsonify(payload), error.code, headers
