from marshmallow import Schema, fields


class SpeciesPhotoSchema(Schema):
    photo_id = fields.Integer(dump_only=True)
    medium_url = fields.String(dump_only=True)
    original_url = fields.String(allow_none=True, dump_only=True)
    license_code = fields.String(allow_none=True, dump_only=True)
    attribution = fields.String(allow_none=True, dump_only=True)
    source = fields.String(dump_only=True)
    fetched_at = fields.DateTime(dump_only=True)
    lumm = fields.Bool(allow_none=True)
    featured = fields.Bool(allow_none=True)


class SpecieWithPhotosSchema(Schema):
    id = fields.Integer(dump_only=True)
    scientific_name = fields.String(required=True)
    lineage = fields.String(required=True)
    photos = fields.List(
        fields.Nested(
            SpeciesPhotoSchema(
                only=(
                    "photo_id",
                    "medium_url",
                    "original_url",
                    "license_code",
                    "attribution",
                    "lumm",
                    "featured",
                )
            ),
            dump_only=True,
        )
    )


class SpecieWithPhotosPaginationSchema(Schema):
    items = fields.List(fields.Nested(SpecieWithPhotosSchema))
    total = fields.Integer()
    page = fields.Integer(allow_none=True)
    per_page = fields.Integer(allow_none=True)
    pages = fields.Integer(allow_none=True)
