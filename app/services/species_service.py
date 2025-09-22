from app.repositories.species_repository import (
    get_species,
    get_species_with_photos,
    get_species_with_photos_pagination,
    select_lineage,
    select_species_country,
)


def list_species_with_photos(search="", lineage="", country="", page=None, per_page=None):
    if page and per_page:
        pagination = get_species_with_photos_pagination(search, lineage, country, page, per_page)
        return {
            "items": pagination.items,
            "total": pagination.total,
            "page": page,
            "per_page": per_page,
            "pages": pagination.pages,
        }

    spacies = get_species_with_photos(search, lineage, country)
    return {
        "items": spacies,
        "total": len(spacies),
        "page": None,
        "per_page": None,
        "pages": None,
    }


def lineage_select(search=""):
    return select_lineage(search)


def species_country_select(search=""):
    return select_species_country(search)


def get_species_service(species=""):
    return get_species(species)
