from marshmallow import Schema, fields


class SelectSchema(Schema):
    label = fields.String(required=True)
    value = fields.String(required=True)
