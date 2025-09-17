from app.repositories.specie_repository import (
    get_species_with_photos,
    get_species_with_photos_pagination,
)


def list_species_with_photos(search="", page=None, per_page=None):
    if page and per_page:
        pagination = get_species_with_photos_pagination(search, page, per_page)
        return {
            "items": pagination.items,
            "total": pagination.total,
            "page": page,
            "per_page": per_page,
            "pages": pagination.pages,
        }

    spacies = get_species_with_photos(search)
    return {
        "items": spacies,
        "total": len(spacies),
        "page": None,
        "per_page": None,
        "pages": None,
    }
