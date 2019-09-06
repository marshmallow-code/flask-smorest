"""Custom field properties functions"""
from flask_rest_api.fields import Upload


def uploadfield2properties(self, field, **kwargs):
    """Document Upload field"""
    ret = {}
    if isinstance(field, Upload):
        if self.openapi_version.major < 3:
            ret['type'] = 'file'
        else:
            ret['type'] = 'string'
            ret['format'] = field.format
    return ret
