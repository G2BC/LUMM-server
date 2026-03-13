import os
import time
from typing import Any, Optional

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

        ncbi_taxonomy_id = SpeciesRepository.get_ncbi_taxon_id(species)
        if not ncbi_taxonomy_id:
            raise ValueError("Espécie sem NCBI taxonomy ID cadastrado")

        Entrez.email = os.getenv("NCBI_EMAIL")
        Entrez.api_key = os.getenv("NCBI_API_KEY")
        taxid = ncbi_taxonomy_id
        term = f"txid{taxid}[Organism:exp]"

        bancos_config = {
            "bioproject": ["BioProject", "https://www.ncbi.nlm.nih.gov/bioproject/"],
            "biosample": ["BioSample", "https://www.ncbi.nlm.nih.gov/biosample/"],
            "gds": ["GEO DataSets", "https://www.ncbi.nlm.nih.gov/gds/"],
            "ipg": ["Identical Protein Groups", "https://www.ncbi.nlm.nih.gov/ipg/"],
            "nucleotide": ["Nucleotide", "https://www.ncbi.nlm.nih.gov/nuccore/"],
            "protein": ["Protein", "https://www.ncbi.nlm.nih.gov/protein/"],
            "structure": ["Structure", "https://www.ncbi.nlm.nih.gov/structure/"],
            "pmc": ["PubMed Central", "https://pmc.ncbi.nlm.nih.gov/search/"],
            "sra": ["SRA", "https://www.ncbi.nlm.nih.gov/sra/"],
            "genome": ["Genome Datasets", "https://www.ncbi.nlm.nih.gov/datasets/genome/"],
        }

        resultado = {}

        for db_key, info in bancos_config.items():
            handle = None
            try:
                handle = Entrez.esearch(db=db_key, term=term, retmax=0)
                record = Entrez.read(handle)

                count = int(record["Count"])

                if db_key == "genome":
                    url = f"{info[1]}?taxon={taxid}"
                elif db_key == "bioproject":
                    url = f"{info[1]}?term=txid{taxid}[Organism:noexp]"
                elif db_key == "pmc":
                    url = f"{info[1]}?term={term}&pmfilter_Fulltext=off"
                else:
                    url = f"{info[1]}?term={term}"

                if count <= 0:
                    continue

                resultado[info[0]] = {
                    "quantity": count,
                    "link": url,
                }

                time.sleep(0.15)
            except Exception as exc:
                raise RuntimeError(f"Falha ao consultar dados do NCBI na base '{db_key}'") from exc
            finally:
                if handle:
                    handle.close()

        return resultado
