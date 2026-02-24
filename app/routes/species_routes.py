from flask import request
from flask.views import MethodView
from flask_smorest import Blueprint, abort

from app.schemas import SelectSchema
from app.schemas.species_schemas import SpeciesWithPhotosPaginationSchema, SpeciesWithPhotosSchema
from app.services.species_service import SpeciesService

specie_bp = Blueprint(
    "species",
    "species",
    url_prefix="/species",
)


@specie_bp.route("/list")
class SpeciesSearchList(MethodView):
    @specie_bp.response(200, SpeciesWithPhotosPaginationSchema)
    @specie_bp.alt_response(400, description="Parâmetros inválidos")
    def get(self):
        search = request.args.get("search", type=str)
        lineage = request.args.get("lineage", type=str)
        country = request.args.get("country", type=str)
        page = request.args.get("page", type=int)
        per_page = request.args.get("per_page", type=int)

        try:
            return SpeciesService.search(search, lineage, country, page, per_page)
        except ValueError as exc:
            abort(400, message=str(exc))


@specie_bp.route("/lineage/select")
class LineageSelect(MethodView):
    @specie_bp.response(200, SelectSchema(many=True))
    def get(self):
        search = request.args.get("search", type=str)

        return SpeciesService.select_lineage(search)


@specie_bp.route("/country/select")
class SpeciesCountrySelect(MethodView):
    @specie_bp.response(200, SelectSchema(many=True))
    def get(self):
        search = request.args.get("search", type=str)

        return SpeciesService.country_select(search)


@specie_bp.route("/<string:species>")
class GetSpecies(MethodView):
    @specie_bp.response(200, SpeciesWithPhotosSchema)
    @specie_bp.alt_response(404, description="Espécie não encontrada")
    def get(self, species: str):
        try:
            return SpeciesService.get(species)
        except ValueError as exc:
            abort(404, message=str(exc))
