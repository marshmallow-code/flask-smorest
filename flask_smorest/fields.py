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


class BigInteger(ma.fields.Integer):
    """A bigint field."""

    def _validated(self, value):
        """Validate that the number is inside 64bit bigint."""
        new_value = super()._validated(value)
        invalid_bigint = (new_value > (2**63 - 1)) or (new_value < (-(2**63) + 1))
        if invalid_bigint:
            raise self.make_error("invalid_bigint", input=value)
        return new_value


BigInteger.default_error_messages["invalid_bigint"] = "Number not valid bigint."
