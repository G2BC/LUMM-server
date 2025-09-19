from app.models.species import Species
from sqlalchemy import and_, or_
from sqlalchemy.orm import selectinload


def get_species_with_photos(search: str = ""):
    base = Species.query.options(selectinload(Species.photos)).order_by(
        Species.scientific_name.asc()
    )

    search = (search or "").strip()
    if not search:
        return base.all()

    terms = [t.strip() for t in search.split() if t.strip()]
    filters = [
        or_(
            Species.scientific_name.ilike(f"%{t}%"),
            Species.lineage.ilike(f"%{t}%"),
        )
        for t in terms
    ]

    return base.filter(and_(*filters)).all()


def get_species_with_photos_pagination(search: str = "", page: int = 1, per_page: int = 30):
    base = Species.query.options(selectinload(Species.photos)).order_by(
        Species.scientific_name.asc()
    )

    search = (search or "").strip()
    if not search:
        return base.paginate(page=page, per_page=per_page, error_out=False)

    terms = [t.strip() for t in search.split() if t.strip()]
    filters = [
        or_(
            Species.scientific_name.ilike(f"%{t}%"),
            Species.lineage.ilike(f"%{t}%"),
        )
        for t in terms
    ]

    return base.filter(and_(*filters)).paginate(page=page, per_page=per_page, error_out=False)


def select_lineage(search: str = ""):
    search = (search or "").strip()

    query = Species.query.with_entities(Species.lineage).distinct()

    if search:
        query = query.filter(Species.lineage.ilike(f"%{search}%"))

    query = query.order_by(Species.lineage.asc())

    lineages = query.all()

    options = [{"label": lineage, "value": lineage} for (lineage,) in lineages if lineage]

    return options
