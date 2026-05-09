"""add uid to species

Revision ID: a4b5c6d7e8f9
Revises: 90232da00fd3
Create Date: 2026-05-08 00:00:00.000000

"""

import uuid

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a4b5c6d7e8f9"
down_revision = "90232da00fd3"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("species", schema=None) as batch_op:
        batch_op.add_column(sa.Column("uid", sa.String(length=36), nullable=True))

    connection = op.get_bind()
    species_ids = connection.execute(sa.text("SELECT id FROM species WHERE uid IS NULL")).scalars()
    for species_id in species_ids:
        connection.execute(
            sa.text("UPDATE species SET uid = :uid WHERE id = :id"),
            {"uid": str(uuid.uuid4()), "id": species_id},
        )

    with op.batch_alter_table("species", schema=None) as batch_op:
        batch_op.alter_column("uid", existing_type=sa.String(length=36), nullable=False)
        batch_op.create_unique_constraint("uq_species_uid", ["uid"])


def downgrade():
    with op.batch_alter_table("species", schema=None) as batch_op:
        batch_op.drop_constraint("uq_species_uid", type_="unique")
        batch_op.drop_column("uid")
