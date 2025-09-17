from sqlalchemy.dialects import postgresql as pg
from sqlalchemy.sql import func

from app import db


class SpeciesPhoto(db.Model):
    __tablename__ = "species_photos"
    __table_args__ = (
        db.PrimaryKeyConstraint("species_id", "photo_id", name="pk_species_photo"),
        db.Index("idx_species_photos_species", "species_id"),
    )

    species_id = db.Column(
        db.BigInteger,
        db.ForeignKey("species.id", ondelete="CASCADE"),
        nullable=False,
    )
    photo_id = db.Column(db.BigInteger, nullable=False)  # ID da foto no iNat
    medium_url = db.Column(db.Text, nullable=False)
    original_url = db.Column(db.Text)
    license_code = db.Column(db.Text)  # ex.: 'CC-BY-NC'
    attribution = db.Column(db.Text)  # crédito do autor
    source = db.Column(db.Text, nullable=False, server_default="iNaturalist")
    fetched_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    lumm = db.Column(db.Boolean, nullable=True)
    featured = db.Column(db.Boolean, nullable=True)

    species = db.relationship("Specie", back_populates="photos")

    def __repr__(self):
        return f"<SpeciesPhoto species_id={self.species_id} photo_id={self.photo_id}>"


class Specie(db.Model):
    __tablename__ = "species"
    __table_args__ = (
        db.UniqueConstraint("scientific_name", name="uq_species_scientific_name"),
        db.Index("idx_species_family", "family"),
        db.Index("idx_species_lineage", "lineage"),
        db.Index("idx_species_distribution", "distribution_regions", postgresql_using="gin"),
    )

    id = db.Column(db.BigInteger, primary_key=True)

    # Identidade científica
    scientific_name = db.Column(db.Text, nullable=False)
    authors_abbrev = db.Column(db.Text)
    publication_year = db.Column(db.Integer)

    # Taxonomia (simples)
    lineage = db.Column(db.Text)
    family = db.Column(db.Text)
    group_name = db.Column(db.Text)
    section = db.Column(db.Text)

    # Bioluminescência (NULL = desconhecido)
    lum_mycelium = db.Column(db.Boolean)
    lum_basidiome = db.Column(db.Boolean)
    lum_stipe = db.Column(db.Boolean)
    lum_pileus = db.Column(db.Boolean)
    lum_lamellae = db.Column(db.Boolean)
    lum_spores = db.Column(db.Boolean)

    # Localidade tipo + distribuição
    type_country = db.Column(db.Text)
    distribution_regions = db.Column(
        pg.ARRAY(db.Text),
        nullable=False,
        server_default=db.text("'{}'::text[]"),  # array vazio
    )

    # IDs externos
    mycobank_index_fungorum_id = db.Column(db.BigInteger)
    mycobank_type = db.Column(db.Text)
    ncbi_taxonomy_id = db.Column(db.BigInteger, unique=True)
    inaturalist_taxon_id = db.Column(db.BigInteger, unique=True)
    iucn_redlist = db.Column(db.Text)
    unite_taxon_id = db.Column(db.BigInteger, unique=True)

    # Referências (texto bruto por ora)
    references_raw = db.Column(db.Text)

    # Timestamps
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relações
    photos = db.relationship(
        "SpeciesPhoto",
        back_populates="species",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self):
        return f"<Specie id={self.id} scientific_name={self.scientific_name!r}>"
