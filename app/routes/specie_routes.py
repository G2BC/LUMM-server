from flask import request
from flask.views import MethodView
from flask_smorest import Blueprint

from app.schemas.specie_schemas import SpecieWithPhotosPaginationSchema
from app.services.specie_service import list_species_with_photos

specie_bp = Blueprint(
    "species",
    "species",
    url_prefix="/species",
    description="Operações relacionadas as espécies",
)


@specie_bp.route("")
class UsersList(MethodView):
    @specie_bp.response(200, SpecieWithPhotosPaginationSchema)
    def get(self):
        search = request.args.get("search", type=str)
        page = request.args.get("page", type=int)
        per_page = request.args.get("per_page", type=int)

        return list_species_with_photos(search, page, per_page)
