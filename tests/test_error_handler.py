import json
from unittest import mock

import pytest

from werkzeug.exceptions import default_exceptions, InternalServerError
from flask_rest_api import Api, abort

from .utils import NoLoggingContext


class TestErrorHandler:

    @pytest.mark.parametrize('code', default_exceptions)
    def test_error_handler_on_abort(self, app, code):

        client = app.test_client()
        logger = app.logger

        message = 'What a bad request.'
        errors = {
            'dimensions': ['Too tall', 'Too wide'],
            'color': ['Too bright']
        }

        @app.route('/abort_no_kwargs')
        def test_abort_no_kwargs():
            abort(code)

        @app.route('/abort_kwargs')
        def test_abort_kwargs():
            abort(code, message=message, errors=errors)

        Api(app)

        # Test error handler logs as INFO with payload content
        with mock.patch.object(logger, 'info') as mock_info:
            response = client.get('/abort_no_kwargs')
            assert mock_info.called
            args, kwargs = mock_info.call_args

        assert args == (str(code), )
        assert kwargs == {}

        assert response.status_code == code
        data = json.loads(response.get_data(as_text=True))
        assert data['status'] == str(default_exceptions[code]())

        with mock.patch.object(logger, 'info') as mock_info:
            response = client.get('/abort_kwargs')
            assert mock_info.called
            args, kwargs = mock_info.call_args

        assert args == (' '.join([str(code), message, str(errors)]), )
        assert kwargs == {}

    def test_error_handler_on_unhandled_error(self, app):

        client = app.test_client()
        logger = app.logger

        uncaught_exc = Exception('Oops, something really bad happened.')

        @app.route('/uncaught')
        def test_uncaught():
            raise uncaught_exc

        Api(app)

        # Test Flask logs uncaught exception as ERROR
        # and handle_http_exception does not log is as INFO
        with mock.patch.object(logger, 'error') as mock_error:
            with mock.patch.object(logger, 'info') as mock_info:
                response = client.get('/uncaught')
                assert mock_error.called
                args, kwargs = mock_error.call_args
                assert not mock_info.called

        assert args == ('Exception on /uncaught [GET]', )
        exc_info = kwargs['exc_info']
        _, exc_value, _ = exc_info
        assert exc_value == uncaught_exc

        assert response.status_code == 500
        data = json.loads(response.get_data(as_text=True))
        assert data['status'] == str(InternalServerError())

    def test_error_handler_payload(self, app):

        client = app.test_client()

        errors = {
            'dimensions': ['Too tall', 'Too wide'],
            'color': ['Too bright']
        }
        messages = {'name': ['Too long'], 'age': ['Too young']}

        @app.route('/message')
        def test_message():
            abort(404, message='Resource not found')

        @app.route('/messages')
        def test_messages():
            abort(422, messages=messages, message='Validation issue')

        @app.route('/errors')
        def test_errors():
            abort(422, errors=errors, messages=messages, message='Wrong!')

        @app.route('/headers')
        def test_headers():
            abort(401, message='Access denied',
                  headers={'WWW-Authenticate': 'Basic realm="My Server"'})

        Api(app)

        with NoLoggingContext(app):
            response = client.get('/message')
        assert response.status_code == 404
        data = json.loads(response.get_data(as_text=True))
        assert data['message'] == 'Resource not found'

        with NoLoggingContext(app):
            response = client.get('/messages')
        assert response.status_code == 422
        data = json.loads(response.get_data(as_text=True))
        assert data['errors'] == messages

        with NoLoggingContext(app):
            response = client.get('/errors')
        assert response.status_code == 422
        data = json.loads(response.get_data(as_text=True))
        assert data['errors'] == errors

        with NoLoggingContext(app):
            response = client.get('/headers')
        assert response.status_code == 401
        assert (
            response.headers['WWW-Authenticate'] == 'Basic realm="My Server"')
        data = json.loads(response.get_data(as_text=True))
        assert data['message'] == 'Access denied'
