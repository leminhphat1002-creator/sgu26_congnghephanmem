"""Add an idempotency key for visitor playback requests."""

import sqlalchemy as sa
from alembic import op

revision = "0006_narration_play"
down_revision = "0005_app_settings"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("activity_events", sa.Column("play_id", sa.String(36), nullable=True))
    op.create_index("uq_activity_events_play_id", "activity_events", ["play_id"], unique=True)


def downgrade():
    op.drop_index("uq_activity_events_play_id", table_name="activity_events")
    with op.batch_alter_table("activity_events") as batch:
        batch.drop_column("play_id")
