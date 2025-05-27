from marshmallow import Schema, fields

class UserSchema(Schema):
    id = fields.String(dump_only=True)
    name = fields.String(required=True)
    institution = fields.String(allow_none=True)
    email = fields.Email(required=True)
    is_admin = fields.Boolean(dump_only=True)
    created_at = fields.DateTime(dump_only=True)

class UserCreateSchema(Schema):
    name = fields.String(required=True)
    institution = fields.String(allow_none=True)
    email = fields.Email(required=True)
    is_admin = fields.Boolean(required=False)
    password = fields.String(required=True, load_only=True)
