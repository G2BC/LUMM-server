from marshmallow import Schema, fields


class ReferenceSchema(Schema):
    id = fields.Integer(dump_only=True)
    doi = fields.String(allow_none=True)
    url = fields.String(allow_none=True)
    apa = fields.String(allow_none=True)
