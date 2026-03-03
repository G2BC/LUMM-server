from app.extensions import db


class NutritionMode(db.Model):
    __tablename__ = "nutrition_modes"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.Text, nullable=False, unique=True)
    label_pt = db.Column(db.Text, nullable=False)
    label_en = db.Column(db.Text, nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, server_default=db.true())

    def __repr__(self):
        return f"<NutritionMode id={self.id} slug={self.slug!r}>"
