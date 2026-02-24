from marshmallow import Schema, fields


class LoginRequestSchema(Schema):
    email = fields.Email(
        required=True,
        error_messages={
            "required": "O campo email é obrigatório.",
            "invalid": "Email inválido.",
            "null": "O campo email não pode ser nulo.",
        },
    )
    password = fields.String(
        required=True,
        load_only=True,
        error_messages={
            "required": "O campo senha é obrigatório.",
            "null": "O campo senha não pode ser nulo.",
        },
    )


class TokenSchema(Schema):
    access_token = fields.String(required=True, dump_only=True)
    refresh_token = fields.String(dump_only=True)
