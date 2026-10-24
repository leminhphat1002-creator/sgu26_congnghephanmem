"""Thêm bảng thuyết minh lâu dài, giữ nguyên dữ liệu và migration cũ."""

import sqlalchemy as sa
from alembic import op

revision = "0003_poi_narrations"
down_revision = "36f391114b26"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "poi_narrations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "location_id",
            sa.Integer(),
            sa.ForeignKey("locations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("language", sa.String(8), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.UniqueConstraint("location_id", "language", name="uq_poi_narration_language"),
    )
    op.create_index("ix_poi_narrations_location_id", "poi_narrations", ["location_id"])


def downgrade():
    op.drop_table("poi_narrations")
