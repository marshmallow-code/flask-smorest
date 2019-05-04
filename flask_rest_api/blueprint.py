"""API Blueprint

This is a subclass of Flask's Blueprint

It provides added features:

- Decorators to specify Marshmallow schema for view functions I/O

- API documentation registration

Documentation process works in several steps:

- At import time

  - When a MethodView or a view function is decorated, relevant information
    is automatically added to the object's ``_apidoc`` attribute.

  - The ``Blueprint.doc`` decorator stores additional information in a separate
    ``_api_manual_doc``. It allows the user to specify documentation
    information that flask-rest-api can not - or does not yet - infer from the
    code.

  - The ``Blueprint.route`` decorator registers the endpoint in the Blueprint
    and gathers all information about the endpoint in
    ``Blueprint._auto_docs[endpoint]`` and
    ``Blueprint._manual_docs[endpoint]``.

- At initialization time

  - Schema instances are replaced either by their reference in the `schemas`
    section of the spec if applicable, otherwise by their json representation.

  - Automatic documentation is adapted to OpenAPI version and deep-merged with
    manual documentation.

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
        self._auto_docs = OrderedDict()
        self._manual_docs = OrderedDict()
        self._endpoints = []

    def route(self, rule, **options):
        """Decorator to register url rule in application

        Also stores doc info for later registration

        Use this to decorate a :class:`MethodView <flask.views.MethodView>` or
        a resource function
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
            self._store_endpoint_docs(endpoint, func, **options)

            return func

        return decorator

    def _store_endpoint_docs(self, endpoint, obj, **kwargs):
        """Store view or function doc info"""

        endpoint_auto_doc = self._auto_docs.setdefault(
            endpoint, OrderedDict())
        endpoint_manual_doc = self._manual_docs.setdefault(
            endpoint, OrderedDict())

        def store_method_docs(method, function):
            """Add auto and manual doc to table for later registration"""
            # Get summary/description from docstring
            # and auto documentation from decorators
            # Get manual documentation from @doc decorator
            docstring = function.__doc__
            auto_doc = load_info_from_docstring(docstring) if docstring else {}
            auto_doc.update(getattr(function, '_apidoc', {}))
            manual_doc = getattr(function, '_api_manual_doc', {})
            # Store function auto and manual docs for later registration
            method_l = method.lower()
            endpoint_auto_doc[method_l] = auto_doc
            endpoint_manual_doc[method_l] = manual_doc

        # MethodView (class)
        if isinstance(obj, MethodViewType):
            for method in self.HTTP_METHODS:
                if method in obj.methods:
                    func = getattr(obj, method.lower())
                    store_method_docs(method, func)
        # Function
        else:
            methods = kwargs.pop('methods', None) or ['GET']
            for method in methods:
                store_method_docs(method, obj)

    def register_views_in_doc(self, app, spec):
        """Register views information in documentation

        If a schema in a parameter or a response appears in the spec
        `schemas` section, it is replaced by a reference in the parameter or
        response documentation:

        "schema":{"$ref": "#/components/schemas/MySchema"}
        """
        # This method uses the documentation information associated with each
        # endpoint in self._[auto|manual]_docs to provide documentation for
        # corresponding route to the spec object.
        for endpoint, endpoint_auto_doc in self._auto_docs.items():
            doc = OrderedDict()
            for key, auto_doc in endpoint_auto_doc.items():
                # Deepcopy to avoid mutating the source
                # Allows calling this function twice
                endpoint_doc = deepcopy(auto_doc)
                # Format operations documentation in OpenAPI structure
                self._prepare_doc(endpoint_doc, spec.openapi_version)
                # Tag all operations with Blueprint name
                endpoint_doc['tags'] = [self.name]
                # Merge auto_doc and manual_doc into doc
                manual_doc = self._manual_docs[endpoint][key]
                doc[key] = deepupdate(endpoint_doc, manual_doc)

            # Thanks to self.route, there can only be one rule per endpoint
            full_endpoint = '.'.join((self.name, endpoint))
            rule = next(app.url_map.iter_rules(full_endpoint))
            spec.path(rule=rule, operations=doc)

    @staticmethod
    def _prepare_doc(operation, openapi_version):
        """Format operation documentation in OpenAPI structure

        The decorators store all documentation information in a dict structure
        that is close to OpenAPI doc structure, so this information could
        _almost_ be copied as is. Yet, some adjustemnts may have to be
        performed, especially if the spec structure differs between OpenAPI
        versions: the OpenAPI version is not known when the decorators are
        applied but only at registration time when this method is called.
        """
        if openapi_version.major < 3:
            if 'responses' in operation:
                for resp in operation['responses'].values():
                    if 'example' in resp:
                        resp['examples'] = {
                            'application/json': resp.pop('example')}
        else:
            if 'responses' in operation:
                for resp in operation['responses'].values():
                    for field in ('schema', 'example', 'examples'):
                        if field in resp:
                            (
                                resp
                                .setdefault('content', {})
                                .setdefault('application/json', {})
                                [field]
                            ) = resp.pop(field)
            if 'parameters' in operation:
                for param in operation['parameters']:
                    if param['in'] == 'body':
                        request_body = {
                            x: param[x] for x in ('description', 'required')
                            if x in param
                        }
                        for field in ('schema', 'example', 'examples'):
                            if field in param:
                                (
                                    request_body
                                    .setdefault('content', {})
                                    .setdefault('application/json', {})
                                    [field]
                                ) = param.pop(field)
                        operation['requestBody'] = request_body
                        # There can be only one requestBody
                        continue
                parameters = [
                    param for param in operation['parameters']
                    if not param['in'] == 'body'
                ]
                if parameters:
                    operation['parameters'] = parameters
                else:
                    del operation['parameters']

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

            # Don't merge manual doc with auto-documentation right now.
            # Store it in a separate attribute to merge it later.
            # The deepcopy avoids modifying the wrapped function doc
            wrapper._api_manual_doc = deepupdate(
                deepcopy(getattr(wrapper, '_api_manual_doc', {})), kwargs)
            return wrapper

        return decorator
