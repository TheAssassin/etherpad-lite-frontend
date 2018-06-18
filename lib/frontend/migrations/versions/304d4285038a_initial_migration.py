"""
Initial migration

Revision ID: 304d4285038a
Revises: None
Create Date: 2015-06-08 21:55:25.715091
"""

# revision identifiers, used by Alembic.
revision = "304d4285038a"
down_revision = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table("user",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("uid", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=128), nullable=False),
        sa.Column("author_id", sa.String(length=32), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uid")
    )


def downgrade():
    op.drop_table("user")
