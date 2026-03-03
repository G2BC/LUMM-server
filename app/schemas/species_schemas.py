from marshmallow import Schema, fields

from app.utils.object_storage import normalize_object_url

from .taxon_schemas import TaxonSchema


class SpeciesPhotoSchema(Schema):
    photo_id = fields.Integer(dump_only=True)
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
    id = fields.Integer(dump_only=True)
    scientific_name = fields.String(required=True)
    lineage = fields.String(allow_none=True)
    lum_mycelium = fields.Method("get_lum_mycelium", allow_none=True)
    lum_basidiome = fields.Method("get_lum_basidiome", allow_none=True)
    lum_stipe = fields.Method("get_lum_stipe", allow_none=True)
    lum_pileus = fields.Method("get_lum_pileus", allow_none=True)
    lum_lamellae = fields.Method("get_lum_lamellae", allow_none=True)
    lum_spores = fields.Method("get_lum_spores", allow_none=True)
    cultivation = fields.Method("get_cultivation", allow_none=True)
    finding_tips = fields.Method("get_finding_tips", allow_none=True)
    nearby_trees = fields.Method("get_nearby_trees", allow_none=True)
    curiosities = fields.Method("get_curiosities", allow_none=True)
    general_description = fields.Method("get_general_description", allow_none=True)
    colors = fields.Method("get_colors", allow_none=True)
    size_cm = fields.Method("get_size_cm", allow_none=True)
    growth_form_id = fields.Method("get_growth_form_id", allow_none=True)
    substrate_id = fields.Method("get_substrate_id", allow_none=True)
    nutrition_mode_id = fields.Method("get_nutrition_mode_id", allow_none=True)
    habitat_ids = fields.Method("get_habitat_ids", allow_none=True)
    season_start_month = fields.Method("get_season_start_month", allow_none=True)
    season_end_month = fields.Method("get_season_end_month", allow_none=True)
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

    def get_cultivation(self, obj):
        return self._get_characteristic_value(obj, "cultivation")

    def get_finding_tips(self, obj):
        return self._get_characteristic_value(obj, "finding_tips")

    def get_nearby_trees(self, obj):
        return self._get_characteristic_value(obj, "nearby_trees")

    def get_curiosities(self, obj):
        return self._get_characteristic_value(obj, "curiosities")

    def get_general_description(self, obj):
        return self._get_characteristic_value(obj, "general_description")

    def get_colors(self, obj):
        return self._get_characteristic_value(obj, "colors")

    def get_size_cm(self, obj):
        return self._get_characteristic_value(obj, "size_cm")

    def get_growth_form_id(self, obj):
        return self._get_characteristic_value(obj, "growth_form_id")

    def get_substrate_id(self, obj):
        return self._get_characteristic_value(obj, "substrate_id")

    def get_nutrition_mode_id(self, obj):
        return self._get_characteristic_value(obj, "nutrition_mode_id")

    def get_habitat_ids(self, obj):
        characteristics = getattr(obj, "characteristics", None)
        if not characteristics:
            return []
        habitats = getattr(characteristics, "habitats", None) or []
        return [habitat.id for habitat in habitats]

    def get_season_start_month(self, obj):
        return self._get_characteristic_value(obj, "season_start_month")

    def get_season_end_month(self, obj):
        return self._get_characteristic_value(obj, "season_end_month")


class SpeciesWithPhotosPaginationSchema(Schema):
    items = fields.List(fields.Nested(SpeciesWithPhotosSchema))
    total = fields.Integer()
    page = fields.Integer(allow_none=True)
    per_page = fields.Integer(allow_none=True)
    pages = fields.Integer(allow_none=True)
