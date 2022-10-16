"""API Blueprint

This is a subclass of Flask's Blueprint

It provides added features:

- Decorators to specify Marshmallow schema for view functions I/O

- API documentation registration

Documentation process works in several steps:

- At import time

  - When a MethodView or a view function is decorated, relevant information
    is automatically added to the object's ``_apidoc`` attribute.

  - The ``Blueprint.doc`` decorator stores additional information in there that
    flask-smorest can not - or does not yet - infer from the code.

  - The ``Blueprint.route`` decorator registers the endpoint in the Blueprint
    and gathers all documentation information about the endpoint in
    ``Blueprint._docs[endpoint]``.

- At initialization time

  - Schema instances are replaced by their reference in the `schemas` section
    of the spec components.

  - The ``Blueprint.register_blueprint`` method merges nested blueprint
    documentation into the parent blueprint documentation.

  - Documentation is finalized using the information stored in
    ``Blueprint._docs``, with adaptations to parameters only known at init
    time, such as OAS version.

  - Manual documentation is deep-merged with automatic documentation.

  - Endpoints documentation is registered in the APISpec object.
"""

from functools import wraps
from copy import deepcopy

from flask import Blueprint as FlaskBlueprint
from flask.views import MethodView

from .utils import deepupdate, load_info_from_docstring
from .arguments import ArgumentsMixin
from .response import ResponseMixin
from .pagination import PaginationMixin
from .etag import EtagMixin


