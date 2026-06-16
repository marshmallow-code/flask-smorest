import pytest

from flask import abort as flask_abort
from werkzeug.exceptions import InternalServerError, default_exceptions

from flask_smorest import Api
from flask_smorest import abort as api_abort
from flask_smorest.exceptions import ApiException


class TestErrorHandler:
    @pytest.mark.parametrize("code", default_exceptions)
    def test_error_handler_on_api_abort(self, app, code):
        client = app.test_client()

        @app.route("/api-abort")
        def test_abort():
            api_abort(code)

        Api(app)

        response = client.get("/api-abort")
        assert response.status_code == code
        assert response.content_type == "application/json"
        assert response.json["code"] == code
        assert response.json["status"] == default_exceptions[code]().name

    @pytest.mark.parametrize("code", default_exceptions)
    def test_error_handler_on_default_abort(self, app, code):
        client = app.test_client()

        @app.route("/html-abort")
        def test_abort():
            flask_abort(code)

        Api(app)

        response = client.get("/html-abort")
        assert response.status_code == code
        assert response.content_type == "text/html; charset=utf-8"

    def test_flask_error_handler_on_unhandled_error(self, app):
        # Unset TESTING to let Flask return 500 on unhandled exception
        app.config["TESTING"] = False
        client = app.test_client()

        @app.route("/html-uncaught")
        def test_uncaught():
            raise Exception("Oops, something really bad happened.")

        Api(app)

        response = client.get("/html-uncaught")
        assert response.status_code == 500
        assert response.content_type == "text/html; charset=utf-8"
        assert "<h1>Internal Server Error</h1>" in response.text

    def test_api_error_handler_on_unhandled_error(self, app):
        # Unset TESTING to let Flask return 500 on unhandled exception
        app.config["TESTING"] = False
        client = app.test_client()

        @app.route("/api-uncaught")
        def test_uncaught():
            raise ApiException("Oops, something really bad happened.")

        Api(app)

        response = client.get("/api-uncaught")
        assert response.content_type == "application/json"
        assert response.json["code"] == 500
        assert response.json["status"] == InternalServerError().name

    def test_error_handler_payload(self, app):
        client = app.test_client()

        errors = {"dimensions": ["Too tall", "Too wide"], "color": ["Too bright"]}
        messages = {"name": ["Too long"], "age": ["Too young"]}

        @app.route("/message")
        def test_message():
            api_abort(404, message="Resource not found")

        @app.route("/messages")
        def test_messages():
            api_abort(422, messages=messages, message="Validation issue")

        @app.route("/errors")
        def test_errors():
            api_abort(422, errors=errors, messages=messages, message="Wrong!")

        @app.route("/headers")
        def test_headers():
            api_abort(
                401,
                message="Access denied",
                headers={"WWW-Authenticate": 'Basic realm="My Server"'},
            )

        Api(app)

        response = client.get("/message")
        assert response.status_code == 404
        assert response.json["message"] == "Resource not found"

        response = client.get("/messages")
        assert response.status_code == 422
        assert response.json["errors"] == messages

        response = client.get("/errors")
        assert response.status_code == 422
        assert response.json["errors"] == errors

        response = client.get("/headers")
        assert response.status_code == 401
        assert response.headers["WWW-Authenticate"] == 'Basic realm="My Server"'
        assert response.json["message"] == "Access denied"
