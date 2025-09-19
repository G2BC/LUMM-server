from flask import request
from flask.views import MethodView
from flask_smorest import Blueprint

from app.schemas import SelectSchema
from app.schemas.species_schemas import SpeciesWithPhotosPaginationSchema
from app.services.species_service import (
    lineage_select,
    list_species_with_photos,
    species_country_select,
)
from app.utils.require_api_key import require_api_key

specie_bp = Blueprint(
    "species",
    "species",
    url_prefix="/species",
)


@specie_bp.route("")
class SpeciesSearchList(MethodView):
    decorators = [require_api_key]

    @specie_bp.response(200, SpeciesWithPhotosPaginationSchema)
    def get(self):
        search = request.args.get("search", type=str)
        lineage = request.args.get("lineage", type=str)
        country = request.args.get("country", type=str)
        page = request.args.get("page", type=int)
        per_page = request.args.get("per_page", type=int) or 30

        return list_species_with_photos(search, lineage, country, page, per_page)


@specie_bp.route("/select/lineage")
class LineageSelect(MethodView):
    decorators = [require_api_key]

    @specie_bp.response(200, SelectSchema(many=True))
    def get(self):
        search = request.args.get("search", type=str)

        return lineage_select(search)


@specie_bp.route("/select/country")
class SpeciesCountrySelect(MethodView):
    decorators = [require_api_key]

    @specie_bp.response(200, SelectSchema(many=True))
    def get(self):
        search = request.args.get("search", type=str)

        return species_country_select(search)
