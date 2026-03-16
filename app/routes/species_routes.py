import json

import sentry_sdk
from flask import Response, request
from flask.views import MethodView
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required, verify_jwt_in_request
from flask_smorest import Blueprint, abort

from app.schemas import DomainSelectSchema, SelectSchema
from app.schemas.species_change_request_schemas import (
    SpeciesChangeRequestCreateSchema,
    SpeciesChangeRequestPaginationSchema,
    SpeciesChangeRequestReviewSchema,
    SpeciesChangeRequestSchema,
    SpeciesPhotoUploadUrlRequestSchema,
    SpeciesPhotoUploadUrlResponseSchema,
    SpeciesTmpCleanupResponseSchema,
)
from app.schemas.species_schemas import (
    SpeciesDetailSchema,
    SpeciesPhotoCreateRequestSchema,
    SpeciesPhotoCreateResponseSchema,
    SpeciesPhotoUpdateRequestSchema,
    SpeciesPhotoUploadUrlPayloadSchema,
    SpeciesWithPhotosPaginationSchema,
)
from app.services.species_change_request_service import SpeciesChangeRequestService
from app.services.species_photo_service import SpeciesPhotoService
from app.services.species_service import SpeciesService

specie_bp = Blueprint(
    "species",
    "species",
    url_prefix="/species",
)


def _ensure_curator_or_admin():
    claims = get_jwt()
    is_admin = bool(claims.get("is_admin", False))
    role = (claims.get("role") or "").lower()
    is_curator = bool(claims.get("is_curator", False))
    if not (is_admin or is_curator or role in {"curator", "admin"}):
        abort(403, message="Acesso permitido apenas para curadores ou administradores.")


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


@specie_bp.route("/family/select")
class SpeciesFamilySelect(MethodView):
    @specie_bp.response(200, SelectSchema(many=True))
    def get(self):
        search = request.args.get("search", type=str)

        return SpeciesService.family_select(search)


@specie_bp.route("/domains/select")
class SpeciesDomainsSelect(MethodView):
    @specie_bp.response(200, DomainSelectSchema(many=True))
    @specie_bp.alt_response(400, description="Parâmetros inválidos")
    def get(self):
        domain = request.args.get("domain", type=str)
        search = request.args.get("search", type=str)

        try:
            return SpeciesService.domain_select(domain, search)
        except ValueError as exc:
            abort(400, message=str(exc))


@specie_bp.route("/<string:species>")
class GetSpecies(MethodView):
    @specie_bp.response(200, SpeciesDetailSchema)
    @specie_bp.alt_response(404, description="Espécie não encontrada")
    def get(self, species: str):
        try:
            return SpeciesService.get(species)
        except ValueError as exc:
            abort(404, message=str(exc))


@specie_bp.route("/<int:species_id>/photos/upload-url")
class SpeciesPhotoUploadUrl(MethodView):
    @jwt_required()
    @specie_bp.arguments(SpeciesPhotoUploadUrlPayloadSchema, location="json")
    @specie_bp.response(200, SpeciesPhotoUploadUrlResponseSchema)
    @specie_bp.alt_response(400, description="Erro de validação/regra de negócio")
    @specie_bp.alt_response(403, description="Acesso permitido apenas para curadores/admins")
    @specie_bp.alt_response(404, description="Espécie não encontrada")
    def post(self, payload, species_id: int):
        _ensure_curator_or_admin()

        try:
            return SpeciesPhotoService.generate_upload_url(
                species_id=species_id,
                filename=payload["filename"],
                mime_type=payload["mime_type"],
                size_bytes=payload["size_bytes"],
            )
        except ValueError as exc:
            message = str(exc)
            if "não encontrada" in message.lower():
                abort(404, message=message)
            abort(400, message=message)


