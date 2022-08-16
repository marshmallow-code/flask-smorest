"""ETag feature"""

from functools import wraps
from copy import deepcopy
import json
import http
import warnings

import hashlib

from marshmallow import Schema
from flask import request, current_app

from .exceptions import PreconditionRequired, PreconditionFailed, NotModified
from .utils import deepupdate, get_appcontext


IF_NONE_MATCH_HEADER = {
    "name": "If-None-Match",
    "in": "header",
    "description": "Tag to check against",
    "schema": {"type": "string"},
}

IF_MATCH_HEADER = {
    "name": "If-Match",
    "in": "header",
    "required": True,
    "description": "Tag to check against",
    "schema": {"type": "string"},
}

ETAG_HEADER = {
    "description": "Tag for the returned entry",
    "schema": {"type": "string"},
}


def _is_etag_enabled():
    """Return True if ETag feature enabled application-wise"""
    return not current_app.config.get("ETAG_DISABLED", False)


def _get_etag_ctx():
    """Get ETag section of AppContext"""
    return get_appcontext().setdefault("etag", {})


class EtagMixin:
    """Extend Blueprint to add ETag handling"""

    METHODS_CHECKING_NOT_MODIFIED = ["GET", "HEAD"]
    METHODS_NEEDING_CHECK_ETAG = ["PUT", "PATCH", "DELETE"]
    METHODS_ALLOWING_SET_ETAG = ["GET", "HEAD", "POST", "PUT", "PATCH"]

    # Headers to include in ETag computation
    ETAG_INCLUDE_HEADERS = ["X-Pagination"]

    def etag(self, etag_schema=None):
        """Decorator generating an endpoint response

        :param etag_schema: :class:`Schema <marshmallow.Schema>` class
            or instance. If not None, will be used to serialize etag data.

        Can be used as either a decorator or a decorator factory:

            Example: ::

                @blp.etag
                def view_func(...):
                    ...

                @blp.etag(EtagSchema)
                def view_func(...):
                    ...

        The ``etag`` decorator expects the decorated view function to return a
        ``Response`` object. It is the case if it is decorated with the
        ``response`` decorator.

        See :doc:`ETag <etag>`.
        """
        if etag_schema is None or isinstance(etag_schema, (type, Schema)):
            # Factory: @etag(), @etag(EtagSchema) or @etag(EtagSchema())
            view_func = None
            if isinstance(etag_schema, type):
                etag_schema = etag_schema()
        else:
            # Decorator: @etag
            view_func, etag_schema = etag_schema, None

        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):

                etag_enabled = _is_etag_enabled()

                if etag_enabled:
                    # Check etag precondition
                    self._check_precondition()
                    # Store etag_schema in AppContext
                    _get_etag_ctx()["etag_schema"] = etag_schema

                # Execute decorated function
                resp = func(*args, **kwargs)

                if etag_enabled:
                    # Verify check_etag was called in resource code if needed
                    self._verify_check_etag()
                    # Add etag value to response
                    self._set_etag_in_response(resp, etag_schema)

                return resp

            # Note function is decorated by etag in doc info
            # The deepcopy avoids modifying the wrapped function doc
            wrapper._apidoc = deepcopy(getattr(wrapper, "_apidoc", {}))
            wrapper._apidoc["etag"] = True

            return wrapper

        if view_func:
            return decorator(view_func)
        return decorator

    @staticmethod
    def _generate_etag(etag_data, etag_schema=None, extra_data=None):
        """Generate an ETag from data

        etag_data: Data to use to compute ETag (must be json serializable)
        etag_schema: Schema to dump data with before hashing
        extra_data: Extra data to add before hashing

        Typically, extra_data is used to add pagination metadata to the hash.
        It is not dumped through the Schema.
        """
        if etag_schema is None:
            raw_data = etag_data
        else:
            if isinstance(etag_schema, type):
                etag_schema = etag_schema()
            raw_data = etag_schema.dump(etag_data)
        if extra_data:
            raw_data = (raw_data, extra_data)
        data = json.dumps(raw_data, sort_keys=True)
        return hashlib.sha1(bytes(data, "utf-8")).hexdigest()

    def _check_precondition(self):
        """Check If-Match header is there

        Raise 428 if If-Match header missing

        Called automatically for PUT, PATCH and DELETE methods
        """
        # TODO: other methods?
        # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/If-Match
        if request.method in self.METHODS_NEEDING_CHECK_ETAG and not request.if_match:
            raise PreconditionRequired

    def check_etag(self, etag_data, etag_schema=None):
        """Compare If-Match header with computed ETag

        Raise 412 if If-Match header does not match.

        Must be called from resource code to check ETag.

        Unfortunately, there is no way to call it automatically. It is the
        developer's responsability to do it. However, a warning is issued at
        runtime if this function was not called.

        Issues a warning if called in a method other than PUT, PATCH, or
        DELETE.
        """
        if request.method not in self.METHODS_NEEDING_CHECK_ETAG:
            warnings.warn(f"ETag cannot be checked on {request.method} request.")
        if _is_etag_enabled():
            etag_schema = etag_schema or _get_etag_ctx().get("etag_schema")
            new_etag = self._generate_etag(etag_data, etag_schema)
            _get_etag_ctx()["etag_checked"] = True
            if new_etag not in request.if_match:
                raise PreconditionFailed

    def _verify_check_etag(self):
        """Verify check_etag was called in resource code

        Issues a warning if ETag is enabled but check_etag was not called in
        resource code in a PUT, PATCH or DELETE method.

        This is called automatically. It is meant to warn the developer about
        an issue in his ETag management.
        """
        if request.method in self.METHODS_NEEDING_CHECK_ETAG:
            if not _get_etag_ctx().get("etag_checked"):
                warnings.warn(
                    "ETag not checked in endpoint {} on {} request.".format(
                        request.endpoint, request.method
                    )
                )

    def _check_not_modified(self, etag):
        """Raise NotModified if etag is in If-None-Match header

        Only applies to methods returning a 304 (Not Modified) code
        """
        if (
            request.method in self.METHODS_CHECKING_NOT_MODIFIED
            and etag in request.if_none_match
        ):
            raise NotModified

    def set_etag(self, etag_data, etag_schema=None):
        """Set ETag for this response

        Raise 304 if ETag identical to If-None-Match header

        Must be called from resource code, unless the view function is
        decorated with the ``response`` decorator, in which case the ETag is
        computed by default from response data if ``set_etag`` is not called.

        Issues a warning if called in a method other than GET, HEAD, POST, PUT
        or PATCH.
        """
        if request.method not in self.METHODS_ALLOWING_SET_ETAG:
            warnings.warn(f"ETag cannot be set on {request.method} request.")
        if _is_etag_enabled():
            etag_schema = etag_schema or _get_etag_ctx().get("etag_schema")
            new_etag = self._generate_etag(etag_data, etag_schema)
            self._check_not_modified(new_etag)
            # Store ETag in AppContext to add it to response headers later on
            _get_etag_ctx()["etag"] = new_etag

    def _set_etag_in_response(self, response, etag_schema):
        """Set ETag in response object

        Called automatically.

        If no ETag data was computed using set_etag, it is computed here from
        response data.
        """
        if request.method in self.METHODS_ALLOWING_SET_ETAG:
            new_etag = _get_etag_ctx().get("etag")
            # If no ETag data was manually provided, use response content
            if new_etag is None:
                # If etag_schema is provided, use raw result rather than
                # the dump, as the dump needs to be done using etag_schema
                etag_data = get_appcontext()[
                    "result_dump" if etag_schema is None else "result_raw"
                ]
                extra_data = tuple(
                    (k, v)
                    for k, v in response.headers
                    if k in self.ETAG_INCLUDE_HEADERS
                )
                new_etag = self._generate_etag(etag_data, etag_schema, extra_data)
                self._check_not_modified(new_etag)
            response.set_etag(new_etag)

    def _prepare_etag_doc(self, doc, doc_info, *, app, spec, method, **kwargs):
        if doc_info.get("etag", False) and not app.config.get("ETAG_DISABLED", False):
            responses = {}
            method_u = method.upper()
            if method_u in self.METHODS_CHECKING_NOT_MODIFIED:
                responses[304] = http.HTTPStatus(304).name
                doc.setdefault("parameters", []).append("IF_NONE_MATCH")
            if method_u in self.METHODS_NEEDING_CHECK_ETAG:
                responses[412] = http.HTTPStatus(412).name
                responses[428] = http.HTTPStatus(428).name
                doc.setdefault("parameters", []).append("IF_MATCH")
            if method_u in self.METHODS_ALLOWING_SET_ETAG:
                success_status_codes = doc_info.get("success_status_codes", [])
                for success_status_code in success_status_codes:
                    doc["responses"][success_status_code].setdefault("headers", {})[
                        "ETag"
                    ] = (ETAG_HEADER if spec.openapi_version.major < 3 else "ETAG")

            if responses:
                doc = deepupdate(doc, {"responses": responses})
        return doc
