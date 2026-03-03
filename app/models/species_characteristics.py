from app.extensions import db


class SpeciesCharacteristics(db.Model):
    __tablename__ = "species_characteristics"

    species_id = db.Column(
        db.BigInteger,
        db.ForeignKey("species.id", ondelete="CASCADE"),
        primary_key=True,
    )
    lum_mycelium = db.Column(db.Boolean)
    lum_basidiome = db.Column(db.Boolean)
    lum_stipe = db.Column(db.Boolean)
    lum_pileus = db.Column(db.Boolean)
    lum_lamellae = db.Column(db.Boolean)
    lum_spores = db.Column(db.Boolean)
    cultivation = db.Column(db.Text)
    finding_tips = db.Column(db.Text)
    nearby_trees = db.Column(db.Text)
    curiosities = db.Column(db.Text)
    general_description = db.Column(db.Text)
    colors = db.Column(db.Text)
    size_cm = db.Column(db.Float)
    growth_form_id = db.Column(
        db.Integer,
        db.ForeignKey("growth_forms.id", ondelete="SET NULL"),
        nullable=True,
    )
    substrate_id = db.Column(
        db.Integer,
        db.ForeignKey("substrates.id", ondelete="SET NULL"),
        nullable=True,
    )
    nutrition_mode_id = db.Column(
        db.Integer,
        db.ForeignKey("nutrition_modes.id", ondelete="SET NULL"),
        nullable=True,
    )
    season_start_month = db.Column(db.SmallInteger)
    season_end_month = db.Column(db.SmallInteger)

    species = db.relationship("Species", back_populates="characteristics")
    growth_form = db.relationship("GrowthForm")
    substrate = db.relationship("Substrate")
    nutrition_mode = db.relationship("NutritionMode")
    habitats = db.relationship(
        "Habitat",
        secondary="species_characteristics_habitats",
        back_populates="species_characteristics",
    )

    def __repr__(self):
        return f"<SpeciesCharacteristics species_id={self.species_id}>"
