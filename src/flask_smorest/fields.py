"""Custom marshmallow fields"""

import marshmallow as ma


class Upload(ma.fields.Field):
    """File upload field

    :param str format: File content encoding (binary, base64).
         Only relevant to OpenAPI 3. Only used for documentation purpose.
    """

    def __init__(self, format="binary", **kwargs):
        self.format = format
        super().__init__(**kwargs)
