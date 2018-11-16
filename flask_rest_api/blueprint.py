"""API Blueprint

This is a subclass of Flask's Blueprint

It provides added features:

- Decorators to specify Marshmallow schema for view functions I/O

- API documentation registration

Documentation process works in several steps:

- At import time

  - When a MethodView or a function is decorated, relevant information
    is added to the object's `_apispec` attribute.

  - The `route` decorator registers the endpoint in the Blueprint and gathers
    all information about the endpoint in `Blueprint._docs[endpoint]`

- At initialization time

  - Schema instances are replaced either by their reference in the `definition`
    section of the spec if applicable, otherwise by their json representation.

  - Endpoints documentation is registered in the APISpec object
"""

from collections import OrderedDict

from flask import Blueprint as FlaskBlueprint
from flask.views import MethodViewType

from .utils import deepupdate, load_info_from_docstring
from .arguments import ArgumentsMixin
from .response import ResponseMixin
from .pagination import PaginationMixin
from .etag import EtagMixin
from .compat import APISPEC_VERSION_MAJOR


# This is the order in which the methods are presented in the spec
HTTP_METHODS = [
    'OPTIONS', 'HEAD', 'GET', 'POST', 'PUT', 'PATCH', 'DELETE']


class Blueprint(
        FlaskBlueprint,
        ArgumentsMixin, ResponseMixin, PaginationMixin, EtagMixin):
    """Blueprint that registers info in API documentation"""

    def __init__(self, *args, **kwargs):

        self.description = kwargs.pop('description', '')

        super().__init__(*args, **kwargs)

        # _docs is an ordered dict storing endpoints documentation:
        # {endpoint: {
        #     'get': documentation,
        #     'post': documentation,
        #     ...
        #     }
        # }
        self._docs = OrderedDict()
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

        endpoint_doc = self._docs.setdefault(endpoint, OrderedDict())

        def store_method_docs(method, function):
            # Get summary/description from docstring
            docstring = function.__doc__
            doc = load_info_from_docstring(docstring) if docstring else {}
            # Update doc with description from @doc decorator
            doc.update(getattr(function, '_apidoc', {}))
            # Add function doc to table for later registration
            endpoint_doc[method.lower()] = doc

        # MethodView (class)
        if isinstance(obj, MethodViewType):
            for method in HTTP_METHODS:
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
        `definitions` section, it is replaced by a reference to its definition
        in the parameter or response documentation:

        "schema":{"$ref": "#/definitions/MySchema"}
        """
        # This method uses the documentation information associated with the
        # endpoint (in self._docs) to provide documentation for the route to
        # the spec object.
        for endpoint, doc in self._docs.items():
            # doc is a dict of documentation per method for the endpoint
            # {'get': documentation, 'post': documentation,...}

            # Prepend Blueprint name to endpoint
            endpoint = '.'.join((self.name, endpoint))

            # Tag all operations with Blueprint name
            # Format operations documentation in OpenAPI structure
            for operation in doc.values():
                operation['tags'] = [self.name]
                self._prepare_doc(operation, spec.openapi_version)

            # Thanks to self.route, there can only be one rule per endpoint
            rule = next(app.url_map.iter_rules(endpoint))
            if APISPEC_VERSION_MAJOR < 1:
                spec.add_path(rule=rule, operations=doc)
            else:
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
        if openapi_version.major >= 3:
            if 'responses' in operation:
                for resp in operation['responses'].values():
                    if 'schema' in resp:
                        resp['content'] = {
                            'application/json': {
                                'schema': resp.pop('schema')}}
            if 'parameters' in operation:
                for param in operation['parameters']:
                    if param['in'] == 'body':
                        request_body = {
                            **{
                                'content': {
                                    'application/json': {
                                        'schema': param['schema']
                                    }
                                }
                            },
                            **{
                                x: param[x]
                                for x in ('description', 'required')
                                if x in param
                            }
                        }
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
            func._apidoc = deepupdate(getattr(func, '_apidoc', {}), kwargs)
            return func
        return decorator
