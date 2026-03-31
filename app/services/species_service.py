import os
from functools import partial
from typing import Any
from urllib.parse import quote_plus
from urllib.request import urlopen as urllib_urlopen

from app.extensions import db
from app.models.species import Species
from app.models.species_similarity import SpeciesSimilarity
from app.repositories.species_change_request_repository import SpeciesChangeRequestRepository
from app.repositories.species_repository import SpeciesRepository
from app.services.cache_service import CacheService
from app.services.species_change_request import SpeciesChangeRequestService
from Bio import Entrez
from flask import current_app
from sqlalchemy.exc import IntegrityError


class SpeciesService:
    DEFAULT_PER_PAGE = 30
    DELETE_AUTO_REVIEW_NOTE = "Solicitação reprovada automaticamente porque a espécie foi excluída."
    PATCH_RELATION_FIELD_MAP = {
        "growth_forms": "growth_form_ids",
        "substrates": "substrate_ids",
        "nutrition_modes": "nutrition_mode_ids",
        "habitats": "habitat_ids",
    }
    PATCH_BIGINT_FIELDS = {
        "mycobank_index_fungorum_id",
        "ncbi_taxonomy_id",
        "inaturalist_taxon_id",
        "unite_taxon_id",
    }

    @classmethod
    def search(
        cls,
        search: str | None = "",
        lineage: str | None = "",
        country: str | None = "",
        is_visible: bool | None = None,
        page: int | None = None,
        per_page: int | None = None,
    ) -> dict[str, Any]:
        search = (search or "").strip()
        lineage = (lineage or "").strip()
        country = (country or "").strip()

        if is_visible is not None and not isinstance(is_visible, bool):
            raise ValueError("`is_visible` deve ser booleano.")

        if page is not None:
            if not isinstance(page, int) or page < 1:
                raise ValueError("`page` deve ser um inteiro >= 1.")

            per_page = per_page or cls.DEFAULT_PER_PAGE
            pagination = SpeciesRepository.list(
                search,
                lineage,
                country,
                is_visible,
                page,
                per_page,
            )
            return {
                "items": pagination.items,
                "total": pagination.total,
                "page": page,
                "per_page": per_page,
                "pages": pagination.pages,
            }

        spacies = SpeciesRepository.list(
            search,
            lineage,
            country,
            is_visible,
            None,
            None,
        )
        return {
            "items": spacies,
            "total": len(spacies),
            "page": None,
            "per_page": None,
            "pages": None,
        }

    @staticmethod
    def select_lineage(search: str | None = ""):
        return SpeciesRepository.lineage_select(search)

    @staticmethod
    def country_select(search: str | None = ""):
        return SpeciesRepository.country_select(search)

    @staticmethod
    def family_select(search: str | None = ""):
        return SpeciesRepository.family_select(search)

    @staticmethod
    def species_select(
        search: str | None = "",
        exclude_species_id: int | None = None,
    ):
        if exclude_species_id is not None and exclude_species_id < 1:
            raise ValueError("`exclude_species_id` deve ser um inteiro >= 1.")

        return SpeciesRepository.species_select(search, exclude_species_id)

    @staticmethod
    def domain_select(domain: str, search: str | None = ""):
        return SpeciesRepository.domain_select(domain, search)

    @staticmethod
    def get(species: str | None = "", is_visible: bool | None = None):
        if is_visible is not None and not isinstance(is_visible, bool):
            raise ValueError("`is_visible` deve ser booleano.")

        found = SpeciesRepository.get(species, is_visible=is_visible)
        if not found:
            raise ValueError("Espécie não encontrada.")
        return found

    @classmethod
    def create(cls, payload: dict[str, Any]):
        normalized_payload = cls._normalize_patch_payload(payload or {})
        lineage = normalized_payload.get("lineage")
        if not isinstance(lineage, str) or not lineage.strip():
            raise ValueError("`lineage` é obrigatório.")
        normalized_payload["lineage"] = lineage.strip()

        mycobank_index_fungorum_id = normalized_payload.get("mycobank_index_fungorum_id")
        if mycobank_index_fungorum_id is None:
            raise ValueError("`mycobank_index_fungorum_id` é obrigatório.")

        scientific_name = normalized_payload.get("scientific_name")
        if scientific_name is None:
            normalized_payload.pop("scientific_name", None)
        elif not isinstance(scientific_name, str):
            raise ValueError("`scientific_name` deve ser string ou null.")
        else:
            normalized_name = scientific_name.strip()
            normalized_payload["scientific_name"] = normalized_name or None

        similar_species_ids = normalized_payload.pop("similar_species_ids", None)
        species = Species(
            scientific_name=normalized_payload.get("scientific_name"),
            lineage=normalized_payload["lineage"],
            mycobank_index_fungorum_id=mycobank_index_fungorum_id,
        )

        try:
            db.session.add(species)
            db.session.flush()

            normalized_payload = cls._enrich_season_payload_with_current(
                species,
                normalized_payload,
            )
            SpeciesChangeRequestService._validate_proposed_data(
                normalized_payload,
                species_id=species.id,
            )
            cls._validate_similar_species_ids(species.id, similar_species_ids)

            SpeciesChangeRequestRepository.apply_species_updates(species, normalized_payload)
            if similar_species_ids is not None:
                species.similar_species_links = [
                    SpeciesSimilarity(similar_species_id=similar_species_id)
                    for similar_species_id in similar_species_ids
                ]

            db.session.add(species)
            db.session.commit()
        except ValueError:
            db.session.rollback()
            raise
        except IntegrityError as exc:
            db.session.rollback()
            raise ValueError(
                "Já existe espécie com `scientific_name` ou identificadores únicos informados."
            ) from exc

        return SpeciesRepository.get(str(species.id))

    @classmethod
    def update(cls, species_id: int, payload: dict[str, Any]):
        if not isinstance(species_id, int) or species_id < 1:
            raise ValueError("`species_id` inválido.")

        species = SpeciesChangeRequestRepository.get_species_by_id(species_id)
        if not species:
            raise ValueError("Espécie não encontrada.")

        normalized_payload = cls._normalize_patch_payload(payload or {})
        similar_species_ids = normalized_payload.pop("similar_species_ids", None)

        normalized_payload = cls._enrich_season_payload_with_current(species, normalized_payload)
        SpeciesChangeRequestService._validate_proposed_data(
            normalized_payload,
            species_id=species_id,
        )
        cls._validate_similar_species_ids(species_id, similar_species_ids)

        SpeciesChangeRequestRepository.apply_species_updates(species, normalized_payload)
        if similar_species_ids is not None:
            species.similar_species_links = [
                SpeciesSimilarity(similar_species_id=similar_species_id)
                for similar_species_id in similar_species_ids
            ]

        db.session.add(species)
        db.session.commit()

        return SpeciesRepository.get(str(species_id))

    @classmethod
    def delete(cls, species_id: int):
        if not isinstance(species_id, int) or species_id < 1:
            raise ValueError("`species_id` inválido.")

        species = SpeciesChangeRequestRepository.get_species_by_id(species_id)
        if not species:
            raise ValueError("Espécie não encontrada.")

        try:
            db.session.delete(species)
            db.session.commit()
            return
        except IntegrityError:
            db.session.rollback()

        species = SpeciesChangeRequestRepository.get_species_by_id(species_id)
        if not species:
            return

        try:
            SpeciesChangeRequestRepository.reject_pending_by_species_id(
                species_id=species_id,
                review_note=cls.DELETE_AUTO_REVIEW_NOTE,
            )
            SpeciesChangeRequestRepository.delete_all_by_species_id(species_id)
            (
                SpeciesSimilarity.query.filter(
                    (SpeciesSimilarity.species_id == species_id)
                    | (SpeciesSimilarity.similar_species_id == species_id)
                ).delete(synchronize_session=False)
            )
            db.session.delete(species)
            db.session.commit()
        except IntegrityError as exc:
            db.session.rollback()
            raise ValueError(
                "Não foi possível excluir a espécie por vínculos relacionados no banco."
            ) from exc

    @classmethod
    def _normalize_patch_payload(cls, payload: dict[str, Any]) -> dict[str, Any]:
        normalized = {}
        for field, value in payload.items():
            mapped_field = cls.PATCH_RELATION_FIELD_MAP.get(field, field)
            if mapped_field in cls.PATCH_BIGINT_FIELDS:
                normalized[mapped_field] = cls._parse_nullable_bigint(mapped_field, value)
                continue
            normalized[mapped_field] = value
        return normalized

    @staticmethod
    def _parse_nullable_bigint(field_name: str, value: Any) -> int | None:
        if value is None:
            return None
        if isinstance(value, bool):
            raise ValueError(f"`{field_name}` deve ser inteiro >= 1 ou null.")
        if isinstance(value, int):
            if value < 1:
                raise ValueError(f"`{field_name}` deve ser inteiro >= 1 ou null.")
            return value
        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                return None
            if not raw.isdigit():
                raise ValueError(f"`{field_name}` deve ser inteiro >= 1 ou null.")
            parsed = int(raw)
            if parsed < 1:
                raise ValueError(f"`{field_name}` deve ser inteiro >= 1 ou null.")
            return parsed

        raise ValueError(f"`{field_name}` deve ser inteiro >= 1 ou null.")

    @staticmethod
    def _enrich_season_payload_with_current(
        species: Species, payload: dict[str, Any]
    ) -> dict[str, Any]:
        has_start = "season_start_month" in payload
        has_end = "season_end_month" in payload
        if not (has_start ^ has_end):
            return payload

        characteristics = getattr(species, "characteristics", None)
        current_start = (
            getattr(characteristics, "season_start_month", None) if characteristics else None
        )
        current_end = (
            getattr(characteristics, "season_end_month", None) if characteristics else None
        )

        normalized = dict(payload)
        if not has_start:
            normalized["season_start_month"] = current_start
        if not has_end:
            normalized["season_end_month"] = current_end
        return normalized

    @staticmethod
    def _validate_similar_species_ids(
        species_id: int,
        similar_species_ids: list[int] | None,
    ) -> None:
        if similar_species_ids is None:
            return

        if not isinstance(similar_species_ids, list):
            raise ValueError("`similar_species_ids` deve ser uma lista de inteiros.")

        normalized: list[int] = []
        for value in similar_species_ids:
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError("`similar_species_ids` deve conter apenas inteiros.")
            if value < 1:
                raise ValueError("`similar_species_ids` deve conter apenas inteiros >= 1.")
            if value == species_id:
                raise ValueError("`similar_species_ids` não pode conter a própria espécie.")
            normalized.append(value)

        unique_ids = sorted(set(normalized))
        if len(unique_ids) != len(normalized):
            raise ValueError("`similar_species_ids` contém IDs duplicados.")

        if not unique_ids:
            return

        existing_ids = {
            found_id
            for (found_id,) in Species.query.with_entities(Species.id)
            .filter(Species.id.in_(unique_ids))
            .all()
        }
        missing_ids = [candidate for candidate in unique_ids if candidate not in existing_ids]
        if missing_ids:
            raise ValueError("`similar_species_ids` contém IDs de espécies inexistentes.")

    @staticmethod
    def get_ncbi_data(
        species: str | None = "", include_cache_meta: bool = False
    ) -> dict[str, Any] | tuple[dict[str, Any], bool]:
        NCBI_EMAIL = os.getenv("NCBI_EMAIL")
        NCBI_API_KEY = os.getenv("NCBI_API_KEY")

        if not NCBI_EMAIL or not NCBI_API_KEY:
            return {}

        species = (species or "").strip()
        if not species:
            raise ValueError("Espécie inválida.")

        taxid = SpeciesRepository.get_ncbi_taxon_id(species)
        if not taxid:
            raise ValueError("Espécie sem NCBI taxonomy ID cadastrado")

        cache_prefix = (
            current_app.config.get("NCBI_CACHE_PREFIX", "ncbi:species").strip() or "ncbi:species"
        )
        cache_ttl_seconds = int(current_app.config.get("NCBI_CACHE_TTL_SECONDS", 86400))
        cache_key = f"{cache_prefix}:{taxid}:v1"

        cached_result = CacheService.get_json(cache_key)
        if isinstance(cached_result, dict):
            if include_cache_meta:
                return cached_result, True
            return cached_result

        Entrez.email = NCBI_EMAIL
        Entrez.api_key = NCBI_API_KEY
        Entrez.max_tries = int(current_app.config.get("NCBI_MAX_TRIES", 1))
        Entrez.sleep_between_tries = float(
            current_app.config.get("NCBI_SLEEP_BETWEEN_TRIES_SECONDS", 0.25)
        )
        ncbi_timeout_seconds = float(current_app.config.get("NCBI_REQUEST_TIMEOUT_SECONDS", 8))
        Entrez.urlopen = partial(urllib_urlopen, timeout=ncbi_timeout_seconds)

        direct_term = f"txid{taxid}[Organism:noexp]"
        subtree_term = f"txid{taxid}[Organism:exp]"

        bancos_config = {
            "taxonomy": {
                "label": "Taxonomy",
                "link": f"https://www.ncbi.nlm.nih.gov/Taxonomy/Browser/wwwtax.cgi?id={taxid}",
            },
            "bioproject": {
                "label": "BioProject",
                "search_url": "https://www.ncbi.nlm.nih.gov/bioproject/?term=",
            },
            "biosample": {
                "label": "BioSample",
                "search_url": "https://www.ncbi.nlm.nih.gov/biosample/?term=",
            },
            "assembly": {
                "label": "Assembly",
                "search_url": "https://www.ncbi.nlm.nih.gov/assembly/?term=",
            },
            "nuccore": {
                "label": "Nucleotide",
                "search_url": "https://www.ncbi.nlm.nih.gov/nuccore/?term=",
            },
            "gene": {
                "label": "Gene",
                "search_url": "https://www.ncbi.nlm.nih.gov/gene/?term=",
            },
            "gds": {
                "label": "GEO DataSets",
                "search_url": "https://www.ncbi.nlm.nih.gov/gds/?term=",
            },
            "sra": {
                "label": "SRA",
                "search_url": "https://www.ncbi.nlm.nih.gov/sra/?term=",
            },
            "protein": {
                "label": "Protein",
                "search_url": "https://www.ncbi.nlm.nih.gov/protein/?term=",
            },
            "ipg": {
                "label": "Identical Protein Groups",
                "search_url": "https://www.ncbi.nlm.nih.gov/ipg/?term=",
            },
            "structure": {
                "label": "Structure",
                "search_url": "https://www.ncbi.nlm.nih.gov/structure/?term=",
            },
            "pmc": {
                "label": "PubMed Central",
                "search_url": "https://pmc.ncbi.nlm.nih.gov/?term=",
            },
        }

        def count_for(db: str, term: str) -> int:
            with Entrez.esearch(db=db, term=term, retmax=0) as handle:
                record = Entrez.read(handle)
                return int(record["Count"])

        resultado = {}

        for db_key, info in bancos_config.items():
            label = info["label"]

            try:
                if db_key == "taxonomy":
                    direct_count = count_for("taxonomy", direct_term)
                    subtree_count = count_for("taxonomy", subtree_term)

                    if direct_count <= 0 and subtree_count <= 0:
                        continue

                    resultado[label] = {
                        "direct_links": {
                            "quantity": direct_count,
                            "link": info["link"],
                        },
                        "subtree_links": {
                            "quantity": subtree_count,
                            "link": info["link"],
                        },
                    }
                    continue

                direct_count = count_for(db_key, direct_term)
                subtree_count = count_for(db_key, subtree_term)

                if direct_count <= 0 and subtree_count <= 0:
                    continue

                resultado[label] = {
                    "direct_links": {
                        "quantity": direct_count,
                        "link": f'{info["search_url"]}{quote_plus(direct_term)}',
                    },
                    "subtree_links": {
                        "quantity": subtree_count,
                        "link": f'{info["search_url"]}{quote_plus(subtree_term)}',
                    },
                }

            except Exception as exc:
                raise RuntimeError(f"Falha ao consultar dados do NCBI na base '{db_key}'") from exc

        CacheService.set_json(cache_key, resultado, ttl_seconds=cache_ttl_seconds)
        if include_cache_meta:
            return resultado, False
        return resultado
