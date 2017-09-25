import pytest

import json
from werkzeug.exceptions import default_exceptions
from flask import Flask
from flask_rest_api import Api, abort


class NoLoggingContext:
    """Context manager to disable logging temporarily

    Those tests purposely trigger errors. We don't want to log them.
    """

    def __init__(self, app):
        self.app = app

    def __enter__(self):
        self.logger_was_disabled = self.app.logger.disabled
        self.app.logger.disabled = True

    def __exit__(self, et, ev, tb):
        self.app.logger.disabled = self.logger_was_disabled


class TestErrorHandlers:

    @pytest.mark.parametrize('code', default_exceptions)
    def test_error_handlers_registration(self, code):
        """Check custom error handler is registered for all codes"""

        app = Flask('test')
        client = app.test_client()

        @app.route("/{}".format(code))
        def test():
            abort(code)

        Api(app)

        with NoLoggingContext(app):
            response = client.get("/{}".format(code))
        assert response.status_code == code

        data = json.loads(response.get_data(as_text=True))
        assert data['error']['status_code'] == code

    def test_default_exception_handler(self):

        app = Flask('test')
        client = app.test_client()

        @app.route("/")
        def test():
            raise Exception

        Api(app)

        with NoLoggingContext(app):
            response = client.get("/")
        assert response.status_code == 500

        data = json.loads(response.get_data(as_text=True))
        assert data['error']['status_code'] == 500
