from app.models.species import Species
from sqlalchemy.orm import selectinload


def get_species_with_photos(search: str = "", lineage: str = "", country: str = ""):
    base = Species.query.options(selectinload(Species.photos)).order_by(
        Species.scientific_name.asc()
    )

    filters = []

    if search := (search or "").strip():
        filters.append(Species.scientific_name.ilike(f"%{search}%"))

    if lineage:
        filters.append(Species.lineage.ilike(f"%{lineage}%"))

    if country:
        filters.append(Species.type_country.ilike(f"%{country}%"))

    if filters:
        base = base.filter(*filters)

    return base.all()


def get_species_with_photos_pagination(
    search: str = "", lineage: str = "", country: str = "", page: int = 1, per_page: int = 30
):
    base = Species.query.options(selectinload(Species.photos)).order_by(
        Species.scientific_name.asc()
    )

    filters = []

    if search := (search or "").strip():
        filters.append(Species.scientific_name.ilike(f"%{search}%"))

    if lineage:
        filters.append(Species.lineage.ilike(f"%{lineage}%"))

    if country:
        filters.append(Species.type_country.ilike(f"%{country}%"))

    if filters:
        base = base.filter(*filters)

    return base.paginate(page=page, per_page=per_page, error_out=False)


def select_lineage(search: str = ""):
    search = (search or "").strip()

    query = Species.query.with_entities(Species.lineage).distinct()

    if search:
        query = query.filter(Species.lineage.ilike(f"%{search}%"))

    query = query.order_by(Species.lineage.asc())

    lineages = query.all()

    options = [{"label": lineage, "value": lineage} for (lineage,) in lineages if lineage]

    return options


def select_species_country(search: str = ""):
    search = (search or "").strip()

    query = Species.query.with_entities(Species.type_country).distinct()

    if search:
        query = query.filter(Species.type_country.ilike(f"%{search}%"))

    query = query.order_by(Species.type_country.asc())

    countries = query.all()

    options = [{"label": country, "value": country} for (country,) in countries if country]

    return options
