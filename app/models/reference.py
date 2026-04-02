from app.extensions import db


class Reference(db.Model):
    __tablename__ = "references"

    id = db.Column(db.Integer, primary_key=True)
    doi = db.Column(db.Text, nullable=False)
    apa = db.Column(db.Text, nullable=False)

    species = db.relationship(
        "Species",
        secondary="species_reference",
        back_populates="reference",
    )

    def __repr__(self):
        return f"<Reference id={self.id} doi={self.doi!r}>"