class Blueprint(
    FlaskBlueprint, ArgumentsMixin, ResponseMixin, PaginationMixin, EtagMixin
):
    """Blueprint that registers info in API documentation"""

    # Order in which the methods are presented in the spec
    HTTP_METHODS = ["OPTIONS", "HEAD", "GET", "POST", "PUT", "PATCH", "DELETE"]

    DEFAULT_LOCATION_CONTENT_TYPE_MAPPING = {
        "json": "application/json",
        "form": "application/x-www-form-urlencoded",
        "files": "multipart/form-data",
    }

    DOCSTRING_INFO_DELIMITER = "---"

    def __init__(self, *args, **kwargs):

        self.description = kwargs.pop("description", "")

        super().__init__(*args, **kwargs)

        # _docs stores information used at init time to produce documentation.
        # For each endpoint, for each method, each feature stores info in there
        # to be is used by a dedicated _prepare_*_doc callback. An extra
        # "parameters" entry is added to store common route parameters doc.
        # {
        #     endpoint: {
        #         'parameters: [list of common route parameters],
        #         'get': {
        #             'response': { info used by response decorator to produce doc},
        #             'argument': { info used by arguments decorator to produce doc},
        #             ...
        #         'post': ...,
        #         ...
        #     },
        #     ...
        # }
        self._docs = {}
        self._endpoints = []
        self._prepare_doc_cbks = [
            self._prepare_arguments_doc,
            self._prepare_response_doc,
            self._prepare_pagination_doc,
            self._prepare_etag_doc,
        ]

    def add_url_rule(
        self,
        rule,
        endpoint=None,
        view_func=None,
        provide_automatic_options=None,
        *,
        parameters=None,
        tags=None,
        **options,
    ):
        """Register url rule in application

        Also stores doc info for later registration

        Use this to register a :class:`MethodView <flask.views.MethodView>` or
        a resource function.

        :param str rule: URL rule as string.
        :param str endpoint: Endpoint for the registered URL rule (defaults
            to function name).
        :param callable|MethodView view_func: View function or MethodView class
        :param list parameters: List of parameter descriptions relevant to all
            operations in this path. Only used to document the resource.
        :param list tags: List of tags for the resource.
            If None, ``Blueprint`` name is used.
        :param options: Options to be forwarded to the underlying
            :class:`werkzeug.routing.Rule <Rule>` object.
        """
        if view_func is None:
            raise TypeError("view_func must be provided")

        if endpoint is None:
            endpoint = view_func.__name__

        # Ensure endpoint name is unique
        # - to avoid a name clash when registering a MethodView
        # - to use it as a key internally in endpoint -> doc mapping
        if endpoint in self._endpoints:
            endpoint = f"{endpoint}_{len(self._endpoints)}"
        self._endpoints.append(endpoint)

        if isinstance(view_func, type(MethodView)):
            func = view_func.as_view(endpoint)
        else:
            func = view_func

        # Add URL rule in Flask and store endpoint documentation
        super().add_url_rule(rule, endpoint, func, **options)
        self._store_endpoint_docs(endpoint, view_func, parameters, tags, **options)

    def route(self, rule, *, parameters=None, tags=None, **options):
        """Decorator to register view function in application and documentation

        Calls :meth:`add_url_rule <Blueprint.add_url_rule>`.
        """

        def decorator(func):
            endpoint = options.pop("endpoint", None)
            self.add_url_rule(
                rule, endpoint, func, parameters=parameters, tags=tags, **options
            )
            return func

        return decorator

    def register_blueprint(self, blueprint, **options):
        """Register a nested blueprint in application

        Also stores doc info from the nested bluepint for later registration.

        Use this to register a nested :class:`Blueprint <Blueprint>`.

        :param Blueprint blueprint: Blueprint to register under this blueprint.
        :param options: Options to be forwarded to the underlying
            :meth:`flask.Blueprint.register_blueprint` method.

        See :ref:`register-nested-blueprints`.
        """
        blp_name = options.get("name", blueprint.name)

        # Inherit all endpoints
        self._docs.update(
            {
                ".".join((blp_name, endpoint_name)): doc
                for endpoint_name, doc in blueprint._docs.items()
            }
        )

        return super().register_blueprint(blueprint, **options)

    def _store_endpoint_docs(self, endpoint, obj, parameters, tags, **options):
        """Store view or function doc info"""

        endpoint_doc_info = self._docs.setdefault(endpoint, {})

        def store_method_docs(method, function):
            """Add auto and manual doc to table for later registration"""
            # Get documentation from decorators
            # Deepcopy doc info as it may be used for several methods and it
            # may be mutated in apispec
            doc = deepcopy(getattr(function, "_apidoc", {}))
            # Get summary/description from docstring
            doc["docstring"] = load_info_from_docstring(
                function.__doc__, delimiter=self.DOCSTRING_INFO_DELIMITER
            )
            # Tags for this resource
            doc["tags"] = tags
            # Store function doc infos for later processing/registration
            endpoint_doc_info[method.lower()] = doc

        # MethodView (class)
        if isinstance(obj, type(MethodView)):
            for method in self.HTTP_METHODS:
                if method in obj.methods:
                    if "methods" not in options or method in options["methods"]:
                        func = getattr(obj, method.lower())
                        store_method_docs(method, func)
        # Function
        else:
            for method in self.HTTP_METHODS:
                if method in options.get("methods", ("GET",)):
                    store_method_docs(method, obj)

        # Store parameters doc info from route decorator
        endpoint_doc_info["parameters"] = parameters

    def register_views_in_doc(self, api, app, spec, *, name, parameters):
        """Register views information in documentation

        If a schema in a parameter or a response appears in the spec
        `schemas` section, it is replaced by a reference in the parameter or
        response documentation:

        "schema":{"$ref": "#/components/schemas/MySchema"}
        """
        url_prefix_parameters = parameters or []

        # This method uses the documentation information associated with each
        # endpoint in self._docs to provide documentation for corresponding
        # route to the spec object.
        # Deepcopy to avoid mutating the source. Allows registering blueprint
        # multiple times (e.g. when creating multiple apps during tests).
        for endpoint, endpoint_doc_info in deepcopy(self._docs).items():
            endpoint_route_parameters = endpoint_doc_info.pop("parameters") or []
            endpoint_parameters = url_prefix_parameters + endpoint_route_parameters
            doc = {}
            # Use doc info stored by decorators to generate doc
            for method_l, operation_doc_info in endpoint_doc_info.items():
                tags = operation_doc_info.pop("tags")
                operation_doc = {}
                for func in self._prepare_doc_cbks:
                    operation_doc = func(
                        operation_doc,
                        operation_doc_info,
                        api=api,
                        app=app,
                        spec=spec,
                        method=method_l,
                    )
                operation_doc.update(operation_doc_info["docstring"])
                # Tag all operations with Blueprint name unless tags specified
                operation_doc["tags"] = (
                    tags
                    if tags is not None
                    else [
                        name,
                    ]
                )
                # Complete doc with manual doc info
                manual_doc = operation_doc_info.get("manual_doc", {})
                doc[method_l] = deepupdate(operation_doc, manual_doc)

            # Thanks to self.route, there can only be one rule per endpoint
            full_endpoint = ".".join((name, endpoint))
            rule = next(app.url_map.iter_rules(full_endpoint))
            spec.path(rule=rule, operations=doc, parameters=endpoint_parameters)

    @staticmethod
    def doc(**kwargs):
        """Decorator adding description attributes to a view function

        Values passed as kwargs are copied verbatim in the docs

            Example: ::

                @blp.doc(description="Return pets based on ID",
                         summary="Find pets by ID"
                )
                def get(...):
                    ...
        """

        def decorator(func):
            @wraps(func)
            def wrapper(*f_args, **f_kwargs):
                return func(*f_args, **f_kwargs)

            # The deepcopy avoids modifying the wrapped function doc
            wrapper._apidoc = deepcopy(getattr(wrapper, "_apidoc", {}))
            wrapper._apidoc["manual_doc"] = deepupdate(
                deepcopy(wrapper._apidoc.get("manual_doc", {})), kwargs
            )
            return wrapper

        return decorator

    def _decorate_view_func_or_method_view(self, decorator, obj):
        """Apply decorator to view func or MethodView HTTP methods"""

        # Decorating a MethodView decorates all HTTP methods
        if isinstance(obj, type(MethodView)):
            for method in self.HTTP_METHODS:
                if method in obj.methods:
                    method_l = method.lower()
                    func = getattr(obj, method_l)
                    setattr(obj, method_l, decorator(func))
            return obj

        return decorator(obj)
