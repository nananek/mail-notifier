"""Add ssl_mode to Account model

Revision ID: 0005
Revises: 0004
Create Date: 2026-02-08

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


def upgrade():
    # Add ssl_mode column with default 'ssl'
    op.add_column('accounts', sa.Column('ssl_mode', sa.String(length=20), nullable=False, server_default='ssl'))
    
    # Update existing records: if use_ssl=True and port=993 -> 'ssl', if use_ssl=True and port!=993 -> 'starttls', else -> 'none'
    op.execute("""
        UPDATE accounts 
        SET ssl_mode = CASE 
            WHEN use_ssl = true AND imap_port = 993 THEN 'ssl'
            WHEN use_ssl = true AND imap_port != 993 THEN 'starttls'
            ELSE 'none'
        END
    """)


def downgrade():
    op.drop_column('accounts', 'ssl_mode')
