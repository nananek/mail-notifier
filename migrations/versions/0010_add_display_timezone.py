"""Add display_timezone to WorkerState

Revision ID: 0010_add_display_timezone
Revises: 0009_add_internaldate_cursor
Create Date: 2026-02-08 15:00:00.000000

Adds timezone configuration for UI display.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0010_add_display_timezone"
down_revision = "0009_add_internaldate_cursor"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "worker_state",
        sa.Column("display_timezone", sa.String(50), nullable=False, server_default="UTC"),
    )


def downgrade():
    op.drop_column("worker_state", "display_timezone")
