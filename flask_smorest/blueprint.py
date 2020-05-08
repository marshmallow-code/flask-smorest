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

  - Documentation is finalized using the information stored in
    ``Blueprint._docs``, with adaptations to parameters only known at init
    time, such as OAS version.

  - Manual documentation is deep-merged with automatic documentation.

  - Endpoints documentation is registered in the APISpec object.
"""

from collections import OrderedDict
from functools import wraps
from copy import deepcopy

from flask import Blueprint as FlaskBlueprint
from flask.views import MethodViewType

from .utils import deepupdate, load_info_from_docstring
from .arguments import ArgumentsMixin
from .response import ResponseMixin
from .pagination import PaginationMixin
from .etag import EtagMixin


class Blueprint(
        FlaskBlueprint,
        ArgumentsMixin, ResponseMixin, PaginationMixin, EtagMixin):
    """Blueprint that registers info in API documentation"""

    # Order in which the methods are presented in the spec
    HTTP_METHODS = ['OPTIONS', 'HEAD', 'GET', 'POST', 'PUT', 'PATCH', 'DELETE']

    DEFAULT_LOCATION_CONTENT_TYPE_MAPPING = {
        "json": "application/json",
        "form": "application/x-www-form-urlencoded",
        "files": "multipart/form-data",
    }

    DOCSTRING_INFO_DELIMITER = "---"

    def __init__(self, *args, **kwargs):

        self.description = kwargs.pop('description', '')

        super().__init__(*args, **kwargs)

        # _[manual|auto]_docs are ordered dicts storing endpoints documentation
        # {
        #     endpoint: {
        #         'get': documentation,
        #         'post': documentation,
        #         ...
        #     },
        #     ...
        # }
        self._docs = OrderedDict()
        self._endpoints = []
        self._prepare_doc_cbks = [
            self._prepare_arguments_doc,
            self._prepare_response_doc,
            self._prepare_pagination_doc,
            self._prepare_etag_doc,
        ]

    def route(self, rule, *, parameters=None, **options):
        """Decorator to register url rule in application

        Also stores doc info for later registration

        Use this to decorate a :class:`MethodView <flask.views.MethodView>` or
        a resource function.

        :param str rule: URL rule as string.
        :param str endpoint: Endpoint for the registered URL rule (defaults
            to function name).
        :param list parameters: List of parameters relevant to all operations
            in this path, only used to document the resource.
        :param dict options: Options to be forwarded to the underlying
            :class:`werkzeug.routing.Rule <Rule>` object.
        """
        def decorator(func):

            # By default, endpoint name is function name
            endpoint = options.pop('endpoint', func.__name__)

            # Prevent registering several times the same endpoint
            # by silently renaming the endpoint in case of collision
            if endpoint in self._endpoints:
                endpoint = '{}_{}'.format(endpoint, len(self._endpoints))
            self._endpoints.append(endpoint)

            if isinstance(func, MethodViewType):
                view_func = func.as_view(endpoint)
            else:
                view_func = func

            # Add URL rule in Flask and store endpoint documentation
            self.add_url_rule(rule, endpoint, view_func, **options)
            self._store_endpoint_docs(endpoint, func, parameters, **options)

            return func

        return decorator

    def _store_endpoint_docs(self, endpoint, obj, parameters, **options):
        """Store view or function doc info"""

        endpoint_doc_info = self._docs.setdefault(endpoint, OrderedDict())

        def store_method_docs(method, function):
            """Add auto and manual doc to table for later registration"""
            # Get documentation from decorators
            # Deepcopy doc info as it may be used for several methods and it
            # may be mutated in apispec
            doc = deepcopy(getattr(function, '_apidoc', {}))
            # Get summary/description from docstring
            doc['docstring'] = load_info_from_docstring(
                function.__doc__, delimiter=self.DOCSTRING_INFO_DELIMITER)
            # Store function doc infos for later processing/registration
            endpoint_doc_info[method.lower()] = doc

        # MethodView (class)
        if isinstance(obj, MethodViewType):
            for method in self.HTTP_METHODS:
                if method in obj.methods:
                    func = getattr(obj, method.lower())
                    store_method_docs(method, func)
        # Function
        else:
            methods = options.pop('methods', None) or ['GET']
            for method in methods:
                store_method_docs(method, obj)

        # Store parameters doc info from route decorator
        endpoint_doc_info['parameters'] = parameters

    def register_views_in_doc(self, app, spec):
        """Register views information in documentation

        If a schema in a parameter or a response appears in the spec
        `schemas` section, it is replaced by a reference in the parameter or
        response documentation:

        "schema":{"$ref": "#/components/schemas/MySchema"}
        """
        # This method uses the documentation information associated with each
        # endpoint in self._docs to provide documentation for corresponding
        # route to the spec object.
        # Deepcopy to avoid mutating the source. Allows registering blueprint
        # multiple times (e.g. when creating multiple apps during tests).
        for endpoint, endpoint_doc_info in deepcopy(self._docs).items():
            parameters = endpoint_doc_info.pop('parameters')
            doc = OrderedDict()
            # Use doc info stored by decorators to generate doc
            for method_l, operation_doc_info in endpoint_doc_info.items():
                operation_doc = {}
                for func in self._prepare_doc_cbks:
                    operation_doc = func(
                        operation_doc,
                        operation_doc_info,
                        app=app,
                        spec=spec,
                        method=method_l
                    )
                operation_doc.update(operation_doc_info['docstring'])
                # Tag all operations with Blueprint name
                operation_doc['tags'] = [self.name]
                # Complete doc with manual doc info
                manual_doc = operation_doc_info.get('manual_doc', {})
                doc[method_l] = deepupdate(operation_doc, manual_doc)

            # Thanks to self.route, there can only be one rule per endpoint
            full_endpoint = '.'.join((self.name, endpoint))
            rule = next(app.url_map.iter_rules(full_endpoint))
            spec.path(rule=rule, operations=doc, parameters=parameters)

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
            wrapper._apidoc = deepcopy(getattr(wrapper, '_apidoc', {}))
            wrapper._apidoc['manual_doc'] = deepupdate(
                deepcopy(wrapper._apidoc.get('manual_doc', {})), kwargs)
            return wrapper

        return decorator