@specie_bp.route("/<int:species_id>/photos")
class SpeciesPhotos(MethodView):
    @jwt_required()
    @specie_bp.arguments(SpeciesPhotoCreateRequestSchema, location="json")
    @specie_bp.response(201, SpeciesPhotoCreateResponseSchema)
    @specie_bp.alt_response(400, description="Erro de validação/regra de negócio")
    @specie_bp.alt_response(403, description="Acesso permitido apenas para curadores/admins")
    @specie_bp.alt_response(404, description="Espécie não encontrada")
    def post(self, payload, species_id: int):
        _ensure_curator_or_admin()

        try:
            return SpeciesPhotoService.create_photo(species_id=species_id, payload=payload)
        except ValueError as exc:
            message = str(exc)
            if "não encontrada" in message.lower():
                abort(404, message=message)
            abort(400, message=message)


@specie_bp.route("/<int:species_id>/photos/<string:photo_id>")
class SpeciesPhotoDetail(MethodView):
    @jwt_required()
    @specie_bp.arguments(SpeciesPhotoUpdateRequestSchema, location="json")
    @specie_bp.response(200, SpeciesPhotoCreateResponseSchema)
    @specie_bp.alt_response(400, description="Erro de validação/regra de negócio")
    @specie_bp.alt_response(403, description="Acesso permitido apenas para curadores/admins")
    @specie_bp.alt_response(404, description="Espécie/foto não encontrada")
    def patch(self, payload, species_id: int, photo_id: str):
        _ensure_curator_or_admin()

        try:
            return SpeciesPhotoService.update_photo(
                species_id=species_id,
                photo_id=photo_id,
                payload=payload,
            )
        except ValueError as exc:
            message = str(exc)
            if "não encontrada" in message.lower():
                abort(404, message=message)
            abort(400, message=message)

    @jwt_required()
    @specie_bp.response(204)
    @specie_bp.alt_response(400, description="Erro de validação/regra de negócio")
    @specie_bp.alt_response(403, description="Acesso permitido apenas para curadores/admins")
    @specie_bp.alt_response(404, description="Espécie/foto não encontrada")
    def delete(self, species_id: int, photo_id: str):
        _ensure_curator_or_admin()

        try:
            SpeciesPhotoService.delete_photo(species_id=species_id, photo_id=photo_id)
            return None
        except ValueError as exc:
            message = str(exc)
            if "não encontrada" in message.lower():
                abort(404, message=message)
            abort(400, message=message)


@specie_bp.route("/requests")
class SpeciesChangeRequests(MethodView):
    @specie_bp.arguments(SpeciesChangeRequestCreateSchema)
    @specie_bp.response(201, SpeciesChangeRequestSchema)
    @specie_bp.alt_response(400, description="Erro de validação/regra de negócio")
    def post(self, payload):
        verify_jwt_in_request(optional=True)
        identity = None
        if get_jwt():
            identity = get_jwt_identity()

        try:
            return SpeciesChangeRequestService.create_request(payload, identity)
        except ValueError as exc:
            abort(400, message=str(exc))

    @jwt_required()
    @specie_bp.response(200, SpeciesChangeRequestPaginationSchema)
    @specie_bp.alt_response(400, description="Parâmetros inválidos")
    @specie_bp.alt_response(403, description="Acesso permitido apenas para curadores/admins")
    def get(self):
        _ensure_curator_or_admin()

        status = request.args.get("status", type=str)
        page = request.args.get("page", type=int)
        per_page = request.args.get("per_page", type=int)

        try:
            return SpeciesChangeRequestService.list_requests(status, page, per_page)
        except ValueError as exc:
            abort(400, message=str(exc))


@specie_bp.route("/requests/<string:request_id>")
class GetSpeciesChangeRequest(MethodView):
    @jwt_required()
    @specie_bp.response(200, SpeciesChangeRequestSchema)
    @specie_bp.alt_response(403, description="Acesso permitido apenas para curadores/admins")
    @specie_bp.alt_response(404, description="Solicitação não encontrada")
    def get(self, request_id: str):
        _ensure_curator_or_admin()

        try:
            return SpeciesChangeRequestService.get_request(request_id)
        except ValueError as exc:
            message = str(exc)
            if "não encontrada" in message.lower():
                abort(404, message=message)
            abort(400, message=message)


