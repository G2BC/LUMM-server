from marshmallow import EXCLUDE, Schema, ValidationError, fields, validates_schema


class SpeciesPhotoRequestInputSchema(Schema):
    object_key = fields.String(required=True)
    bucket_name = fields.String(allow_none=True)
    original_filename = fields.String(allow_none=True)
    mime_type = fields.String(allow_none=True)
    size_bytes = fields.Integer(allow_none=True)
    checksum_sha256 = fields.String(allow_none=True)
    caption = fields.String(allow_none=True)
    license_code = fields.String(allow_none=True)
    attribution = fields.String(allow_none=True)


class SpeciesChangeRequestCreateSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    species_id = fields.Integer(required=True)
    proposed_data = fields.Dict(required=False, load_default=dict)
    request_note = fields.String(allow_none=True)
    requester_name = fields.String(allow_none=True)
    requester_email = fields.Email(allow_none=True)
    requester_institution = fields.String(allow_none=True)
    photos = fields.List(
        fields.Nested(SpeciesPhotoRequestInputSchema),
        required=False,
        load_default=list,
    )

    @validates_schema
    def validate_has_changes(self, data, **kwargs):
        has_data = bool(data.get("proposed_data") or {})
        has_photos = bool(data.get("photos") or [])
        if not has_data and not has_photos:
            raise ValidationError(
                "Informe ao menos `proposed_data` ou uma foto em `photos`.",
                field_name="proposed_data",
            )


class SpeciesPhotoRequestSchema(Schema):
    id = fields.String(dump_only=True)
    object_key = fields.String(dump_only=True)
    bucket_name = fields.String(allow_none=True, dump_only=True)
    original_filename = fields.String(allow_none=True, dump_only=True)
    mime_type = fields.String(allow_none=True, dump_only=True)
    size_bytes = fields.Integer(allow_none=True, dump_only=True)
    checksum_sha256 = fields.String(allow_none=True, dump_only=True)
    caption = fields.String(allow_none=True, dump_only=True)
    license_code = fields.String(allow_none=True, dump_only=True)
    attribution = fields.String(allow_none=True, dump_only=True)
    status = fields.String(dump_only=True)
    created_at = fields.DateTime(dump_only=True)


class SpeciesChangeRequestSchema(Schema):
    id = fields.String(dump_only=True)
    species_id = fields.String(dump_only=True)
    requested_by_user_id = fields.String(allow_none=True, dump_only=True)
    requester_name = fields.String(allow_none=True, dump_only=True)
    requester_email = fields.String(allow_none=True, dump_only=True)
    requester_institution = fields.String(allow_none=True, dump_only=True)
    request_note = fields.String(allow_none=True, dump_only=True)
    proposed_data = fields.Dict(dump_only=True)
    status = fields.String(dump_only=True)
    review_note = fields.String(allow_none=True, dump_only=True)
    reviewed_by_user_id = fields.String(allow_none=True, dump_only=True)
    reviewed_at = fields.DateTime(allow_none=True, dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    photos = fields.List(fields.Nested(SpeciesPhotoRequestSchema), dump_only=True)


class SpeciesChangeRequestPaginationSchema(Schema):
    items = fields.List(fields.Nested(SpeciesChangeRequestSchema))
    total = fields.Integer()
    page = fields.Integer(allow_none=True)
    per_page = fields.Integer(allow_none=True)
    pages = fields.Integer(allow_none=True)


class SpeciesChangeRequestReviewSchema(Schema):
    decision = fields.String(required=True)
    review_note = fields.String(allow_none=True)

    @validates_schema
    def validate_decision(self, data, **kwargs):
        if (data.get("decision") or "").lower() not in {"approve", "reject"}:
            raise ValidationError(
                "`decision` deve ser `approve` ou `reject`.",
                field_name="decision",
            )


class SpeciesPhotoUploadUrlRequestSchema(Schema):
    filename = fields.String(required=True)
    mime_type = fields.String(required=True)
    size_bytes = fields.Integer(required=True)
    species_id = fields.Integer(allow_none=True)


class SpeciesPhotoUploadUrlResponseSchema(Schema):
    upload_url = fields.String(required=True, dump_only=True)
    form_fields = fields.Dict(
        required=True,
        dump_only=True,
        attribute="fields",
        data_key="fields",
    )
    bucket_name = fields.String(required=True, dump_only=True)
    object_key = fields.String(required=True, dump_only=True)
    expires_at = fields.DateTime(required=True, dump_only=True)


class SpeciesTmpCleanupResponseSchema(Schema):
    bucket = fields.String(required=True, dump_only=True)
    retention_days = fields.Integer(required=True, dump_only=True)
    candidates = fields.Integer(required=True, dump_only=True)
    deleted = fields.Integer(required=True, dump_only=True)
    dry_run = fields.Boolean(required=True, dump_only=True)
