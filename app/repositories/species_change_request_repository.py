from typing import Optional

import app.utils.object_storage as object_storage
from app.extensions import db
from app.models.species import Species, SpeciesPhoto
from app.models.species_change_request import SpeciesChangeRequest, SpeciesPhotoRequest
from sqlalchemy.orm import selectinload


class SpeciesChangeRequestRepository:
    @classmethod
    def create(
        cls,
        species_id: int,
        proposed_data: dict,
        request_note: Optional[str],
        requester_name: Optional[str],
        requester_email: Optional[str],
        requester_institution: Optional[str],
        requested_by_user_id: Optional[int],
        photos_payload: list[dict],
    ) -> SpeciesChangeRequest:
        req = SpeciesChangeRequest(
            species_id=species_id,
            proposed_data=proposed_data or {},
            request_note=request_note,
            requester_name=requester_name,
            requester_email=requester_email,
            requester_institution=requester_institution,
            requested_by_user_id=requested_by_user_id,
            status=SpeciesChangeRequest.STATUS_PENDING,
        )

        for photo in photos_payload:
            req.photos.append(
                SpeciesPhotoRequest(
                    object_key=photo["object_key"],
                    bucket_name=photo.get("bucket_name"),
                    original_filename=photo.get("original_filename"),
                    mime_type=photo.get("mime_type"),
                    size_bytes=photo.get("size_bytes"),
                    checksum_sha256=photo.get("checksum_sha256"),
                    caption=photo.get("caption"),
                    license_code=photo.get("license_code"),
                    attribution=photo.get("attribution"),
                    rights_holder=photo.get("rights_holder"),
                    source_url=photo.get("source_url"),
                    declaration_accepted_at=photo.get("declaration_accepted_at"),
                )
            )

        db.session.add(req)
        db.session.commit()
        return cls.get_by_id(req.id)

    @classmethod
    def list(
        cls,
        status: Optional[str] = None,
        page: Optional[int] = None,
        per_page: Optional[int] = None,
    ):
        query = SpeciesChangeRequest.query.options(
            selectinload(SpeciesChangeRequest.photos)
        ).order_by(SpeciesChangeRequest.created_at.desc())

        if status:
            query = query.filter(SpeciesChangeRequest.status == status)

        if page:
            return query.paginate(page=page, per_page=per_page, error_out=False)

        return query.all()

    @classmethod
    def get_by_id(cls, request_id: int) -> Optional[SpeciesChangeRequest]:
        return (
            SpeciesChangeRequest.query.options(selectinload(SpeciesChangeRequest.photos))
            .filter(SpeciesChangeRequest.id == request_id)
            .first()
        )

    @classmethod
    def get_species_by_id(cls, species_id: int) -> Optional[Species]:
        return Species.query.filter(Species.id == species_id).first()

    @classmethod
    def apply_species_updates(cls, species: Species, proposed_data: dict) -> Species:
        for field, value in proposed_data.items():
            setattr(species, field, value)

        db.session.add(species)
        return species

    @classmethod
    def create_or_skip_species_photo_from_request(
        cls, species_id: int, photo_request: SpeciesPhotoRequest
    ) -> bool:
        url = cls._build_object_url(photo_request)
        formatted_attribution = cls._format_attribution(photo_request)
        already_exists = (
            SpeciesPhoto.query.filter(
                SpeciesPhoto.species_id == species_id,
                SpeciesPhoto.original_url == url,
            ).first()
            is not None
        )
        if already_exists:
            return False

        db.session.add(
            SpeciesPhoto(
                species_id=species_id,
                photo_id=-photo_request.id,
                medium_url=url,
                original_url=url,
                license_code=photo_request.license_code,
                attribution=formatted_attribution,
                rights_holder=photo_request.rights_holder,
                source_url=photo_request.source_url,
                declaration_accepted_at=photo_request.declaration_accepted_at,
                source="LUMM-Upload",
                lumm=True,
            )
        )
        return True

    @staticmethod
    def _build_object_url(photo_request: SpeciesPhotoRequest) -> str:
        if photo_request.bucket_name:
            return object_storage.build_public_object_url(
                photo_request.bucket_name, photo_request.object_key
            )
        return f"minio://{photo_request.object_key}"

    @staticmethod
    def _normalize_license_display(license_code: Optional[str]) -> str:
        raw = (license_code or "").strip().upper()
        if not raw:
            return "LICENSE NOT PROVIDED"
        if raw == "ALL-RIGHTS-RESERVED":
            return "ALL RIGHTS RESERVED"

        normalized = raw
        if normalized.startswith("CC-"):
            normalized = "CC " + normalized[3:]
        normalized = normalized.replace("-4.0", "").replace("-3.0", "").replace("-2.0", "")
        normalized = normalized.replace("-1.0", "")
        return normalized

    @staticmethod
    def _rights_clause(license_code: Optional[str]) -> str:
        raw = (license_code or "").strip().upper()
        if raw == "ALL-RIGHTS-RESERVED":
            return "all rights reserved"
        if raw.startswith("CC0"):
            return "no rights reserved"
        return "some rights reserved"

    @classmethod
    def _format_attribution(cls, photo_request: SpeciesPhotoRequest) -> str:
        uploader = (photo_request.attribution or "").strip() or "unknown uploader"
        rights_holder = (photo_request.rights_holder or "").strip() or uploader
        rights_clause = cls._rights_clause(photo_request.license_code)
        license_display = cls._normalize_license_display(photo_request.license_code)
        return (
            f"(c) {rights_holder}, {rights_clause} ({license_display}), " f"uploaded by {uploader}"
        )

    @classmethod
    def save_review(
        cls,
        req: SpeciesChangeRequest,
        status: str,
        reviewed_by_user_id: int,
        review_note: Optional[str],
    ) -> SpeciesChangeRequest:
        req.status = status
        req.reviewed_by_user_id = reviewed_by_user_id
        req.review_note = review_note
        req.reviewed_at = db.func.now()

        db.session.add(req)
        db.session.commit()
        return cls.get_by_id(req.id)
