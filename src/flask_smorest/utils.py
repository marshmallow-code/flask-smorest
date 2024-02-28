"""Utils"""

from collections import abc

from werkzeug.datastructures import Headers
from flask import g
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


def remove_none(mapping):
    """Remove None values in a dict"""
    return {k: v for k, v in mapping.items() if v is not None}


def resolve_schema_instance(schema):
    """Return schema instance for given schema (instance or class).

    :param type|Schema schema: marshmallow.Schema instance or class
    :return: schema instance of given schema
    """
    return schema() if isinstance(schema, type) else schema


def get_appcontext():
    """Get extension section in flask g"""
    return g.setdefault("_flask_smorest", {})


def load_info_from_docstring(docstring, *, delimiter="---"):
    """Load summary and description from docstring

    :param str delimiter: Summary and description information delimiter.
    If a line starts with this string, this line and the lines after are
    ignored. Defaults to "---".
    """
    split_lines = trim_docstring(docstring).split("\n")

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
        if line.strip() == "":
            summary_lines = split_lines[:index]
            description_lines = split_lines[index + 1 :]
            break
    else:
        summary_lines = split_lines
        description_lines = []

    info = {}
    if summary_lines:
        info["summary"] = dedent("\n".join(summary_lines))
    if description_lines:
        info["description"] = dedent("\n".join(description_lines))
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
                "The view function did not return a valid response tuple."
                " The tuple must have the form (body, status, headers),"
                " (body, status), or (body, headers)."
            )

    return rv, status, headers


def set_status_and_headers_in_response(response, status, headers):
    """Set status and headers in flask Response object"""
    if headers:
        response.headers.extend(headers)
    if status is not None:
        if isinstance(status, int):
            response.status_code = status
        else:
            response.status = status


def prepare_response(response, spec, content_type):
    """Rework response according to OAS version"""
    # OAS 2
    if spec.openapi_version.major < 3:
        if "example" in response:
            response["examples"] = {content_type: response.pop("example")}
    # OAS 3
    else:
        for field in ("schema", "example", "examples"):
            if field in response:
                (
                    response.setdefault("content", {}).setdefault(content_type, {})[
                        field
                    ]
                ) = response.pop(field)


def normalize_config_prefix(config_prefix):
    """Normalize API config prefix

    Sets upper case and appends underscore if missing.

    :param str config_prefix: Raw prefix

    :return: Normalized prefix
    """
    result = config_prefix.strip().upper()
    if result and not result.endswith("_"):
        result += "_"
    return result


class PrefixedMappingProxy(abc.Mapping):
    """Mapping to proxy another mapping using a prefix

    .. code-block:: python
        some_dict = PrefixedMappingProxy(
            proxied_dict={"foobar_key1": 1, "foobar_key2": 2}, prefix="foobar_"
        )
        assert some_dict["key1"] == 1
        assert some_dict["key2"] == 2
    """

    def __init__(self, proxied_dict, prefix):
        self._dict = proxied_dict
        self.prefix = prefix

    def __getitem__(self, key):
        return self._dict[self.prefix + str(key)]

    def __iter__(self):
        return iter(x for x in self._dict if x.startswith(self.prefix))

    def __len__(self):
        return sum(1 for _ in iter(self))
