from marshmallow import Schema, fields

from app.utils.object_storage import normalize_object_url

from .taxon_schemas import TaxonSchema


class SpeciesPhotoSchema(Schema):
    photo_id = fields.String(dump_only=True)
    medium_url = fields.Method("get_medium_url", dump_only=True)
    original_url = fields.Method("get_original_url", dump_only=True)
    license_code = fields.String(allow_none=True, dump_only=True)
    attribution = fields.String(allow_none=True, dump_only=True)
    rights_holder = fields.String(allow_none=True, dump_only=True)
    source_url = fields.String(allow_none=True, dump_only=True)
    declaration_accepted_at = fields.DateTime(allow_none=True, dump_only=True)
    source = fields.String(dump_only=True)
    fetched_at = fields.DateTime(dump_only=True)
    lumm = fields.Boolean(allow_none=True)
    featured = fields.Boolean(allow_none=True)

    @staticmethod
    def get_medium_url(obj):
        return normalize_object_url(getattr(obj, "medium_url", None))

    @staticmethod
    def get_original_url(obj):
        return normalize_object_url(getattr(obj, "original_url", None))


class SpeciesWithPhotosSchema(Schema):
    id = fields.String(dump_only=True)
    scientific_name = fields.String(required=True)
    lineage = fields.String(allow_none=True)
    lum_mycelium = fields.Method("get_lum_mycelium", allow_none=True)
    lum_basidiome = fields.Method("get_lum_basidiome", allow_none=True)
    lum_stipe = fields.Method("get_lum_stipe", allow_none=True)
    lum_pileus = fields.Method("get_lum_pileus", allow_none=True)
    lum_lamellae = fields.Method("get_lum_lamellae", allow_none=True)
    lum_spores = fields.Method("get_lum_spores", allow_none=True)
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
                    "rights_holder",
                    "source_url",
                    "declaration_accepted_at",
                    "lumm",
                    "featured",
                )
            ),
            dump_only=True,
        )
    )

    @staticmethod
    def _get_characteristic_value(obj, field_name):
        characteristics = getattr(obj, "characteristics", None)
        if characteristics is not None:
            return getattr(characteristics, field_name, None)
        return None

    def get_lum_mycelium(self, obj):
        return self._get_characteristic_value(obj, "lum_mycelium")

    def get_lum_basidiome(self, obj):
        return self._get_characteristic_value(obj, "lum_basidiome")

    def get_lum_stipe(self, obj):
        return self._get_characteristic_value(obj, "lum_stipe")

    def get_lum_pileus(self, obj):
        return self._get_characteristic_value(obj, "lum_pileus")

    def get_lum_lamellae(self, obj):
        return self._get_characteristic_value(obj, "lum_lamellae")

    def get_lum_spores(self, obj):
        return self._get_characteristic_value(obj, "lum_spores")


class SpeciesWithPhotosPaginationSchema(Schema):
    items = fields.List(fields.Nested(SpeciesWithPhotosSchema))
    total = fields.Integer()
    page = fields.Integer(allow_none=True)
    per_page = fields.Integer(allow_none=True)
    pages = fields.Integer(allow_none=True)
