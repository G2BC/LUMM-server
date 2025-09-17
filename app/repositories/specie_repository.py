from app.models.specie import Specie
from sqlalchemy import and_, or_
from sqlalchemy.orm import selectinload


def get_species_with_photos(search: str = ""):
    base = Specie.query.options(selectinload(Specie.photos)).order_by(Specie.scientific_name.asc())

    search = (search or "").strip()
    if not search:
        return base.all()

    terms = [t.strip() for t in search.split() if t.strip()]
    filters = [
        or_(
            Specie.scientific_name.ilike(f"%{t}%"),
            Specie.lineage.ilike(f"%{t}%"),
        )
        for t in terms
    ]

    return base.filter(and_(*filters)).all()


def get_species_with_photos_pagination(search: str = "", page: int = 1, per_page: int = 20):
    base = Specie.query.options(selectinload(Specie.photos)).order_by(Specie.scientific_name.asc())

    search = (search or "").strip()
    if not search:
        return base.paginate(page=page, per_page=per_page, error_out=False)

    terms = [t.strip() for t in search.split() if t.strip()]
    filters = [
        or_(
            Specie.scientific_name.ilike(f"%{t}%"),
            Specie.lineage.ilike(f"%{t}%"),
        )
        for t in terms
    ]

    return base.filter(and_(*filters)).paginate(page=page, per_page=per_page, error_out=False)
