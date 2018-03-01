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

from copy import deepcopy

from flask import Blueprint as FlaskBlueprint
from flask.views import MethodViewType

from apispec.ext.marshmallow.swagger import schema2parameters

from .utils import deepupdate
from .args_parser import parser
from .response import response
from .exceptions import EndpointMethodDocAlreadyRegisted, InvalidLocation


# Map webargs locations to OpenAPI locations
LOCATION_MAP = {
    'querystring': 'query',
    'query': 'query',
    'json': 'body',
    'form': 'formData',
    'headers': 'header',
    'files': 'formData',
    # Unsupported in OpenAPI v2, uncomment for OpenAPI v3 support
    # 'cookies': cookie,
    # Unsupported: path params are managed in flask_path_helper
    # 'view_args': 'path',
}


class Blueprint(FlaskBlueprint):
    """Blueprint that registers info in API documentation"""

    def __init__(self, *args, **kwargs):

        self.description = kwargs.pop('description', '')

        super().__init__(*args, **kwargs)

        # _docs is a dict storing endpoints documentation:
        # {endpoint: {
        #     'get': documentation,
        #     'post': documentation,
        #     ...
        #     }
        # }
        self._docs = {}

    def _store_endpoint_docs(self, endpoint, obj, **kwargs):
        """Store view or function doc info"""

        endpoint_doc = self._docs.setdefault(endpoint, {})

        def store_method_docs(method, function):
            doc = getattr(function, '_apidoc', {})
            # Add function doc to table for later registration
            method_l = method.lower()
            # Check another doc was not already registed for endpoint/method
            if method_l in endpoint_doc and endpoint_doc[method_l] is not doc:
                # If multiple routes point to the same endpoint, the doc may
                # be already registered.
                # Only trigger exception if a different doc is passed.
                raise EndpointMethodDocAlreadyRegisted(
                    "Another doc is already registered for endpoint '{}' "
                    "method {}".format(endpoint, method_l.upper()))
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

        If a schema in a parameter or a response appears in the spec
        `definitions` section, it is replaced by a reference to its definition
        in the parameter or response documentation:

        "schema":{"$ref": "#/definitions/MySchema"}
        """

        for endpoint, doc in self._docs.items():

            endpoint = '.'.join((self.name, endpoint))

            # Modifying doc in place causes troubles if this method is
            # called twice. Typically, during tests, because modules are
            # imported once but initialized once before each test.
            doc = deepcopy(doc)

            # doc is a dict of documentation per method for the endpoint
            # {'get': documentation, 'post': documentation,...}

            # Tag the function with the resource name
            for method_l in doc.keys():
                doc[method_l].update({'tags': [self.name]})

            # Process parameters: resolve schema reference
            # or convert schema to json description
            for apidoc in doc.values():
                params = apidoc.get('parameters', None)
                if params:
                    # self.arguments can only register a Schema
                    # so there's no need to check if schema is in params
                    params = schema2parameters(
                        params['schema'],
                        spec=spec,
                        required=params['required'],
                        default_in=params['location'])
                    apidoc['parameters'] = params

            for rule in app.url_map.iter_rules(endpoint):
                # We need to deepcopy operations here as well
                # because it is modified in add_path, which causes
                # issues if there are multiple rules for the same endpoint
                spec.add_path(
                    app=app,
                    rule=rule,
                    operations=deepcopy(doc)
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
                # This decorator may be called multiple times on the same
                # MethodView, but Flask will complain if different views are
                # mapped to the same endpoint, so we should call 'as_view' only
                # once and keep the result in MethodView._view_func
                if not getattr(wrapped, '_view_func', None):
                    wrapped._view_func = wrapped.as_view(_endpoint)
                view_func = wrapped._view_func

            # Function
            else:
                view_func = wrapped

            # Add URL rule in Flask and store endpoint documentation
            self.add_url_rule(url, view_func=view_func, **kwargs)
            self._store_endpoint_docs(_endpoint, wrapped, **kwargs)

            return wrapped

        return wrapper

    def doc(self, **kwargs):
        """Decorator allowing to pass description attributes

        For instance: summary,...
        """

        def decorator(func):
            func._apidoc = deepupdate(getattr(func, '_apidoc', {}), kwargs)
            return func

        return decorator

    def arguments(self, schema, **kwargs):
        """Decorator specifying the schema used to deserialize parameters

        :param type|Schema schema: A marshmallow Schema class or instance.

        Can only be called once on a resource function.
        """

        if isinstance(schema, type):
            schema = schema()

        def decorator(func):

            location = kwargs.pop('location', 'json')
            required = kwargs.pop('required', False)

            # Call use_args (from webargs) to inject params in function
            func = parser.use_args(
                schema, locations=[location], **kwargs)(func)

            # Add parameters info to documentation
            try:
                location = LOCATION_MAP[location]
            except KeyError:
                raise InvalidLocation(
                    "{} is not a valid location".format(location))

            # At this stage, only dump schema and parameters in doc dictionary
            # schema instance will be replaced later on by $ref or json
            doc = {'parameters': {
                'location': location,
                'required': required,
                'schema': schema,
            }}
            func._apidoc = deepupdate(getattr(func, '_apidoc', {}), doc)

            return func

        return decorator

    def response(self, schema=None, *, code=200, description='',
                 paginate=False, paginate_with=None,
                 etag_schema=None, disable_etag=False):
        """Decorator generating an endpoint response, specifying the schema
        to use for serialization and others parameters.

        :param schema: :class:`Schema <marshmallow.Schema>` class or instance,
            or `None`
        :param int code: HTTP status code (default 200)
        :param bool paginate: Assume resource function returns paginated result
        :param etag_schema: :class:`Schema <marshmallow.Schema>` class
            or instance, or `None`
        :param bool disable_etag: Disable ETag feature locally even if enabled
            globally
        """
        def wrapper(func):

            # Add schema as response in the API doc
            doc = {'responses': {code: {'description': description}}}
            if schema:
                if paginate:
                    # Pagination -> we're returning a list
                    doc['responses'][code]['schema'] = {
                        'type': 'array',
                        'items': schema
                    }
                else:
                    doc['responses'][code]['schema'] = schema
            func._apidoc = deepupdate(getattr(func, '_apidoc', {}), doc)

            return response(
                schema=schema, code=code,
                paginate=paginate, paginate_with=paginate_with,
                etag_schema=etag_schema, disable_etag=disable_etag
            )(func)

        return wrapper
