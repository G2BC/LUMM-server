import os
from functools import partial
from typing import Any
from urllib.parse import quote_plus
from urllib.request import urlopen as urllib_urlopen

from app.repositories.species_repository import SpeciesRepository
from app.services.cache_service import CacheService
from Bio import Entrez
from flask import current_app


class SpeciesService:
    DEFAULT_PER_PAGE = 30

    @classmethod
    def search(
        cls,
        search: str | None = "",
        lineage: str | None = "",
        country: str | None = "",
        page: int | None = None,
        per_page: int | None = None,
    ) -> dict[str, Any]:
        search = (search or "").strip()
        lineage = (lineage or "").strip()
        country = (country or "").strip()

        if page is not None:
            if not isinstance(page, int) or page < 1:
                raise ValueError("`page` deve ser um inteiro >= 1.")

            per_page = per_page or cls.DEFAULT_PER_PAGE
            pagination = SpeciesRepository.list(search, lineage, country, page, per_page)
            return {
                "items": pagination.items,
                "total": pagination.total,
                "page": page,
                "per_page": per_page,
                "pages": pagination.pages,
            }

        spacies = SpeciesRepository.list(search, lineage, country, None, None)
        return {
            "items": spacies,
            "total": len(spacies),
            "page": None,
            "per_page": None,
            "pages": None,
        }

    @classmethod
    def select_lineage(cls, search: str | None = ""):
        return SpeciesRepository.lineage_select(search)

    @classmethod
    def country_select(cls, search: str | None = ""):
        return SpeciesRepository.country_select(search)

    @classmethod
    def family_select(cls, search: str | None = ""):
        return SpeciesRepository.family_select(search)

    @classmethod
    def species_select(
        cls,
        search: str | None = "",
        exclude_species_id: int | None = None,
    ):
        if exclude_species_id is not None and exclude_species_id < 1:
            raise ValueError("`exclude_species_id` deve ser um inteiro >= 1.")

        return SpeciesRepository.species_select(search, exclude_species_id)

    @classmethod
    def domain_select(cls, domain: str, search: str | None = ""):
        return SpeciesRepository.domain_select(domain, search)

    @classmethod
    def get(cls, species: str | None = ""):
        found = SpeciesRepository.get(species)
        if not found:
            raise ValueError("Espécie não encontrada.")
        return found

    @classmethod
    def get_ncbi_data(
        cls, species: str | None = "", include_cache_meta: bool = False
    ) -> dict[str, Any] | tuple[dict[str, Any], bool]:
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

        Entrez.email = os.getenv("NCBI_EMAIL")
        Entrez.api_key = os.getenv("NCBI_API_KEY")
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
