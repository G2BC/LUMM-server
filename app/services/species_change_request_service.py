import mimetypes
import os
import re
import time
from datetime import timedelta
from typing import Any, Optional
from uuid import uuid4

import app.utils.object_storage as object_storage
from app.models.species_change_request import SpeciesChangeRequest
from app.repositories.species_change_request_repository import SpeciesChangeRequestRepository
from app.repositories.user_repository import UserRepository
from botocore.exceptions import BotoCoreError, ClientError
from flask import current_app


class SpeciesChangeRequestService:
    DEFAULT_PER_PAGE = 20
    MAX_PER_PAGE = 100
    ALLOWED_SPECIES_FIELDS = {
        "scientific_name",
        "group_name",
        "section",
        "lum_mycelium",
        "lum_basidiome",
        "lum_stipe",
        "lum_pileus",
        "lum_lamellae",
        "lum_spores",
        "distribution_regions",
        "mycobank_index_fungorum_id",
        "mycobank_type",
        "ncbi_taxonomy_id",
        "inaturalist_taxon_id",
        "iucn_redlist",
        "unite_taxon_id",
        "references_raw",
    }
    UPLOAD_EXPIRES_SECONDS = 900
    UPLOAD_HEAD_MAX_ATTEMPTS = 4
    UPLOAD_HEAD_RETRY_SECONDS = 0.35
    TMP_PREFIX = "species/pending/"
    FINAL_PREFIX = "species/approved/"
    CHARACTERISTICS_FIELDS = {
        "lum_mycelium",
        "lum_basidiome",
        "lum_stipe",
        "lum_pileus",
        "lum_lamellae",
        "lum_spores",
    }

    @classmethod
    def create_request(cls, payload: dict[str, Any], requester_user_id: Optional[str] = None):
        species_id = payload["species_id"]
        species = SpeciesChangeRequestRepository.get_species_by_id(species_id)
        if not species:
            raise ValueError("Espécie não encontrada.")

        proposed_data = payload.get("proposed_data") or {}
        invalid_fields = sorted(set(proposed_data.keys()) - cls.ALLOWED_SPECIES_FIELDS)
        if invalid_fields:
            raise ValueError(
                f"Campos não permitidos em `proposed_data`: {', '.join(invalid_fields)}"
            )

        photos_payload = payload.get("photos") or []
        cls._validate_photos_payload(photos_payload)
        cls._validate_uploaded_objects(photos_payload)

        requested_by_user_id = None
        if requester_user_id is not None:
            user = UserRepository.get_by_id(requester_user_id)
            if user:
                requested_by_user_id = user.id

        return SpeciesChangeRequestRepository.create(
            species_id=species_id,
            proposed_data=proposed_data,
            request_note=(payload.get("request_note") or None),
            requester_name=(payload.get("requester_name") or None),
            requester_email=(payload.get("requester_email") or None),
            requester_institution=(payload.get("requester_institution") or None),
            requested_by_user_id=requested_by_user_id,
            photos_payload=photos_payload,
        )

    @classmethod
    def generate_upload_url(cls, filename: str, mime_type: str, size_bytes: int, species_id=None):
        normalized_mime = (mime_type or "").strip().lower()
        allowed_mimes = set(current_app.config.get("SPECIES_PHOTO_ALLOWED_MIME_TYPES", []))
        max_size = int(current_app.config["SPECIES_PHOTO_MAX_BYTES"])

        if normalized_mime not in allowed_mimes:
            raise ValueError("Tipo de arquivo não permitido.")
        if not isinstance(size_bytes, int) or size_bytes < 1:
            raise ValueError("`size_bytes` deve ser > 0.")
        if size_bytes > max_size:
            raise ValueError(f"Arquivo excede o limite de {max_size} bytes.")

        ext = cls._safe_extension(filename, normalized_mime)
        sid = f"{species_id}" if species_id is not None else "unknown"
        object_key = f"{cls.TMP_PREFIX}{sid}/{uuid4().hex}{ext}"
        tmp_bucket = current_app.config["MINIO_TMP_BUCKET"]

        try:
            signed = object_storage.generate_presigned_post(
                bucket=tmp_bucket,
                key=object_key,
                content_type=normalized_mime,
                max_size_bytes=max_size,
                expires_in_seconds=cls.UPLOAD_EXPIRES_SECONDS,
            )
        except (object_storage.ObjectStorageError, BotoCoreError, ClientError) as exc:
            raise ValueError(f"Falha ao gerar URL de upload: {exc}")

        return {
            "upload_url": signed["url"],
            "fields": signed["fields"],
            "bucket_name": tmp_bucket,
            "object_key": object_key,
            "expires_at": object_storage.utc_now() + timedelta(seconds=cls.UPLOAD_EXPIRES_SECONDS),
        }

    @classmethod
    def list_requests(cls, status=None, page=None, per_page=None):
        normalized_status = (status or "").strip().lower() or None
        if normalized_status and normalized_status not in SpeciesChangeRequest.STATUSES:
            raise ValueError(
                "`status` inválido. Use: pending, approved, partial_approved, rejected."
            )

        if page is None and per_page is None:
            items = SpeciesChangeRequestRepository.list(normalized_status, None, None)
            cls._enrich_requests(items)
            return {
                "items": items,
                "total": len(items),
                "page": None,
                "per_page": None,
                "pages": None,
            }

        if page is None:
            page = 1
        if per_page is None:
            per_page = cls.DEFAULT_PER_PAGE

        if not isinstance(page, int) or page < 1:
            raise ValueError("`page` deve ser um inteiro >= 1.")
        if not isinstance(per_page, int) or per_page < 1:
            raise ValueError("`per_page` deve ser um inteiro >= 1.")
        if per_page > cls.MAX_PER_PAGE:
            raise ValueError(f"`per_page` deve ser <= {cls.MAX_PER_PAGE}.")

        pagination = SpeciesChangeRequestRepository.list(normalized_status, page, per_page)
        cls._enrich_requests(pagination.items)
        return {
            "items": pagination.items,
            "total": pagination.total,
            "page": page,
            "per_page": per_page,
            "pages": pagination.pages,
        }

    @classmethod
    def get_request(cls, request_id: str):
        req = SpeciesChangeRequestRepository.get_by_id(cls._parse_id(request_id))
        if not req:
            raise ValueError("Solicitação não encontrada.")
        cls._enrich_requests([req])
        return req

    @classmethod
    def review_request(
        cls,
        request_id: str,
        reviewer_user_id: str,
        decision: Optional[str],
        review_note: Optional[str],
        proposed_data_decision: Optional[str] = None,
        photo_decisions: Optional[list[dict[str, Any]]] = None,
    ):
        req = SpeciesChangeRequestRepository.get_by_id(cls._parse_id(request_id))
        if not req:
            raise ValueError("Solicitação não encontrada.")
        if req.status != SpeciesChangeRequest.STATUS_PENDING:
            raise ValueError("Solicitação já revisada.")

        reviewer = UserRepository.get_by_id(reviewer_user_id)
        if not reviewer:
            raise ValueError("Usuário autenticado não encontrado.")

        normalized_decision = cls._normalize_review_decision(decision, "decision")
        normalized_proposed_data_decision = cls._normalize_review_decision(
            proposed_data_decision, "proposed_data_decision"
        )
        normalized_photo_decisions = cls._normalize_photo_decisions(photo_decisions or [])
        photo_decision_map = {
            item["photo_request_id"]: item["decision"] for item in normalized_photo_decisions
        }

        has_proposed_data = bool(req.proposed_data or {})
        if not normalized_decision:
            if has_proposed_data and not normalized_proposed_data_decision:
                raise ValueError(
                    "Informe `proposed_data_decision` quando `decision` não for enviado."
                )
            if req.photos and len(photo_decision_map) != len(req.photos):
                raise ValueError(
                    "Informe decisão para todas as fotos quando `decision` não for enviado."
                )

        proposed_data_final_decision = None
        if has_proposed_data:
            proposed_data_final_decision = normalized_proposed_data_decision or normalized_decision

        approved_items = 0
        rejected_items = 0

        if proposed_data_final_decision == "approve":
            species = SpeciesChangeRequestRepository.get_species_by_id(req.species_id)
            if not species:
                raise ValueError("Espécie não encontrada.")
            SpeciesChangeRequestRepository.apply_species_updates(species, req.proposed_data or {})
            approved_items += 1
        elif proposed_data_final_decision == "reject":
            rejected_items += 1

        photo_ids = {photo.id for photo in req.photos}
        unknown_photo_ids = sorted(set(photo_decision_map.keys()) - photo_ids)
        if unknown_photo_ids:
            raise ValueError(
                "IDs de foto inválidos em `photos`: "
                + ", ".join(str(photo_id) for photo_id in unknown_photo_ids)
            )

        for photo in req.photos:
            photo_final_decision = photo_decision_map.get(photo.id) or normalized_decision
            if not photo_final_decision:
                raise ValueError(f"Decisão ausente para foto {photo.id}.")

            if photo_final_decision == "approve":
                promoted_bucket, promoted_key = cls._promote_object_to_final(photo, req.species_id)
                photo.bucket_name = promoted_bucket
                photo.object_key = promoted_key
                SpeciesChangeRequestRepository.create_or_skip_species_photo_from_request(
                    req.species_id, photo
                )
                photo.status = SpeciesChangeRequest.STATUS_APPROVED
                approved_items += 1
            else:
                cls._delete_tmp_object_if_exists(photo)
                photo.status = SpeciesChangeRequest.STATUS_REJECTED
                rejected_items += 1

        if approved_items > 0 and rejected_items > 0:
            status = SpeciesChangeRequest.STATUS_PARTIAL_APPROVED
        elif approved_items > 0:
            status = SpeciesChangeRequest.STATUS_APPROVED
        else:
            status = SpeciesChangeRequest.STATUS_REJECTED

        reviewed = SpeciesChangeRequestRepository.save_review(
            req=req,
            status=status,
            reviewed_by_user_id=reviewer.id,
            review_note=review_note,
        )
        cls._enrich_requests([reviewed])
        return reviewed

    @staticmethod
    def _normalize_review_decision(value: Optional[str], field_name: str) -> Optional[str]:
        normalized = (value or "").strip().lower()
        if not normalized:
            return None
        if normalized not in {"approve", "reject"}:
            raise ValueError(f"`{field_name}` deve ser `approve` ou `reject`.")
        return normalized

    @classmethod
    def _normalize_photo_decisions(
        cls, photo_decisions: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        normalized = []
        seen_ids = set()

        for item in photo_decisions:
            raw_photo_id = item.get("photo_request_id")
            try:
                photo_id = int(raw_photo_id)
            except (TypeError, ValueError):
                raise ValueError("`photo_request_id` deve ser inteiro positivo.")
            if photo_id < 1:
                raise ValueError("`photo_request_id` deve ser inteiro positivo.")
            if photo_id in seen_ids:
                raise ValueError(f"`photo_request_id` duplicado: {photo_id}.")
            seen_ids.add(photo_id)

            decision = cls._normalize_review_decision(item.get("decision"), "photos.decision")
            if not decision:
                raise ValueError("`photos.decision` é obrigatório.")
            normalized.append({"photo_request_id": photo_id, "decision": decision})

        return normalized

    @staticmethod
    def _parse_id(raw_id: str) -> int:
        try:
            value = int(raw_id)
        except (TypeError, ValueError):
            raise ValueError("ID inválido.")
        if value < 1:
            raise ValueError("ID inválido.")
        return value

    @classmethod
    def cleanup_tmp_objects(cls, retention_days: Optional[int] = None, dry_run: bool = True):
        days = retention_days or int(current_app.config["SPECIES_TMP_RETENTION_DAYS"])
        if days < 1:
            raise ValueError("`retention_days` deve ser >= 1.")

        threshold = object_storage.utc_now() - timedelta(days=days)
        tmp_bucket = current_app.config["MINIO_TMP_BUCKET"]
        objects = object_storage.list_objects(tmp_bucket, cls.TMP_PREFIX)

        deleted = 0
        candidates = 0
        for item in objects:
            last_modified = item.get("LastModified")
            if not last_modified or last_modified >= threshold:
                continue
            candidates += 1
            if not dry_run:
                object_storage.delete_object(tmp_bucket, item["Key"])
                deleted += 1

        return {
            "bucket": tmp_bucket,
            "retention_days": days,
            "candidates": candidates,
            "deleted": deleted,
            "dry_run": dry_run,
        }

    @classmethod
    def _validate_photos_payload(cls, photos_payload: list[dict[str, Any]]) -> None:
        max_photos = int(current_app.config["SPECIES_REQUEST_MAX_PHOTOS"])
        if len(photos_payload) > max_photos:
            raise ValueError(f"Máximo de {max_photos} fotos por solicitação.")

    @classmethod
    def _validate_uploaded_objects(cls, photos_payload: list[dict[str, Any]]) -> None:
        if not photos_payload:
            return

        tmp_bucket = current_app.config["MINIO_TMP_BUCKET"]
        max_size = int(current_app.config["SPECIES_PHOTO_MAX_BYTES"])
        allowed_mimes = set(current_app.config.get("SPECIES_PHOTO_ALLOWED_MIME_TYPES", []))
        for photo in photos_payload:
            key = (photo.get("object_key") or "").strip()
            if not key.startswith(cls.TMP_PREFIX):
                raise ValueError("`object_key` inválido para bucket temporário.")

            declared_bucket = (photo.get("bucket_name") or tmp_bucket).strip()
            if declared_bucket != tmp_bucket:
                raise ValueError("Fotos devem vir do bucket temporário.")

            try:
                meta = cls._head_object_with_retry(tmp_bucket, key)
            except ValueError:
                raise
            except (object_storage.ObjectStorageError, BotoCoreError, ClientError):
                raise ValueError("Falha ao validar arquivo no bucket temporário.")

            content_length = int(meta.get("ContentLength") or 0)
            content_type = (meta.get("ContentType") or "").lower()
            if content_length < 1 or content_length > max_size:
                raise ValueError("Arquivo com tamanho fora do limite permitido.")
            if content_type not in allowed_mimes:
                raise ValueError("Arquivo com tipo MIME não permitido.")

            photo["bucket_name"] = tmp_bucket
            photo["size_bytes"] = content_length
            if not photo.get("mime_type"):
                photo["mime_type"] = content_type

    @classmethod
    def _head_object_with_retry(cls, bucket: str, key: str) -> dict[str, Any]:
        attempts = max(1, cls.UPLOAD_HEAD_MAX_ATTEMPTS)

        for attempt in range(1, attempts + 1):
            try:
                return object_storage.head_object(bucket, key)
            except (object_storage.ObjectStorageError, BotoCoreError, ClientError) as exc:
                if not cls._is_not_found_error(exc):
                    raise
                if attempt < attempts:
                    time.sleep(cls.UPLOAD_HEAD_RETRY_SECONDS)

        raise ValueError("Arquivo não encontrado no bucket temporário.")

    @staticmethod
    def _is_not_found_error(exc: Exception) -> bool:
        if not isinstance(exc, ClientError):
            return False

        code = str((exc.response.get("Error") or {}).get("Code") or "").strip()
        status = (exc.response.get("ResponseMetadata") or {}).get("HTTPStatusCode")
        return code in {"404", "NoSuchKey", "NotFound"} or status == 404

    @classmethod
    def _promote_object_to_final(cls, photo, species_id: int) -> tuple[str, str]:
        src_bucket = (photo.bucket_name or current_app.config["MINIO_TMP_BUCKET"]).strip()
        src_key = photo.object_key
        tmp_bucket = current_app.config["MINIO_TMP_BUCKET"]
        final_bucket = current_app.config["MINIO_FINAL_BUCKET"]

        if src_bucket == final_bucket:
            return final_bucket, src_key
        if src_bucket != tmp_bucket:
            raise ValueError("Bucket de origem inválido para promoção.")

        basename = os.path.basename(src_key)
        safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", basename)
        dest_key = f"{cls.FINAL_PREFIX}{species_id}/{photo.request_id}_{photo.id}_{safe_name}"
        try:
            object_storage.copy_object(src_bucket, src_key, final_bucket, dest_key)
            object_storage.delete_object(src_bucket, src_key)
        except (object_storage.ObjectStorageError, BotoCoreError, ClientError) as exc:
            raise ValueError(f"Falha ao promover foto para bucket final: {exc}")

        return final_bucket, dest_key

    @staticmethod
    def _safe_extension(filename: str, mime_type: str) -> str:
        guessed = mimetypes.guess_extension(mime_type) or ""
        source_ext = os.path.splitext(filename or "")[1].lower()
        if source_ext in {".jpg", ".jpeg", ".png", ".webp"}:
            return source_ext
        if guessed in {".jpe"}:
            return ".jpg"
        if guessed in {".jpg", ".jpeg", ".png", ".webp"}:
            return guessed
        return ".bin"

    @classmethod
    def _delete_tmp_object_if_exists(cls, photo) -> None:
        src_bucket = (photo.bucket_name or current_app.config["MINIO_TMP_BUCKET"]).strip()
        src_key = photo.object_key
        tmp_bucket = current_app.config["MINIO_TMP_BUCKET"]
        if src_bucket != tmp_bucket:
            return
        try:
            object_storage.delete_object(src_bucket, src_key)
        except (object_storage.ObjectStorageError, BotoCoreError, ClientError):
            # Cleanup best-effort: a revisão não deve falhar por lixo já removido.
            return

    @classmethod
    def _attach_preview_urls(cls, req) -> None:
        expires_in = int(current_app.config.get("SPECIES_REQUEST_PREVIEW_URL_EXPIRES_SECONDS", 900))
        for photo in req.photos:
            photo.preview_url = cls._build_preview_url(photo, expires_in)

    @classmethod
    def _enrich_requests(cls, requests) -> None:
        species_cache = {}
        for req in requests:
            cls._attach_preview_urls(req)

            species_id = getattr(req, "species_id", None)
            if species_id not in species_cache:
                species_cache[species_id] = (
                    SpeciesChangeRequestRepository.get_species_by_id(species_id)
                    if species_id is not None
                    else None
                )

            species = species_cache.get(species_id)
            cls._attach_current_data(req, species)

    @staticmethod
    def _attach_current_data(req, species) -> None:
        proposed_data = getattr(req, "proposed_data", None) or {}
        current_data = {}
        characteristics = getattr(species, "characteristics", None) if species else None

        for field in proposed_data.keys():
            if field in SpeciesChangeRequestService.CHARACTERISTICS_FIELDS and species:
                if characteristics is not None:
                    current_data[field] = getattr(characteristics, field, None)
                else:
                    current_data[field] = getattr(species, field, None)
                continue
            current_data[field] = getattr(species, field, None) if species else None

        req.current_data = current_data

    @staticmethod
    def _build_preview_url(photo, expires_in_seconds: int) -> Optional[str]:
        source_url = (getattr(photo, "source_url", None) or "").strip()
        if source_url.startswith(("http://", "https://")):
            return source_url

        bucket = (getattr(photo, "bucket_name", None) or "").strip()
        key = (getattr(photo, "object_key", None) or "").strip()
        if not bucket or not key:
            return None

        try:
            return object_storage.generate_presigned_get_url(bucket, key, expires_in_seconds)
        except (object_storage.ObjectStorageError, BotoCoreError, ClientError):
            return None
