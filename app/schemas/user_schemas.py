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
    password = fields.String(required=True, load_only=True)


class UserPaginationSchema(Schema):
    items = fields.List(fields.Nested(UserSchema))
    total = fields.Integer()
    page = fields.Integer(allow_none=True)
    per_page = fields.Integer(allow_none=True)
    pages = fields.Integer(allow_none=True)
