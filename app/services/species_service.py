from typing import Any, Dict, Optional

from app.repositories.species_repository import SpeciesRepository


class SpeciesService:
    DEFAULT_PER_PAGE = 30

    @classmethod
    def search(
        self,
        search: Optional[str] = "",
        lineage: Optional[str] = "",
        country: Optional[str] = "",
        page: Optional[int] = None,
        per_page: Optional[int] = None,
    ) -> Dict[str, Any]:
        search = (search or "").strip()
        lineage = (lineage or "").strip()
        country = (country or "").strip()

        if page is not None:
            if not isinstance(page, int) or page < 1:
                raise ValueError("`page` deve ser um inteiro >= 1.")

            per_page = per_page or self.DEFAULT_PER_PAGE
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
    def select_lineage(self, search: Optional[str] = ""):
        return SpeciesRepository.lineage_select(search)

    @classmethod
    def country_select(self, search: Optional[str] = ""):
        return SpeciesRepository.country_select(search)

    @classmethod
    def get(self, species: Optional[str] = ""):
        return SpeciesRepository.get(species)
