import mimetypes
import os
import re
import time
from datetime import timedelta
from typing import Any
from uuid import uuid4

import app.utils.object_storage as object_storage
import requests
from app.models.growth_form import GrowthForm
from app.models.habitat import Habitat
from app.models.nutrition_mode import NutritionMode
from app.models.species_change_request import SpeciesChangeRequest
from app.models.substrate import Substrate
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
        "edible",
        "cultivation",
        "cultivation_pt",
        "finding_tips",
        "finding_tips_pt",
        "nearby_trees",
        "nearby_trees_pt",
        "curiosities",
        "curiosities_pt",
        "general_description",
        "general_description_pt",
        "colors",
        "colors_pt",
        "size_cm",
        "growth_form_ids",
        "substrate_ids",
        "nutrition_mode_ids",
        "habitat_ids",
        "season_start_month",
        "season_end_month",
        "distribution_regions",
        "references_raw",
    }
    UPLOAD_EXPIRES_SECONDS = 900
    UPLOAD_HEAD_MAX_ATTEMPTS = 4
    UPLOAD_HEAD_RETRY_SECONDS = 0.35
    TMP_PREFIX = "species/pending/"
    FINAL_PREFIX = "species/"
    CHARACTERISTICS_FIELDS = {
        "lum_mycelium",
        "lum_basidiome",
        "lum_stipe",
        "lum_pileus",
        "lum_lamellae",
        "lum_spores",
        "edible",
        "cultivation",
        "cultivation_pt",
        "finding_tips",
        "finding_tips_pt",
        "nearby_trees",
        "nearby_trees_pt",
        "curiosities",
        "curiosities_pt",
        "general_description",
        "general_description_pt",
        "colors",
        "colors_pt",
        "size_cm",
        "growth_form_ids",
        "substrate_ids",
        "nutrition_mode_ids",
        "habitat_ids",
        "season_start_month",
        "season_end_month",
    }
    RELATION_FIELD_MODELS = {
        "growth_form_ids": GrowthForm,
        "substrate_ids": Substrate,
        "nutrition_mode_ids": NutritionMode,
        "habitat_ids": Habitat,
    }
    TRANSLATABLE_FIELDS = {
        "colors": "colors_pt",
        "cultivation": "cultivation_pt",
        "finding_tips": "finding_tips_pt",
        "nearby_trees": "nearby_trees_pt",
        "curiosities": "curiosities_pt",
        "general_description": "general_description_pt",
    }
    TRANSLATABLE_PAIR_MAP = {
        **TRANSLATABLE_FIELDS,
        **{pt_field: en_field for en_field, pt_field in TRANSLATABLE_FIELDS.items()},
    }

    @classmethod
    def create_request(cls, payload: dict[str, Any], requester_user_id: str | None = None):
        species_id = payload["species_id"]
        species = SpeciesChangeRequestRepository.get_species_by_id(species_id)
        if not species:
            raise ValueError("Espécie não encontrada.")

        proposed_data = payload.get("proposed_data") or {}
        source_lang = (payload.get("source_lang") or "pt").strip().lower()
        if source_lang not in {"pt", "en"}:
            raise ValueError("`source_lang` deve ser `pt` ou `en`.")

        proposed_data = cls._normalize_translatable_fields(proposed_data, source_lang)
        invalid_fields = sorted(set(proposed_data.keys()) - cls.ALLOWED_SPECIES_FIELDS)
        if invalid_fields:
            raise ValueError(
                f"Campos não permitidos em `proposed_data`: {', '.join(invalid_fields)}"
            )
        cls._validate_proposed_data(proposed_data, species_id=species_id)

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

    @staticmethod
    def _normalize_optional_text(value: Any) -> str:
        if value is None:
            return ""
        if not isinstance(value, str):
            raise ValueError("Campos textuais traduzíveis devem ser string.")
        return value.strip()

    @classmethod
    def _normalize_translatable_fields(
        cls, proposed_data: dict[str, Any], source_lang: str
    ) -> dict[str, Any]:
        normalized = dict(proposed_data or {})
        queued_texts: list[str] = []
        queued_fields: list[tuple[str, str, str]] = []

        for en_field, pt_field in cls.TRANSLATABLE_FIELDS.items():
            source_text = cls._normalize_optional_text(
                normalized.get(en_field) or normalized.get(pt_field)
            )
            normalized.pop(en_field, None)
            normalized.pop(pt_field, None)
            if not source_text:
                continue
            queued_fields.append((en_field, pt_field, source_text))
            queued_texts.append(source_text)

        if not queued_fields:
            return normalized

        translated_texts = cls._translate_texts_with_deepl(queued_texts, source_lang=source_lang)
        if len(translated_texts) != len(queued_fields):
            raise ValueError("Falha ao traduzir campos textuais.")

        for index, (en_field, pt_field, source_text) in enumerate(queued_fields):
            translated_text = (translated_texts[index] or "").strip() or source_text
            if source_lang == "pt":
                normalized[pt_field] = source_text
                normalized[en_field] = translated_text
            else:
                normalized[en_field] = source_text
                normalized[pt_field] = translated_text

        return normalized

    @classmethod
    def _translate_texts_with_deepl(cls, texts: list[str], source_lang: str) -> list[str]:
        if not texts:
            return []

        env = current_app.config.get("APP_ENV")
        if env == "development":
            return texts

        api_key = (current_app.config.get("DEEPL_API_KEY") or "").strip()
        if not api_key:
            raise ValueError("DEEPL_API_KEY não configurada no servidor.")

        api_url = (
            current_app.config.get("DEEPL_API_URL") or "https://api-free.deepl.com/v2/translate"
        ).strip()
        timeout_seconds = float(current_app.config.get("DEEPL_TIMEOUT_SECONDS", 45))

        source = "PT" if source_lang == "pt" else "EN"
        target = "EN" if source_lang == "pt" else "PT-BR"

        payload: list[tuple[str, str]] = [("source_lang", source), ("target_lang", target)]
        for text in texts:
            payload.append(("text", text))

        try:
            response = requests.post(
                api_url,
                data=payload,
                headers={
                    "Authorization": f"DeepL-Auth-Key {api_key}",
                    "Accept": "application/json",
                },
                timeout=timeout_seconds,
            )
        except requests.RequestException as exc:
            raise ValueError(f"Falha ao conectar no serviço de tradução: {exc}") from exc

        if response.status_code >= 400:
            details = (response.text or "").strip()
            raise ValueError(
                f"Erro na tradução automática (DeepL): {details or response.status_code}."
            )

        data = response.json() if response.content else {}
        translations = data.get("translations") if isinstance(data, dict) else None
        if not isinstance(translations, list):
            raise ValueError("Resposta inválida da tradução automática (DeepL).")

        result: list[str] = []
        for item in translations:
            if not isinstance(item, dict):
                continue
            text = item.get("text")
            if isinstance(text, str):
                result.append(text)

        return result

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

    @staticmethod
    def _validate_proposed_data(
        proposed_data: dict[str, Any], species_id: int | None = None
    ) -> None:
        edible = proposed_data.get("edible")
        if edible is not None and not isinstance(edible, bool):
            raise ValueError("`edible` deve ser booleano ou null.")

        size_cm = proposed_data.get("size_cm")
        if size_cm is not None:
            if isinstance(size_cm, bool) or not isinstance(size_cm, int | float):
                raise ValueError("`size_cm` deve ser numérico.")
            if size_cm < 0:
                raise ValueError("`size_cm` deve ser >= 0.")

        growth_form_ids = proposed_data.get("growth_form_ids")
        if growth_form_ids is not None:
            if not isinstance(growth_form_ids, list):
                raise ValueError("`growth_form_ids` deve ser uma lista de inteiros.")
            normalized_growth_form_ids = []
            for growth_form_value in growth_form_ids:
                if isinstance(growth_form_value, bool) or not isinstance(growth_form_value, int):
                    raise ValueError("`growth_form_ids` deve conter apenas inteiros.")
                if growth_form_value < 1:
                    raise ValueError("`growth_form_ids` deve conter apenas inteiros >= 1.")
                normalized_growth_form_ids.append(growth_form_value)
            unique_growth_form_ids = sorted(set(normalized_growth_form_ids))
            if len(unique_growth_form_ids) != len(normalized_growth_form_ids):
                raise ValueError("`growth_form_ids` contém IDs duplicados.")
            if unique_growth_form_ids:
                active_count = GrowthForm.query.filter(
                    GrowthForm.id.in_(unique_growth_form_ids),
                    GrowthForm.is_active.is_(True),
                ).count()
                if active_count != len(unique_growth_form_ids):
                    raise ValueError("`growth_form_ids` contém IDs inválidos ou inativos.")

        substrate_ids = proposed_data.get("substrate_ids")
        if substrate_ids is not None:
            if not isinstance(substrate_ids, list):
                raise ValueError("`substrate_ids` deve ser uma lista de inteiros.")
            normalized_substrate_ids = []
            for substrate_value in substrate_ids:
                if isinstance(substrate_value, bool) or not isinstance(substrate_value, int):
                    raise ValueError("`substrate_ids` deve conter apenas inteiros.")
                if substrate_value < 1:
                    raise ValueError("`substrate_ids` deve conter apenas inteiros >= 1.")
                normalized_substrate_ids.append(substrate_value)
            unique_substrate_ids = sorted(set(normalized_substrate_ids))
            if len(unique_substrate_ids) != len(normalized_substrate_ids):
                raise ValueError("`substrate_ids` contém IDs duplicados.")
            if unique_substrate_ids:
                active_count = Substrate.query.filter(
                    Substrate.id.in_(unique_substrate_ids),
                    Substrate.is_active.is_(True),
                ).count()
                if active_count != len(unique_substrate_ids):
                    raise ValueError("`substrate_ids` contém IDs inválidos ou inativos.")

        nutrition_mode_ids = proposed_data.get("nutrition_mode_ids")
        if nutrition_mode_ids is not None:
            if not isinstance(nutrition_mode_ids, list):
                raise ValueError("`nutrition_mode_ids` deve ser uma lista de inteiros.")
            normalized_nutrition_mode_ids = []
            for nutrition_mode_value in nutrition_mode_ids:
                if isinstance(nutrition_mode_value, bool) or not isinstance(
                    nutrition_mode_value, int
                ):
                    raise ValueError("`nutrition_mode_ids` deve conter apenas inteiros.")
                if nutrition_mode_value < 1:
                    raise ValueError("`nutrition_mode_ids` deve conter apenas inteiros >= 1.")
                normalized_nutrition_mode_ids.append(nutrition_mode_value)

            unique_nutrition_mode_ids = sorted(set(normalized_nutrition_mode_ids))
            if len(unique_nutrition_mode_ids) != len(normalized_nutrition_mode_ids):
                raise ValueError("`nutrition_mode_ids` contém IDs duplicados.")

            if unique_nutrition_mode_ids:
                active_count = NutritionMode.query.filter(
                    NutritionMode.id.in_(unique_nutrition_mode_ids),
                    NutritionMode.is_active.is_(True),
                ).count()
                if active_count != len(unique_nutrition_mode_ids):
                    raise ValueError("`nutrition_mode_ids` contém IDs inválidos ou inativos.")

        habitat_ids = proposed_data.get("habitat_ids")
        if habitat_ids is not None:
            if not isinstance(habitat_ids, list):
                raise ValueError("`habitat_ids` deve ser uma lista de inteiros.")
            normalized_habitat_ids = []
            for hid in habitat_ids:
                if isinstance(hid, bool) or not isinstance(hid, int):
                    raise ValueError("`habitat_ids` deve conter apenas inteiros.")
                if hid < 1:
                    raise ValueError("`habitat_ids` deve conter apenas inteiros >= 1.")
                normalized_habitat_ids.append(hid)

            unique_habitat_ids = sorted(set(normalized_habitat_ids))
            if len(unique_habitat_ids) != len(normalized_habitat_ids):
                raise ValueError("`habitat_ids` contém IDs duplicados.")

            if unique_habitat_ids:
                active_count = Habitat.query.filter(
                    Habitat.id.in_(unique_habitat_ids),
                    Habitat.is_active.is_(True),
                ).count()
                if active_count != len(unique_habitat_ids):
                    raise ValueError("`habitat_ids` contém IDs inválidos ou inativos.")

        start = proposed_data.get("season_start_month")
        end = proposed_data.get("season_end_month")

        if start is None and end is None:
            return
        if start is None or end is None:
            raise ValueError(
                "`season_start_month` e `season_end_month` devem ser informados juntos."
            )
        if not isinstance(start, int) or not isinstance(end, int):
            raise ValueError("`season_start_month` e `season_end_month` devem ser inteiros.")
        if start < 1 or start > 12 or end < 1 or end > 12:
            raise ValueError("`season_start_month` e `season_end_month` devem estar entre 1 e 12.")

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
        decision: str | None,
        review_note: str | None,
        proposed_data_decision: str | None = None,
        proposed_data_fields: list[dict[str, Any]] | None = None,
        photo_decisions: list[dict[str, Any]] | None = None,
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
        normalized_proposed_data_fields = cls._normalize_proposed_data_field_decisions(
            proposed_data_fields or []
        )
        proposed_data_decision_map = {
            item["field"]: item["decision"] for item in normalized_proposed_data_fields
        }
        proposed_data_decision_map = cls._expand_translatable_decision_map(
            proposed_data_decision_map, req.proposed_data or {}
        )
        normalized_photo_decisions = cls._normalize_photo_decisions(photo_decisions or [])
        photo_decision_map = {
            item["photo_request_id"]: item["decision"] for item in normalized_photo_decisions
        }

        has_proposed_data = bool(req.proposed_data or {})
        if not normalized_decision:
            proposed_fields_count = len((req.proposed_data or {}).keys())
            if (
                has_proposed_data
                and not normalized_proposed_data_decision
                and len(proposed_data_decision_map) != proposed_fields_count
            ):
                raise ValueError(
                    "Informe `proposed_data_decision` ou decisões para todos os campos "
                    "em `proposed_data_fields` quando `decision` não for enviado."
                )
            if req.photos and len(photo_decision_map) != len(req.photos):
                raise ValueError(
                    "Informe decisão para todas as fotos quando `decision` não for enviado."
                )

        approved_items = 0
        rejected_items = 0

        approved_proposed_data = {}
        if not has_proposed_data and proposed_data_decision_map:
            raise ValueError(
                "`proposed_data_fields` só pode ser usado quando a solicitação "
                "tiver `proposed_data`."
            )
        if has_proposed_data:
            proposed_data_keys = list((req.proposed_data or {}).keys())
            unknown_proposed_fields = sorted(
                set(proposed_data_decision_map.keys()) - set(proposed_data_keys)
            )
            if unknown_proposed_fields:
                raise ValueError(
                    "Campos inválidos em `proposed_data_fields`: "
                    + ", ".join(unknown_proposed_fields)
                )

            for field in proposed_data_keys:
                field_final_decision = (
                    proposed_data_decision_map.get(field)
                    or normalized_proposed_data_decision
                    or normalized_decision
                )
                if not field_final_decision:
                    raise ValueError(f"Decisão ausente para o campo `{field}`.")

                if field_final_decision == "approve":
                    approved_proposed_data[field] = req.proposed_data[field]
                    approved_items += 1
                else:
                    rejected_items += 1

            if approved_proposed_data:
                species = SpeciesChangeRequestRepository.get_species_by_id(req.species_id)
                if not species:
                    raise ValueError("Espécie não encontrada.")
                SpeciesChangeRequestRepository.apply_species_updates(
                    species, approved_proposed_data
                )

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
    def _normalize_review_decision(value: str | None, field_name: str) -> str | None:
        normalized = (value or "").strip().lower()
        if not normalized:
            return None
        if normalized not in {"approve", "reject"}:
            raise ValueError(f"`{field_name}` deve ser `approve` ou `reject`.")
        return normalized

    @classmethod
    def _expand_translatable_decision_map(
        cls, decision_map: dict[str, str], proposed_data: dict[str, Any]
    ) -> dict[str, str]:
        if not decision_map:
            return decision_map

        expanded = dict(decision_map)
        for field, decision in list(decision_map.items()):
            paired_field = cls.TRANSLATABLE_PAIR_MAP.get(field)
            if not paired_field or paired_field not in proposed_data:
                continue

            paired_decision = expanded.get(paired_field)
            if paired_decision and paired_decision != decision:
                raise ValueError(
                    "Campos traduzíveis devem ter a mesma decisão: "
                    f"`{field}` e `{paired_field}`."
                )
            expanded[paired_field] = decision

        return expanded

    @classmethod
    def _normalize_proposed_data_field_decisions(
        cls, proposed_data_fields: list[dict[str, Any]]
    ) -> list[dict[str, str]]:
        normalized = []
        seen_fields = set()

        for item in proposed_data_fields:
            field_name = str(item.get("field") or "").strip()
            if not field_name:
                raise ValueError("`proposed_data_fields.field` é obrigatório.")
            if field_name in seen_fields:
                raise ValueError(f"`field` duplicado em `proposed_data_fields`: {field_name}.")
            seen_fields.add(field_name)

            decision = cls._normalize_review_decision(
                item.get("decision"), "proposed_data_fields.decision"
            )
            if not decision:
                raise ValueError("`proposed_data_fields.decision` é obrigatório.")

            normalized.append({"field": field_name, "decision": decision})

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
    def cleanup_tmp_objects(cls, retention_days: int | None = None, dry_run: bool = True):
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

        for photo in photos_payload:
            if "lumm" not in photo or photo.get("lumm") is None:
                photo["lumm"] = True
                continue

            if not isinstance(photo.get("lumm"), bool):
                raise ValueError("`photos.lumm` deve ser booleano.")

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
        relation_label_cache = {field: {} for field in cls.RELATION_FIELD_MODELS.keys()}
        for req in requests:
            cls._attach_preview_urls(req)
            cls._attach_enriched_proposed_data(req, relation_label_cache)

            species_id = getattr(req, "species_id", None)
            if species_id not in species_cache:
                species_cache[species_id] = (
                    SpeciesChangeRequestRepository.get_species_by_id(species_id)
                    if species_id is not None
                    else None
                )

            species = species_cache.get(species_id)
            cls._attach_current_data(req, species, relation_label_cache)

    @classmethod
    def _attach_enriched_proposed_data(cls, req, relation_label_cache: dict[str, dict]) -> None:
        proposed_data = getattr(req, "proposed_data", None) or {}
        enriched = {}

        for field, value in proposed_data.items():
            model = cls.RELATION_FIELD_MODELS.get(field)
            if model and isinstance(value, list):
                enriched[field] = cls._resolve_relation_items(
                    value,
                    model,
                    relation_label_cache[field],
                )
                continue
            enriched[field] = value

        req.proposed_data_enriched = enriched

    @staticmethod
    def _resolve_relation_items(
        ids: list[Any],
        model,
        cache: dict[int, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        normalized_ids = []
        for value in ids:
            if isinstance(value, bool):
                continue
            try:
                parsed = int(value)
            except (TypeError, ValueError):
                continue
            if parsed < 1:
                continue
            normalized_ids.append(parsed)

        if not normalized_ids:
            return []

        missing_ids = sorted(set(normalized_ids) - set(cache.keys()))
        if missing_ids:
            rows = model.query.filter(model.id.in_(missing_ids)).order_by(model.id.asc()).all()
            for row in rows:
                cache[row.id] = {
                    "id": row.id,
                    "label_pt": row.label_pt,
                    "label_en": row.label_en,
                }

        return [
            cache.get(
                item_id,
                {
                    "id": item_id,
                    "label_pt": None,
                    "label_en": None,
                },
            )
            for item_id in normalized_ids
        ]

    @classmethod
    def _attach_current_data(cls, req, species, relation_label_cache: dict[str, dict]) -> None:
        proposed_data = getattr(req, "proposed_data", None) or {}
        current_data = {}
        characteristics = getattr(species, "characteristics", None) if species else None

        for field in proposed_data.keys():
            if field == "habitat_ids" and species:
                if characteristics is None:
                    current_data[field] = []
                else:
                    habitats = getattr(characteristics, "habitats", None) or []
                    current_data[field] = [
                        {
                            "id": habitat.id,
                            "label_pt": habitat.label_pt,
                            "label_en": habitat.label_en,
                        }
                        for habitat in habitats
                    ]
                    for habitat in habitats:
                        relation_label_cache[field][habitat.id] = {
                            "id": habitat.id,
                            "label_pt": habitat.label_pt,
                            "label_en": habitat.label_en,
                        }
                continue
            if field == "growth_form_ids" and species:
                if characteristics is None:
                    current_data[field] = []
                else:
                    growth_forms = getattr(characteristics, "growth_forms", None) or []
                    current_data[field] = [
                        {
                            "id": growth_form.id,
                            "label_pt": growth_form.label_pt,
                            "label_en": growth_form.label_en,
                        }
                        for growth_form in growth_forms
                    ]
                    for growth_form in growth_forms:
                        relation_label_cache[field][growth_form.id] = {
                            "id": growth_form.id,
                            "label_pt": growth_form.label_pt,
                            "label_en": growth_form.label_en,
                        }
                continue
            if field == "substrate_ids" and species:
                if characteristics is None:
                    current_data[field] = []
                else:
                    substrates = getattr(characteristics, "substrates", None) or []
                    current_data[field] = [
                        {
                            "id": substrate.id,
                            "label_pt": substrate.label_pt,
                            "label_en": substrate.label_en,
                        }
                        for substrate in substrates
                    ]
                    for substrate in substrates:
                        relation_label_cache[field][substrate.id] = {
                            "id": substrate.id,
                            "label_pt": substrate.label_pt,
                            "label_en": substrate.label_en,
                        }
                continue
            if field == "nutrition_mode_ids" and species:
                if characteristics is None:
                    current_data[field] = []
                else:
                    nutrition_modes = getattr(characteristics, "nutrition_modes", None) or []
                    current_data[field] = [
                        {
                            "id": nutrition_mode.id,
                            "label_pt": nutrition_mode.label_pt,
                            "label_en": nutrition_mode.label_en,
                        }
                        for nutrition_mode in nutrition_modes
                    ]
                    for nutrition_mode in nutrition_modes:
                        relation_label_cache[field][nutrition_mode.id] = {
                            "id": nutrition_mode.id,
                            "label_pt": nutrition_mode.label_pt,
                            "label_en": nutrition_mode.label_en,
                        }
                continue
            if field in SpeciesChangeRequestService.CHARACTERISTICS_FIELDS and species:
                if characteristics is not None:
                    current_data[field] = getattr(characteristics, field, None)
                else:
                    current_data[field] = getattr(species, field, None)
                continue
            current_data[field] = getattr(species, field, None) if species else None

        req.current_data = current_data

    @staticmethod
    def _build_preview_url(photo, expires_in_seconds: int) -> str | None:
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
