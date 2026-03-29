from sqlalchemy.dialects import postgresql as pg
from sqlalchemy.sql import func

from app.extensions import db


class Species(db.Model):
    __tablename__ = "species"
    __table_args__ = (
        db.UniqueConstraint("scientific_name", name="uq_species_scientific_name"),
        db.Index("idx_species_family", "family"),
        db.Index("idx_species_lineage", "lineage"),
        db.Index("idx_species_distribution", "distribution_regions", postgresql_using="gin"),
    )

    id = db.Column(db.BigInteger, primary_key=True)

    # Identidade científica
    scientific_name = db.Column(db.Text, nullable=True)

    # Taxonomia (simples)
    lineage = db.Column(db.Text)
    family = db.Column(db.Text)
    group_name = db.Column(db.Text)
    section = db.Column(db.Text)

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
    is_visible = db.Column(db.Boolean, nullable=False, server_default=db.false())

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
    taxonomy = db.relationship(
        "Taxon",
        back_populates="species",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    characteristics = db.relationship(
        "SpeciesCharacteristics",
        back_populates="species",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    similar_species_links = db.relationship(
        "SpeciesSimilarity",
        foreign_keys="SpeciesSimilarity.species_id",
        back_populates="species",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self):
        return f"<Specie id={self.id} scientific_name={self.scientific_name!r}>"
