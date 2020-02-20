"""Utils"""

from collections import abc

from werkzeug.datastructures import Headers
from flask import _app_ctx_stack
from apispec.utils import trim_docstring, dedent


# https://stackoverflow.com/questions/3232943/
def deepupdate(original, update):
    """Recursively update a dict.

    Subdict's won't be overwritten but also updated.
    """
    if not isinstance(original, abc.Mapping):
        return update
    for key, value in update.items():
        if isinstance(value, abc.Mapping):
            original[key] = deepupdate(original.get(key, {}), value)
        else:
            original[key] = value
    return original


# XXX: Does this belong here?
def get_appcontext():
    """Return extension section from top of appcontext stack"""

    # http://flask.pocoo.org/docs/latest/extensiondev/#the-extension-code
    ctx = _app_ctx_stack.top
    if not hasattr(ctx, 'flask_smorest'):
        ctx.flask_smorest = {}
    return ctx.flask_smorest


def load_info_from_docstring(docstring, *, delimiter="---"):
    """Load summary and description from docstring

    :param str delimiter: Summary and description information delimiter.
    If a line starts with this string, this line and the lines after are
    ignored. Defaults to "---".
    """
    split_lines = trim_docstring(docstring).split('\n')

    if delimiter is not None:
        # Info is separated from rest of docstring by a `delimiter` line
        for index, line in enumerate(split_lines):
            if line.lstrip().startswith(delimiter):
                cut_at = index
                break
        else:
            cut_at = index + 1
        split_lines = split_lines[:cut_at]

    # Description is separated from summary by an empty line
    for index, line in enumerate(split_lines):
        if line.strip() == '':
            summary_lines = split_lines[:index]
            description_lines = split_lines[index + 1:]
            break
    else:
        summary_lines = split_lines
        description_lines = []

    info = {}
    if summary_lines:
        info['summary'] = dedent('\n'.join(summary_lines))
    if description_lines:
        info['description'] = dedent('\n'.join(description_lines))
    return info


# Copied from Flask
def unpack_tuple_response(rv):
    """Unpack a flask Response tuple"""

    status = headers = None

    # unpack tuple returns
    # Unlike Flask, we check exact type because tuple subclasses may be
    # returned by view functions and paginated/dumped
    if type(rv) is tuple:  # pylint: disable=unidiomatic-typecheck
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


def prepare_response(response, spec, default_response_content_type):
    """Rework response according to OAS version"""
    # OAS 2
    if spec.openapi_version.major < 3:
        if 'example' in response:
            response['examples'] = {
                default_response_content_type: response.pop('example')
            }
    # OAS 3
    else:
        for field in ('schema', 'example', 'examples'):
            if field in response:
                (
                    response
                    .setdefault('content', {})
                    .setdefault(default_response_content_type, {})
                    [field]
                ) = response.pop(field)
