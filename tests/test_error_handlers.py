import pytest

import json
from werkzeug.exceptions import default_exceptions
from flask import Flask, abort
from flask_rest_api import Api


class TestErrorHandlers():

    @pytest.mark.parametrize(
        'code', default_exceptions)
    def test_error_handlers_registration(self, code):
        """Check custom error handler is registered for all codes"""

        app = Flask('test')
        client = app.test_client()

        @app.route("/{}".format(code))
        def test():
            abort(code)

        Api(app)

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

        response = client.get("/")
        assert response.status_code == 500

        data = json.loads(response.get_data(as_text=True))
        assert data['error']['status_code'] == 500