@specie_bp.route("/requests/upload-url")
class SpeciesChangeRequestUploadUrl(MethodView):
    @specie_bp.arguments(SpeciesPhotoUploadUrlRequestSchema, location="json")
    @specie_bp.response(200, SpeciesPhotoUploadUrlResponseSchema)
    @specie_bp.alt_response(400, description="Erro de validação/regra de negócio")
    def post(self, payload):
        try:
            return SpeciesChangeRequestService.generate_upload_url(
                filename=payload["filename"],
                mime_type=payload["mime_type"],
                size_bytes=payload["size_bytes"],
                species_id=payload.get("species_id"),
            )
        except ValueError as exc:
            abort(400, message=str(exc))


@specie_bp.route("/requests/cleanup-tmp")
class CleanupSpeciesTmpUploads(MethodView):
    @jwt_required()
    @specie_bp.response(200, SpeciesTmpCleanupResponseSchema)
    @specie_bp.alt_response(400, description="Parâmetros inválidos")
    @specie_bp.alt_response(403, description="Acesso permitido apenas para curadores/admins")
    def post(self):
        _ensure_curator_or_admin()
        retention_days = request.args.get("retention_days", type=int)
        dry_run = request.args.get("dry_run", default="true", type=str).lower() != "false"

        try:
            return SpeciesChangeRequestService.cleanup_tmp_objects(
                retention_days=retention_days,
                dry_run=dry_run,
            )
        except ValueError as exc:
            abort(400, message=str(exc))


@specie_bp.route("/requests/<string:request_id>/review")
class ReviewSpeciesChangeRequest(MethodView):
    @jwt_required()
    @specie_bp.arguments(SpeciesChangeRequestReviewSchema)
    @specie_bp.response(200, SpeciesChangeRequestSchema)
    @specie_bp.alt_response(400, description="Erro de validação/regra de negócio")
    @specie_bp.alt_response(403, description="Acesso permitido apenas para curadores/admins")
    @specie_bp.alt_response(404, description="Solicitação não encontrada")
    def patch(self, payload, request_id: str):
        _ensure_curator_or_admin()
        identity = get_jwt_identity()

        try:
            return SpeciesChangeRequestService.review_request(
                request_id=request_id,
                reviewer_user_id=str(identity),
                decision=payload.get("decision"),
                review_note=payload.get("review_note"),
                proposed_data_decision=payload.get("proposed_data_decision"),
                proposed_data_fields=payload.get("proposed_data_fields") or [],
                photo_decisions=payload.get("photos") or [],
            )
        except ValueError as exc:
            message = str(exc)
            if "não encontrada" in message.lower():
                abort(404, message=message)
            abort(400, message=message)


@specie_bp.route("/<string:species>/ncbi")
class GetNCBISpeciesData(MethodView):
    @specie_bp.response(200)
    @specie_bp.alt_response(400, description="Parâmetros inválidos")
    @specie_bp.alt_response(404, description="Espécie não encontrada")
    @specie_bp.alt_response(502, description="Falha ao consultar serviço externo")
    def get(self, species: str):
        try:
            data, is_cached = SpeciesService.get_ncbi_data(species, include_cache_meta=True)
            return Response(
                json.dumps(data, ensure_ascii=False, sort_keys=False),
                status=200,
                mimetype="application/json",
                headers={"X-Cache": "HIT" if is_cached else "MISS"},
            )
        except ValueError as exc:
            message = str(exc)
            if message == "Espécie não encontrada.":
                abort(404, message=message)
            abort(400, message=message)
        except RuntimeError as exc:
            sentry_sdk.capture_exception(exc)
            abort(502, message=str(exc))
        except Exception as exc:
            sentry_sdk.capture_exception(exc)
            abort(500, message="Erro interno.")
