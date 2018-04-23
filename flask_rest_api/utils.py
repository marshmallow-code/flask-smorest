"""Utils"""

from collections import defaultdict

from flask import _app_ctx_stack


# http://stackoverflow.com/a/8310229/4653485
def deepupdate(original, update):
    """Recursively update a dict.

    Subdict's won't be overwritten but also updated.
    """
    for key, value in original.items():
        if key not in update:
            update[key] = value
        elif isinstance(value, dict):
            deepupdate(value, update[key])
    return update


# XXX: Does this belong here?
def get_appcontext():
    """Return extension section from top of appcontext stack"""

    # http://flask.pocoo.org/docs/0.12/extensiondev/#the-extension-code
    ctx = _app_ctx_stack.top
    if not hasattr(ctx, 'flask_rest_api'):
        ctx.flask_rest_api = defaultdict(dict)
    return ctx.flask_rest_api
