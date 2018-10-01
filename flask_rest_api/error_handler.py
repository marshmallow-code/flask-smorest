"""Exception handler"""

from werkzeug.exceptions import HTTPException, InternalServerError
from flask import jsonify, current_app


class ErrorHandlerMixin:
    """Extend Api to manage error handling."""

    def _register_error_handlers(self):
        """Register error handlers in Flask app

        This method registers a default error handler for HTTPException.
        """
        self._app.register_error_handler(
            HTTPException, self.handle_http_exception)

    def handle_http_exception(self, error):
        """Return error description and details in response body

        This method is registered at init to handle `HTTPException`.

        - When `abort` is called in the code, this triggers a `HTTPException`,
          and Flask calls this handler to generate a better response.

        - Also, when an exception is not caught in a view, Flask automatically
          calls the 500 error handler.

        flask_rest_api republishes webarg's `abort` override. This `abort`
        allows the caller to pass kwargs and stores those kwargs in
        `exception.data`.

        This handler uses this extra information to populate the response.

        Extra information considered by this handler:
        - `message`: a comment (string)
        - `errors`: a dict of errors, typically validation issues on a form
        - `headers`: a dict of additional headers

        If the error is an `HTTPException` (typically if it was triggered by
        `abort`), this handler logs it with `INF0` level. Otherwise, it is an
        unhandled exception and it is already logged as `ERROR` by Flask.
        """
        # TODO: use an error Schema
        # TODO: add a parameter to enable/disable logging?

        # If error is not a HTTPException, then it is an unhandled exception.
        # Make it a 500 (InternalServerError) and don't log.
        do_log = True
        if not isinstance(error, HTTPException):
            error = InternalServerError()
            do_log = False

        payload, headers = self._prepare_error_reponse_content(error)
        if do_log:
            self._log_error(error, payload)
        return jsonify(payload), error.code, headers

    @staticmethod
    def _prepare_error_reponse_content(error):
        """Build payload and headers from error"""
        headers = {}
        payload = {'status': str(error), }

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

        return payload, headers

    @staticmethod
    def _log_error(error, payload):
        """Log error as INFO, including payload content"""
        log_string_content = [str(error.code), ]
        log_string_content.extend([
            str(payload[k]) for k in ('message', 'errors') if k in payload])
        current_app.logger.info(' '.join(log_string_content))
