from flask_smorest import Api

from ..utils import deepupdate
from . import abc


class APIKeySecurityPlugin(abc.Plugin):
    def __init__(self, schema_name, parameter_name, in_="header") -> None:
        self._schema_name = schema_name
        self._parameter_name = parameter_name
        self._in = in_

    def security(self, keys):
        def decorator(func):
            func._apidoc = deepupdate(
                getattr(func, "_apidoc", {}), {"security": [{key: [] for key in keys}]}
            )
            return func

        return decorator

    def register_method_docs(self, doc, doc_info, *, api, spec, **kwargs):
        # No need to attempt to add "security" to doc if it is not in doc_info
        if "security" in doc_info:
            doc = deepupdate(doc, {"security": doc_info["security"]})
        return doc

    def visit_api(self, api: Api, **kwargs) -> None:
        """Visits the api and registers security objects"""
        api.spec.components.security_scheme(
            self._schema_name,
            {"type": "apiKey", "in": self._in, "name": self._parameter_name},
        )
