import pytest

from werkzeug.exceptions import default_exceptions, InternalServerError
from flask_smorest import Api, abort


class TestErrorHandler:

    @pytest.mark.parametrize('code', default_exceptions)
    def test_error_handler_on_abort(self, app, code):

        client = app.test_client()

        @app.route('/abort')
        def test_abort():
            abort(code)

        Api(app)

        response = client.get('/abort')
        assert response.status_code == code
        assert response.json['code'] == code
        assert response.json['status'] == default_exceptions[code]().name

    def test_error_handler_on_unhandled_error(self, app):

        client = app.test_client()

        @app.route('/uncaught')
        def test_uncaught():
            raise Exception('Oops, something really bad happened.')

        Api(app)

        response = client.get('/uncaught')
        assert response.status_code == 500
        assert response.json['code'] == 500
        assert response.json['status'] == InternalServerError().name

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

        response = client.get('/message')
        assert response.status_code == 404
        assert response.json['message'] == 'Resource not found'

        response = client.get('/messages')
        assert response.status_code == 422
        assert response.json['errors'] == messages

        response = client.get('/errors')
        assert response.status_code == 422
        assert response.json['errors'] == errors

        response = client.get('/headers')
        assert response.status_code == 401
        assert (
            response.headers['WWW-Authenticate'] == 'Basic realm="My Server"')
        assert response.json['message'] == 'Access denied'
