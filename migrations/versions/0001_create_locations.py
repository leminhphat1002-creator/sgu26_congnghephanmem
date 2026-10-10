"""create locations

Revision ID: 0001
Revises:
Create Date: 2026-10-10
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "locations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description_source", sa.Text(), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("radius", sa.Float(), nullable=False, server_default="80"),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="manual"),
        sa.Column("source_lang", sa.String(length=8), nullable=True),
        sa.Column("source_title", sa.String(length=255), nullable=True),
        sa.Column("source_page_id", sa.Integer(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(), nullable=True),
        sa.Column("is_ready", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.UniqueConstraint("source", "source_lang", "source_page_id", name="uq_location_source"),
    )


def downgrade() -> None:
    op.drop_table("locations")
