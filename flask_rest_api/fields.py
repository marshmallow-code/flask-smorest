"""Custom fields"""

import marshmallow as ma


class Upload(ma.fields.Field):
    """File upload field"""
    def __init__(self, format='binary', **kwargs):
        self.format = format
        super().__init__(**kwargs)
