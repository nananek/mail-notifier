revision = '0004_mailbox_name'
down_revision = '0003_notification_format'
branch_labels = None
depends_on = None
"""add mailbox_name to Account"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column('accounts', sa.Column('mailbox_name', sa.String(length=120), nullable=False, server_default='INBOX'))
    op.execute("UPDATE accounts SET mailbox_name = 'INBOX'")
    op.alter_column('accounts', 'mailbox_name', server_default=None)

def downgrade():
    op.drop_column('accounts', 'mailbox_name')
