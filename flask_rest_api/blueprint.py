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
from .spec import (
    DEFAULT_REQUEST_BODY_CONTENT_TYPE, DEFAULT_RESPONSE_CONTENT_TYPE)


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
        self._auto_docs = OrderedDict()
        self._manual_docs = OrderedDict()
        self._endpoints = []

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

        endpoint_auto_doc = self._auto_docs.setdefault(
            endpoint, OrderedDict())
        endpoint_manual_doc = self._manual_docs.setdefault(
            endpoint, OrderedDict())

        def store_method_docs(method, function):
            """Add auto and manual doc to table for later registration"""
            # Get auto documentation from decorators
            # and summary/description from docstring
            # Get manual documentation from @doc decorator
            auto_doc = getattr(function, '_apidoc', {})
            auto_doc.update(
                load_info_from_docstring(
                    function.__doc__,
                    delimiter=self.DOCSTRING_INFO_DELIMITER
                )
            )
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
            methods = options.pop('methods', None) or ['GET']
            for method in methods:
                store_method_docs(method, obj)

        endpoint_auto_doc['parameters'] = parameters

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
        # Deepcopy to avoid mutating the source
        # Allows registering blueprint multiple times (e.g. when creating
        # multiple apps during tests)
        auto_docs = deepcopy(self._auto_docs)
        for endpoint, endpoint_auto_doc in auto_docs.items():
            parameters = endpoint_auto_doc.pop('parameters')
            doc = OrderedDict()
            for method_l, endpoint_doc in endpoint_auto_doc.items():
                # Format operations documentation in OpenAPI structure
                self._prepare_doc(endpoint_doc, spec.openapi_version)
                # Tag all operations with Blueprint name
                endpoint_doc['tags'] = [self.name]
                # Merge auto_doc and manual_doc into doc
                manual_doc = self._manual_docs[endpoint][method_l]
                doc[method_l] = deepupdate(endpoint_doc, manual_doc)

            # Thanks to self.route, there can only be one rule per endpoint
            full_endpoint = '.'.join((self.name, endpoint))
            rule = next(app.url_map.iter_rules(full_endpoint))
            spec.path(rule=rule, operations=doc, parameters=parameters)

    def _prepare_doc(self, operation, openapi_version):
        """Format operation documentation in OpenAPI structure

        The decorators store all documentation information in a dict structure
        that is close to OpenAPI doc structure, so this information could
        _almost_ be copied as is. Yet, some adjustemnts may have to be
        performed, especially if the spec structure differs between OpenAPI
        versions: the OpenAPI version is not known when the decorators are
        applied but only at registration time when this method is called.
        """
        # OAS 2
        if openapi_version.major < 3:
            if 'responses' in operation:
                for resp in operation['responses'].values():
                    if 'example' in resp:
                        resp['examples'] = {
                            DEFAULT_RESPONSE_CONTENT_TYPE: resp.pop('example')}
            if 'parameters' in operation:
                for param in operation['parameters']:
                    if param['in'] in (
                            self.DEFAULT_LOCATION_CONTENT_TYPE_MAPPING
                    ):
                        content_type = (
                            param.pop('content_type', None) or
                            self.DEFAULT_LOCATION_CONTENT_TYPE_MAPPING[
                                param['in']]
                        )
                        if content_type != DEFAULT_REQUEST_BODY_CONTENT_TYPE:
                            operation['consumes'] = [content_type, ]
                        # body and formData are mutually exclusive
                        break
        # OAS 3
        else:
            if 'responses' in operation:
                for resp in operation['responses'].values():
                    for field in ('schema', 'example', 'examples'):
                        if field in resp:
                            (
                                resp
                                .setdefault('content', {})
                                .setdefault(DEFAULT_RESPONSE_CONTENT_TYPE, {})
                                [field]
                            ) = resp.pop(field)
            if 'parameters' in operation:
                for param in operation['parameters']:
                    if param['in'] in (
                            self.DEFAULT_LOCATION_CONTENT_TYPE_MAPPING
                    ):
                        request_body = {
                            x: param[x]
                            for x in ('description', 'required')
                            if x in param
                        }
                        fields = {
                            x: param.pop(x)
                            for x in ('schema', 'example', 'examples')
                            if x in param
                        }
                        content_type = (
                            param.pop('content_type', None) or
                            self.DEFAULT_LOCATION_CONTENT_TYPE_MAPPING[
                                param['in']]
                        )
                        request_body['content'] = {content_type: fields}
                        operation['requestBody'] = request_body
                        # There can be only one requestBody
                        operation['parameters'].remove(param)
                        if not operation['parameters']:
                            del operation['parameters']
                        break

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
