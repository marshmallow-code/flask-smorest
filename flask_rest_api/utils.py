"""Utils"""

from collections.abc import Mapping

from werkzeug.datastructures import Headers
from flask import _app_ctx_stack
from apispec.utils import trim_docstring, dedent


# https://stackoverflow.com/a/3233356
def deepupdate(original, update):
    """Recursively update a dict.

    Subdict's won't be overwritten but also updated.
    """
    for key, value in update.items():
        if isinstance(value, Mapping):
            original[key] = deepupdate(original.get(key, {}), value)
        else:
            original[key] = value
    return original


# XXX: Does this belong here?
def get_appcontext():
    """Return extension section from top of appcontext stack"""

    # http://flask.pocoo.org/docs/latest/extensiondev/#the-extension-code
    ctx = _app_ctx_stack.top
    if not hasattr(ctx, 'flask_rest_api'):
        ctx.flask_rest_api = {}
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


# Copied from flask
def unpack_tuple_response(rv):
    """Unpack a flask Response tuple"""

    status = headers = None

    # unpack tuple returns
    if isinstance(rv, tuple):
        len_rv = len(rv)

        # a 3-tuple is unpacked directly
        if len_rv == 3:
            rv, status, headers = rv
        # decide if a 2-tuple has status or headers
        elif len_rv == 2:
            if isinstance(rv[1], (Headers, dict, tuple, list)):
                rv, headers = rv
            else:
                rv, status = rv
        # other sized tuples are not allowed
        else:
            raise TypeError(
                'The view function did not return a valid response tuple.'
                ' The tuple must have the form (body, status, headers),'
                ' (body, status), or (body, headers).'
            )

    return rv, status, headers


def set_status_and_headers_in_response(response, status, headers):
    """Set status and headers in flask Reponse object"""
    if headers:
        response.headers.extend(headers)
    if status is not None:
        if isinstance(status, int):
            response.status_code = status
        else:
            response.status = status
