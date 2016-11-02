# -*- coding: utf-8 -*-
"""API Blueprint

This is a subclass of Flask's Blueprint

It provides added features:

- Decorators to specify Marshmallow schema for view functions I/O

- API documentation registration

Documentation process works in several steps:

- At import time

  - When a MethodView or a function is decorated, relevant information
    is added to the object's `__apispec__` attribute.

  - The `route` decorator registers the endpoint in the Blueprint and gathers
    all information about the endpoint in `Blueprint.__docs__[endpoint]`

- At initialization time

  - Schema instances are replaced either by their reference in the `definition`
    section of the spec if applicable, otherwise by their json representation.

  - Endpoints documentation is registered in the APISpec object
"""

from copy import deepcopy

from flask import Blueprint as FlaskBlueprint
from flask.views import MethodViewType

from .utils import deepupdate
import webargs.flaskparser as wfp
from apispec.ext.marshmallow.swagger import schema2parameters

from .marshal import marshal_with
from .exceptions import EndpointMethodDocAlreadyRegisted


class Blueprint(FlaskBlueprint):
    """Blueprint that registers info in API documentation"""

    def __init__(self, *args, **kwargs):

        self.description = kwargs.pop('description', '')

        super().__init__(*args, **kwargs)

        # __docs__ is a dict storing endpoints documentation
        # {endpoint: {
        #     'get': documentation,
        #     'post': documentation,
        #     ...
        #     }
        # }
        self.__docs__ = {}

    def _store_endpoint_docs(self, endpoint, obj, **kwargs):
        """Store view or function doc info"""

        endpoint_doc = self.__docs__.setdefault(endpoint, {})

        def store_method_docs(method, function):
            doc = getattr(function, '__apidoc__', {})
            # Tag the function with the resource name
            doc.update({"tags": [self.name]})
            # Add function doc to table for later registration
            method_l = method.lower()
            if method_l in endpoint_doc:
                raise EndpointMethodDocAlreadyRegisted(
                    'Method {} already registered for endpoint {}'.format(
                        method_l, endpoint))
            endpoint_doc[method_l] = doc

        # MethodView (class)
        if isinstance(obj, MethodViewType):
            for method in obj.methods:
                func = getattr(obj, method.lower())
                store_method_docs(method, func)
        # Function
        else:
            methods = kwargs.pop('methods', None) or ['GET']
            for method in methods:
                store_method_docs(method, obj)

    def register_views_in_doc(self, app, spec):
        """Register views information in documentation

        If a schema in a parameter (or a response) appears in the spec
        `definitions` section, it is replace by a reference to its definition
        in the parameter (or response) documentation:

        "schema":{"$ref": "#/definitions/MySchema"}
        """

        for endpoint, doc in self.__docs__.items():

            endpoint = '.'.join((self.name, endpoint))

            # Modifying doc in place causes troubles if this method is
            # called twice. Typically, during tests, because modules are
            # imported once but initialized once before each test.
            doc = deepcopy(doc)

            # doc is a dict of documentation per method for the endpoint
            # {'get': documentation, 'post': documentation,...}

            # Process parameters: resolve schema reference
            # or convert schema in json description
            for apidoc in doc.values():
                params = apidoc.get('parameters', None)
                if params:
                    # use_args only register schema as parameters
                    # so there's no need to check
                    params = schema2parameters(
                        params['schema'],
                        spec=spec,
                        required=params['required'],
                        default_in=params['location'])
                    apidoc['parameters'] = params

            spec.add_path(
                app=app,
                endpoint=endpoint,
                operations=doc
            )

    def route(self, url, endpoint=None, **kwargs):
        """Decorator to register url rule in application

        Also stores doc info for later registration

        Use this to decorate a MethodView or a resource function
        """

        def wrapper(wrapped):

            # By default, endpoint for User is 'user'
            _endpoint = endpoint or wrapped.__name__.lower()

            # MethodView (class)
            if isinstance(wrapped, MethodViewType):
                self.add_url_rule(
                    url,
                    view_func=wrapped.as_view(_endpoint))
                self._store_endpoint_docs(_endpoint, wrapped)

            # Function
            else:
                self.add_url_rule(url, endpoint, wrapped, **kwargs)
                self._store_endpoint_docs(_endpoint, wrapped, **kwargs)

        return wrapper

    def doc(self, **kwargs):
        """Decorator allowing to pass description attributes

        For instance: summary,...
        """

        def decorator(func):

            func.__apidoc__ = deepupdate(
                getattr(func, '__apidoc__', {}), kwargs)

            return func

        return decorator

    def use_args(self, schema, **kwargs):
        """Decorator specifying the schema used as parameter"""

        def decorator(func):

            location = kwargs.pop('location', 'json')
            required = kwargs.pop('required', False)

            # Call webargs' use_args
            func = wfp.use_args(schema(), locations=[location], **kwargs)(func)

            # XXX: this sucks
            if location == 'json':
                location = 'body'

            # At this stage, dump schema and parameters in doc dictionary
            # schema instance will be later replaced by ref or json
            doc = {'parameters': {
                'location': location,
                'required': required,
                'schema': schema,
            }}
            func.__apidoc__ = deepupdate(getattr(func, '__apidoc__', {}), doc)

            return func

        return decorator

    def marshal_with(
            self, schema=None, code=200, paginate_with=None, description=''):
        """Decorator specifying the schema to use for serialization.

        :param schema: :class:`Schema <marshmallow.Schema>` class or instance,
            or `None`
        :param int code: HTTP status code (default 200)
        :param str payload: Key name of data returned
        :param Page paginate_with: Page class to paginate results with

        Page can be a Page object as defined in 'paginate' library. But it
        does not have to, as long as it provides the following subset of
        attributes from Page:
          - items: items in page (list/generator)
          - page: current page number (starting at 1)
          - items_per_page: number of items per page
          - page_count: number of pages
          - item_count: total number of items
        """

        def wrapper(func):

            # Add schema as response in the API doc
            doc = {'responses': {code: {'description': description}}}
            if schema:
                if paginate_with is not None:
                    # Pagination -> we're returning a list
                    doc['responses'][code]['schema'] = {
                        'type': 'array',
                        'items': schema
                    }
                else:
                    doc['responses'][code]['schema'] = schema
            func.__apidoc__ = deepupdate(getattr(func, '__apidoc__', {}), doc)

            return marshal_with(
                schema=schema, code=code, paginate_with=paginate_with)(func)
        return wrapper
