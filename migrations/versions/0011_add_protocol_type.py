"""Add protocol_type to accounts

Revision ID: 0011_add_protocol_type
Revises: 0010_add_display_timezone
Create Date: 2026-02-11 00:00:00.000000

Adds protocol_type column to support IMAP and POP3.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0011_add_protocol_type"
down_revision = "0010_add_display_timezone"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "accounts",
        sa.Column(
            "protocol_type",
            sa.String(10),
            nullable=False,
            server_default="imap",
        ),
    )


def downgrade():
    op.drop_column("accounts", "protocol_type")
