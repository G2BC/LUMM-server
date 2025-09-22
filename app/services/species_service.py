from app.repositories.species_repository import SpeciesRepository


class SpeciesService:
    @classmethod
    def list(search=None, lineage=None, country=None, page=None, per_page=None):
        if page:
            per_page = per_page or 30
            pagination = SpeciesRepository.list(search, lineage, country, page, per_page)
            return {
                "items": pagination.items,
                "total": pagination.total,
                "page": page,
                "per_page": per_page,
                "pages": pagination.pages,
            }

        spacies = SpeciesRepository.list(search, lineage, country)
        return {
            "items": spacies,
            "total": len(spacies),
            "page": None,
            "per_page": None,
            "pages": None,
        }

    @classmethod
    def select_lineage(search=None):
        return SpeciesRepository.lineage_select(search)

    @classmethod
    def country_select(search=None):
        return SpeciesRepository.country_select(search)

    @classmethod
    def get(species=None):
        return SpeciesRepository.get(species)
