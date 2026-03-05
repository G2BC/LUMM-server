from typing import Optional

from app.models.species import Species
from app.models.species_characteristics import SpeciesCharacteristics
from app.models.species_similarity import SpeciesSimilarity
from sqlalchemy.orm import selectinload


class SpeciesRepository:
    @classmethod
    def list(
        cls,
        search: Optional[str] = "",
        lineage: Optional[str] = "",
        country: Optional[str] = "",
        page: Optional[int] = None,
        per_page: Optional[int] = None,
    ):
        base = Species.query.options(
            selectinload(Species.photos),
            selectinload(Species.characteristics).selectinload(
                SpeciesCharacteristics.nutrition_modes
            ),
            selectinload(Species.characteristics).selectinload(SpeciesCharacteristics.habitats),
            selectinload(Species.characteristics).selectinload(SpeciesCharacteristics.growth_forms),
            selectinload(Species.characteristics).selectinload(SpeciesCharacteristics.substrates),
            selectinload(Species.similar_species_links),
        ).order_by(Species.scientific_name.asc())

        filters = []

        if search := (search or "").strip():
            filters.append(Species.scientific_name.ilike(f"%{search}%"))

        if lineage:
            filters.append(Species.lineage.ilike(f"%{lineage}%"))

        if country:
            filters.append(Species.type_country.ilike(f"%{country}%"))

        if filters:
            base = base.filter(*filters)

        if page:
            return base.paginate(page=page, per_page=per_page, error_out=False)

        return base.all()

    @classmethod
    def get(cls, species: Optional[str] = ""):
        if not species:
            return None

        base = Species.query.options(
            selectinload(Species.photos),
            selectinload(Species.taxonomy),
            selectinload(Species.characteristics).selectinload(
                SpeciesCharacteristics.nutrition_modes
            ),
            selectinload(Species.characteristics).selectinload(SpeciesCharacteristics.habitats),
            selectinload(Species.characteristics).selectinload(SpeciesCharacteristics.growth_forms),
            selectinload(Species.characteristics).selectinload(SpeciesCharacteristics.substrates),
            selectinload(Species.similar_species_links).selectinload(
                SpeciesSimilarity.similar_species
            ),
        ).order_by(Species.scientific_name.asc())

        if species.isdigit():
            id = int(species)
            base = base.filter(Species.id == id)
        else:
            name = species.replace("+", " ")
            base = base.filter(Species.scientific_name.ilike(f"%{name}%"))

        return base.first()

    @classmethod
    def lineage_select(cls, search: Optional[str] = ""):
        search = (search or "").strip()

        query = Species.query.with_entities(Species.lineage).distinct()

        if search:
            query = query.filter(Species.lineage.ilike(f"%{search}%"))

        query = query.order_by(Species.lineage.asc())

        lineages = query.all()

        options = [{"label": lineage, "value": lineage} for (lineage,) in lineages if lineage]

        return options

    @classmethod
    def country_select(
        cls,
        search: Optional[str] = "",
    ):
        search = (search or "").strip()

        query = Species.query.with_entities(Species.type_country).distinct()

        if search:
            query = query.filter(Species.type_country.ilike(f"%{search}%"))

        query = query.order_by(Species.type_country.asc())

        countries = query.all()

        options = [{"label": country, "value": country} for (country,) in countries if country]

        return options

    @classmethod
    def family_select(
        cls,
        search: Optional[str] = "",
    ):
        search = (search or "").strip()

        query = Species.query.with_entities(Species.family).distinct()

        if search:
            query = query.filter(Species.family.ilike(f"%{search}%"))

        query = query.order_by(Species.family.asc())

        families = query.all()

        options = [{"label": family, "value": family} for (family,) in families if family]

        return options
