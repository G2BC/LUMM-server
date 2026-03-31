from app.extensions import db
from app.models.growth_form import GrowthForm
from app.models.habitat import Habitat
from app.models.nutrition_mode import NutritionMode
from app.models.species import Species
from app.models.species_characteristics import SpeciesCharacteristics
from app.models.species_similarity import SpeciesSimilarity
from app.models.substrate import Substrate
from app.utils.object_storage import normalize_object_url
from sqlalchemy.orm import selectinload


class SpeciesRepository:
    DOMAIN_MODELS = {
        "growth_form": GrowthForm,
        "nutrition_mode": NutritionMode,
        "substrate": Substrate,
        "habitat": Habitat,
    }

    @classmethod
    def list(
        cls,
        search: str | None = "",
        lineage: str | None = "",
        country: str | None = "",
        is_visible: bool | None = None,
        page: int | None = None,
        per_page: int | None = None,
    ):
        base = Species.query.options(
            selectinload(Species.photos),
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

        filters = []

        if search := (search or "").strip():
            filters.append(Species.scientific_name.ilike(f"%{search}%"))

        if lineage:
            filters.append(Species.lineage.ilike(f"%{lineage}%"))

        if country:
            filters.append(Species.type_country.ilike(f"%{country}%"))
        if is_visible is not None:
            filters.append(Species.is_visible.is_(is_visible))

        if filters:
            base = base.filter(*filters)

        if page:
            return base.paginate(page=page, per_page=per_page, error_out=False)

        return base.all()

    @classmethod
    def get(cls, species: str | None = "", is_visible: bool | None = None):
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

        if is_visible is not None:
            base = base.filter(Species.is_visible.is_(is_visible))

        if species.isdigit():
            id = int(species)
            base = base.filter(Species.id == id)
        else:
            name = species.replace("+", " ")
            base = base.filter(Species.scientific_name.ilike(f"%{name}%"))

        return base.first()

    @classmethod
    def lineage_select(cls, search: str | None = ""):
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
        search: str | None = "",
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
        search: str | None = "",
    ):
        search = (search or "").strip()

        query = Species.query.with_entities(Species.family).distinct()

        if search:
            query = query.filter(Species.family.ilike(f"%{search}%"))

        query = query.order_by(Species.family.asc())

        families = query.all()

        options = [{"label": family, "value": family} for (family,) in families if family]

        return options

    @classmethod
    def species_select(
        cls,
        search: str | None = "",
        exclude_species_id: int | None = None,
    ):
        search = (search or "").strip()
        query = Species.query.options(selectinload(Species.photos))

        if search:
            query = query.filter(Species.scientific_name.ilike(f"%{search}%"))
        if exclude_species_id is not None:
            query = query.filter(Species.id != exclude_species_id)

        species_list = query.order_by(Species.scientific_name.asc()).all()

        def pick_photo(species: Species) -> str | None:
            photos = getattr(species, "photos", None) or []
            if not photos:
                return None

            ordered = sorted(photos, key=lambda photo: getattr(photo, "photo_id", 0))
            featured = next(
                (photo for photo in ordered if bool(getattr(photo, "featured", False))),
                None,
            )
            chosen = featured or ordered[0]
            return normalize_object_url(getattr(chosen, "medium_url", None))

        return [
            {
                "id": item.id,
                "label": item.scientific_name,
                "photo": pick_photo(item),
            }
            for item in species_list
        ]

    @classmethod
    def domain_select(
        cls,
        domain: str,
        search: str | None = "",
    ):
        model = cls.DOMAIN_MODELS.get((domain or "").strip().lower())
        if not model:
            allowed = ", ".join(sorted(cls.DOMAIN_MODELS.keys()))
            raise ValueError(f"`domain` inválido. Use um de: {allowed}")

        search = (search or "").strip()
        query = model.query.filter(model.is_active.is_(True))

        if search:
            query = query.filter(
                (model.label_pt.ilike(f"%{search}%"))
                | (model.label_en.ilike(f"%{search}%"))
                | (model.slug.ilike(f"%{search}%"))
            )

        items = query.order_by(model.label_pt.asc()).all()

        return [
            {
                "value": item.id,
                "label_pt": item.label_pt,
                "label_en": item.label_en,
            }
            for item in items
        ]

    @classmethod
    def get_ncbi_taxon_id(cls, species_id: str | None = ""):
        species_id = (species_id or "").strip()
        if not species_id or not species_id.isdigit():
            return None

        species = (
            Species.query.filter(Species.id == int(species_id))
            .where(Species.ncbi_taxonomy_id.is_not(None))
            .first()
        )

        if not species:
            return None

        return species.ncbi_taxonomy_id

    @classmethod
    def exists_by_id(cls, species_id: str | None = "") -> bool:
        if not species_id:
            return False

        species = Species.query.with_entities(Species.id).filter(Species.id == species_id).first()
        return species is not None

    @staticmethod
    def stage(species) -> None:
        """add + flush to generate the species.id without committing."""
        db.session.add(species)
        db.session.flush()

    @staticmethod
    def save(species) -> None:
        """add + commit."""
        db.session.add(species)
        db.session.commit()

    @staticmethod
    def rollback() -> None:
        db.session.rollback()

    @staticmethod
    def delete(species) -> None:
        """delete + commit. IntegrityError propagates to the caller."""
        db.session.delete(species)
        db.session.commit()
