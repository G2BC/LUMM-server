import re

from marshmallow import Schema, ValidationError, fields, validate, validates


class UserSchema(Schema):
    id = fields.String(dump_only=True)
    name = fields.String(required=True)
    institution = fields.String(allow_none=True)
    email = fields.Email(
        required=True,
        error_messages={
            "required": "O campo email é obrigatório.",
            "invalid": "Email inválido.",
            "null": "O campo email não pode ser nulo.",
        },
    )
    is_admin = fields.Boolean(dump_only=True)
    created_at = fields.DateTime(dump_only=True)


class UserCreateSchema(Schema):
    name = fields.String(
        required=True,
        validate=validate.Length(min=2, max=100, error="Nome deve ter entre 2 e 100 caracteres."),
        error_messages={
            "required": "O campo nome é obrigatório.",
            "null": "O campo nome não pode ser nulo.",
        },
    )
    institution = fields.String(
        allow_none=True,
        validate=validate.Length(max=150, error="Instituição deve ter no máximo 150 caracteres."),
    )
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
        validate=validate.Length(
            min=8, max=128, error="A senha deve ter entre 8 e 128 caracteres."
        ),
        error_messages={
            "required": "O campo senha é obrigatório.",
            "null": "O campo senha não pode ser nulo.",
        },
    )

    @validates("password")
    def validate_password_strength(self, value: str):
        if not re.search(r"[A-Z]", value):
            raise ValidationError("A senha precisa ter ao menos uma letra maiúscula.")
        if not re.search(r"[a-z]", value):
            raise ValidationError("A senha precisa ter ao menos uma letra minúscula.")
        if not re.search(r"\d", value):
            raise ValidationError("A senha precisa ter ao menos um número.")


class UserPaginationSchema(Schema):
    items = fields.List(fields.Nested(UserSchema))
    total = fields.Integer()
    page = fields.Integer(allow_none=True)
    per_page = fields.Integer(allow_none=True)
    pages = fields.Integer(allow_none=True)
