from apispec.utils import build_reference


# Getter functions are copied from apispec tests

def get_schemas(spec):
    if spec.openapi_version.major < 3:
        return spec.to_dict()["definitions"]
    return spec.to_dict()["components"]["schemas"]


def get_responses(spec):
    if spec.openapi_version.major < 3:
        return spec.to_dict()["responses"]
    return spec.to_dict()["components"]["responses"]


def get_parameters(spec):
    if spec.openapi_version.major < 3:
        return spec.to_dict()["parameters"]
    return spec.to_dict()["components"]["parameters"]


def get_headers(spec):
    return spec.to_dict()["components"]["headers"]


def build_ref(spec, component_type, obj):
    return build_reference(component_type, spec.openapi_version.major, obj)
