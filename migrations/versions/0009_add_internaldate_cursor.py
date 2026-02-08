"""Add INTERNALDATE cursor and message deduplication fields

Revision ID: 0009
Revises: 0008
Create Date: 2026-02-08 14:30:00.000000

Migrates from UID-based polling to INTERNALDATE-based cursor polling
to handle Proton Mail Bridge UIDVALIDITY resets.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade():
    # Add last_processed_internal_date for high-water mark cursor
    op.add_column(
        "accounts",
        sa.Column("last_processed_internal_date", sa.DateTime(), nullable=True),
    )
    
    # Add processed_message_ids for deduplication (stored as JSON text)
    op.add_column(
        "accounts",
        sa.Column("processed_message_ids", sa.Text(), nullable=False, server_default=""),
    )


def downgrade():
    op.drop_column("accounts", "processed_message_ids")
    op.drop_column("accounts", "last_processed_internal_date")
