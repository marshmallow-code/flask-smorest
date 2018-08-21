"""Utils"""

from collections import defaultdict

from flask import _app_ctx_stack
from apispec.utils import trim_docstring, dedent


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


def load_info_from_docstring(docstring):
    """Load summary and description from docstring"""
    split_lines = trim_docstring(docstring).split('\n')

    # Info is separated from rest of docstring by a '---' line
    for index, line in enumerate(split_lines):
        if line.lstrip().startswith('---'):
            cut_at = index
            break
    else:
        cut_at = index + 1

    split_info_lines = split_lines[:cut_at]

    # Description is separated from summary by an empty line
    for index, line in enumerate(split_info_lines):
        if line.strip() == '':
            summary_lines = split_info_lines[:index]
            description_lines = split_info_lines[index + 1:]
            break
    else:
        summary_lines = split_info_lines
        description_lines = []

    info = {}
    if summary_lines:
        info['summary'] = dedent('\n'.join(summary_lines))
    if description_lines:
        info['description'] = dedent('\n'.join(description_lines))
    return info
