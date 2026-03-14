import os
from typing import Any, Optional
from urllib.parse import quote_plus

from app.repositories.species_repository import SpeciesRepository
from Bio import Entrez


class SpeciesService:
    DEFAULT_PER_PAGE = 30

    @classmethod
    def search(
        cls,
        search: Optional[str] = "",
        lineage: Optional[str] = "",
        country: Optional[str] = "",
        page: Optional[int] = None,
        per_page: Optional[int] = None,
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
    def select_lineage(cls, search: Optional[str] = ""):
        return SpeciesRepository.lineage_select(search)

    @classmethod
    def country_select(cls, search: Optional[str] = ""):
        return SpeciesRepository.country_select(search)

    @classmethod
    def family_select(cls, search: Optional[str] = ""):
        return SpeciesRepository.family_select(search)

    @classmethod
    def domain_select(cls, domain: str, search: Optional[str] = ""):
        return SpeciesRepository.domain_select(domain, search)

    @classmethod
    def get(cls, species: Optional[str] = ""):
        found = SpeciesRepository.get(species)
        if not found:
            raise ValueError("Espécie não encontrada.")
        return found

    @classmethod
    def get_ncbi_data(cls, species: Optional[str] = "") -> dict[str, Any]:
        species = (species or "").strip()
        if not species:
            raise ValueError("Espécie inválida.")

        taxid = SpeciesRepository.get_ncbi_taxon_id(species)
        if not taxid:
            raise ValueError("Espécie sem NCBI taxonomy ID cadastrado")

        Entrez.email = os.getenv("NCBI_EMAIL")
        Entrez.api_key = os.getenv("NCBI_API_KEY")

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

        return resultado
