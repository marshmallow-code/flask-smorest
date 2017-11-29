import json

import pytest

from werkzeug.exceptions import default_exceptions, InternalServerError
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
        assert data['status'] == str(default_exceptions[code]())

    def test_error_handler_payload(self):

        app = Flask('test')
        app.config.debug = True
        app.config['DEBUG'] = True

        client = app.test_client()

        errors = {
            'dimensions': ['Too tall', 'Too wide'],
            'color': ['Too bright']
        }
        messages = {'name': ['Too long'], 'age': ['Too young']}

        @app.route("/message")
        def test_message():
            abort(404, message='Resource not found')

        @app.route("/messages")
        def test_messages():
            abort(422, messages=messages, message='Validation issue')

        @app.route("/errors")
        def test_errors():
            abort(422, errors=errors, messages=messages, message='Wrong!')

        @app.route("/headers")
        def test_headers():
            abort(401, message='Access denied',
                  headers={'WWW-Authenticate': 'Basic realm="My Server"'})

        Api(app)

        with NoLoggingContext(app):
            response = client.get("/message")
        assert response.status_code == 404
        data = json.loads(response.get_data(as_text=True))
        assert data['message'] == 'Resource not found'

        with NoLoggingContext(app):
            response = client.get("/messages")
        assert response.status_code == 422
        data = json.loads(response.get_data(as_text=True))
        assert data['errors'] == messages

        with NoLoggingContext(app):
            response = client.get("/errors")
        assert response.status_code == 422
        data = json.loads(response.get_data(as_text=True))
        assert data['errors'] == errors

        with NoLoggingContext(app):
            response = client.get("/headers")
        assert response.status_code == 401
        assert (
            response.headers['WWW-Authenticate'] == 'Basic realm="My Server"')
        data = json.loads(response.get_data(as_text=True))
        assert data['message'] == 'Access denied'

    def test_uncaught_exception_handler(self):
        """Test uncaught exceptions result in 500 status code being returned"""

        app = Flask('test')
        client = app.test_client()

        @app.route("/")
        def test():
            raise Exception('Oops, something really bad happened.')

        Api(app)

        with NoLoggingContext(app):
            response = client.get("/")
        assert response.status_code == 500

        data = json.loads(response.get_data(as_text=True))
        assert data['status'] == str(InternalServerError())
