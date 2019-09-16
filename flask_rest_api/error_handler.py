"""Exception handler"""

from werkzeug.exceptions import HTTPException


class ErrorHandlerMixin:
    """Extend Api to manage error handling."""

    def _register_error_handlers(self):
        """Register error handlers in Flask app

        This method registers a default error handler for ``HTTPException``.
        """
        self._app.register_error_handler(
            HTTPException, self.handle_http_exception)

    def handle_http_exception(self, error):
        """Return a JSON response containing a description of the error

        This method is registered at app init to handle ``HTTPException``.

        - When ``abort`` is called in the code, an ``HTTPException`` is
          triggered and Flask calls this handler.

        - When an exception is not caught in a view, Flask makes it an
          ``InternalServerError`` and calls this handler.

        flask_rest_api republishes webargs's
        :func:`abort <webargs.flaskparser.abort>`. This ``abort`` allows the
        caller to pass kwargs and stores them in ``exception.data`` so that the
        error handler can use them to populate the response payload.

        Extra information expected by this handler:

        - `message` (``str``): a comment
        - `errors` (``dict``): errors, typically validation errors in
            parameters and request body
        - `headers` (``dict``): additional headers
        """
        headers = {}
        payload = {'code': error.code, 'status': error.name}

        # Get additional info passed as kwargs when calling abort
        # data may not exist if
        # - HTTPException was raised not using webargs abort or
        # - no kwargs were passed (https://github.com/sloria/webargs/pull/184)
        #   and webargs<1.9.0
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

        return payload, error.code, headers
