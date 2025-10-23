from marshmallow import Schema, fields

from .taxon_schemas import TaxonSchema


class SpeciesPhotoSchema(Schema):
    photo_id = fields.Integer(dump_only=True)
    medium_url = fields.String(dump_only=True)
    original_url = fields.String(allow_none=True, dump_only=True)
    license_code = fields.String(allow_none=True, dump_only=True)
    attribution = fields.String(allow_none=True, dump_only=True)
    source = fields.String(dump_only=True)
    fetched_at = fields.DateTime(dump_only=True)
    lumm = fields.Boolean(allow_none=True)
    featured = fields.Boolean(allow_none=True)


class SpeciesWithPhotosSchema(Schema):
    id = fields.Integer(dump_only=True)
    scientific_name = fields.String(required=True)
    lineage = fields.String(allow_none=True)
    lum_mycelium = fields.Boolean(allow_none=True, load_default=None, dump_default=None)
    lum_basidiome = fields.Boolean(allow_none=True, load_default=None, dump_default=None)
    lum_stipe = fields.Boolean(allow_none=True, load_default=None, dump_default=None)
    lum_pileus = fields.Boolean(allow_none=True, load_default=None, dump_default=None)
    lum_lamellae = fields.Boolean(allow_none=True, load_default=None, dump_default=None)
    lum_spores = fields.Boolean(allow_none=True, load_default=None, dump_default=None)
    types_country = fields.String(allow_none=True)
    mycobank_type = fields.String(allow_none=True)
    mycobank_index_fungorum_id = fields.String(allow_none=True)
    taxonomy = fields.Nested(TaxonSchema, dump_only=True)
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


class SpeciesWithPhotosPaginationSchema(Schema):
    items = fields.List(fields.Nested(SpeciesWithPhotosSchema))
    total = fields.Integer()
    page = fields.Integer(allow_none=True)
    per_page = fields.Integer(allow_none=True)
    pages = fields.Integer(allow_none=True)
