"""
Fix author ID bug

Revision ID: 40a4dc1888e4
Revises: 304d4285038a
Create Date: 2015-06-10 18:27:43.274556
"""

# revision identifiers, used by Alembic.
revision = "40a4dc1888e4"
down_revision = "304d4285038a"

from alembic import op
import sqlalchemy as sa


def upgrade():
    with op.batch_alter_table("user") as batch_op:
        batch_op.alter_column("author_id",
                              existing_type=sa.VARCHAR(length=32),
                              nullable=True)


def downgrade():
    with op.batch_alter_table("user") as batch_op:
        batch_op.alter_column("author_id",
                              existing_type=sa.VARCHAR(length=32),
                              nullable=False)
