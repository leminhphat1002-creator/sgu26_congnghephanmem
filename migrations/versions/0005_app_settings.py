"""Persistent bootstrap state for hosted deployments."""

import sqlalchemy as sa
from alembic import op

revision = "0005_app_settings"
down_revision = "0004_admin"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "app_settings",
        sa.Column("key", sa.String(80), primary_key=True),
        sa.Column("value", sa.String(255), nullable=False),
    )


def downgrade():
    op.drop_table("app_settings")
